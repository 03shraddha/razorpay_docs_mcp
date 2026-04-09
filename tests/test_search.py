"""Tests for the search layer — uses an in-memory DuckDB index."""

from datetime import datetime, timezone

import duckdb
import pytest

from razorpay_docs_mcp.db import create_fts_index
from razorpay_docs_mcp.search import fetch_full, search

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_DOCS = [
    {
        "url": "https://razorpay.com/docs/webhooks",
        "raw_url": "https://raw.githubusercontent.com/razorpay/markdown-docs/master/webhooks.md",
        "title": "About Webhooks",
        "description": "Webhook events and signature verification.",
        "product": "webhooks",
        "content": (
            "# About Webhooks\n\n"
            "## Signature Verification\n\n"
            "Use validateWebhookSignature to verify the HMAC-SHA256 signature "
            "of incoming webhook payloads. Pass the raw request body as a string."
        ),
    },
    {
        "url": "https://razorpay.com/docs/api",
        "raw_url": "https://raw.githubusercontent.com/razorpay/markdown-docs/master/api.md",
        "title": "API Reference",
        "description": "Razorpay REST API reference.",
        "product": "api",
        "content": (
            "# API Reference\n\n"
            "## Authentication\n\n"
            "All API requests use HTTP Basic Auth with your key_id and key_secret.\n\n"
            "## Orders\n\n"
            "Create an order with POST /v1/orders."
        ),
    },
    {
        "url": "https://razorpay.com/docs/errors",
        "raw_url": "https://raw.githubusercontent.com/razorpay/markdown-docs/master/errors.md",
        "title": "About Errors",
        "description": "Error codes and handling.",
        "product": "errors",
        "content": (
            "# About Errors\n\n"
            "## BAD_REQUEST_ERROR\n\n"
            "Returned when the request body is malformed or a required field is missing."
        ),
    },
]


@pytest.fixture
def conn():
    """In-memory DuckDB with schema + FTS populated from _DOCS."""
    c = duckdb.connect(":memory:")
    c.execute("INSTALL fts")
    c.execute("LOAD fts")

    c.execute("""
        CREATE TABLE docs (
            url TEXT PRIMARY KEY,
            raw_url TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            product TEXT NOT NULL,
            fetched_at TIMESTAMP NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE chunks (
            chunk_id INTEGER PRIMARY KEY,
            url TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            heading_path TEXT,
            content TEXT NOT NULL
        )
    """)

    now = datetime.now(timezone.utc)
    for doc in _DOCS:
        c.execute(
            "INSERT INTO docs VALUES (?, ?, ?, ?, ?, ?)",
            [doc["url"], doc["raw_url"], doc["title"], doc["description"], doc["product"], now],
        )

    # Import chunker so we use real chunk_markdown
    from razorpay_docs_mcp.ingest import chunk_markdown

    chunk_id = 0
    for doc in _DOCS:
        for ch in chunk_markdown(doc["content"]):
            c.execute(
                "INSERT INTO chunks VALUES (?, ?, ?, ?, ?)",
                [chunk_id, doc["url"], ch.chunk_index, ch.heading_path, ch.content],
            )
            chunk_id += 1

    create_fts_index(c)
    return c


# ---------------------------------------------------------------------------
# search() tests
# ---------------------------------------------------------------------------

def test_search_returns_correct_url(conn):
    """Searching for 'validateWebhookSignature' returns the webhooks URL."""
    hits = search(conn, "validateWebhookSignature", product=None, limit=10)
    assert len(hits) >= 1
    urls = [h.url for h in hits]
    assert "https://razorpay.com/docs/webhooks" in urls


def test_search_snippet_contains_term(conn):
    """The snippet for a webhook hit contains at least part of the query."""
    hits = search(conn, "HMAC-SHA256 signature", product=None, limit=10)
    webhooks_hits = [h for h in hits if h.url == "https://razorpay.com/docs/webhooks"]
    assert webhooks_hits, "Expected a webhooks hit"
    snippet = webhooks_hits[0].snippet
    assert "HMAC" in snippet or "signature" in snippet.lower()


def test_search_product_filter_narrows(conn):
    """Product filter restricts results to only that product."""
    all_hits = search(conn, "error", product=None, limit=25)
    filtered_hits = search(conn, "error", product="errors", limit=25)
    assert len(filtered_hits) <= len(all_hits)
    for h in filtered_hits:
        assert h.product == "errors"


def test_search_product_filter_excludes_others(conn):
    """A product filter that doesn't match the best result changes the ranking."""
    # "validateWebhookSignature" best matches webhooks, not api
    webhooks_only = search(conn, "validateWebhookSignature", product="api", limit=10)
    for h in webhooks_only:
        assert h.product == "api"


def test_search_result_has_required_fields(conn):
    """Every search hit includes all required fields."""
    hits = search(conn, "authentication", product=None, limit=5)
    for h in hits:
        assert h.url.startswith("https://razorpay.com/docs/")
        assert h.title
        assert h.product
        assert h.snippet
        assert isinstance(h.score, float)


# ---------------------------------------------------------------------------
# fetch_full() tests
# ---------------------------------------------------------------------------

def test_fetch_full_found(conn):
    found, not_found = fetch_full(conn, ["https://razorpay.com/docs/api"])
    assert len(found) == 1
    assert not_found == []
    doc = found[0]
    assert doc.url == "https://razorpay.com/docs/api"
    assert doc.title == "API Reference"
    assert doc.product == "api"
    assert "Orders" in doc.content


def test_fetch_full_not_found(conn):
    found, not_found = fetch_full(conn, ["https://razorpay.com/docs/nonexistent"])
    assert found == []
    assert not_found == ["https://razorpay.com/docs/nonexistent"]


def test_fetch_full_mixed(conn):
    found, not_found = fetch_full(
        conn,
        ["https://razorpay.com/docs/errors", "https://razorpay.com/docs/missing"],
    )
    assert len(found) == 1
    assert found[0].url == "https://razorpay.com/docs/errors"
    assert not_found == ["https://razorpay.com/docs/missing"]


def test_fetch_full_never_exposes_raw_url(conn):
    """The returned doc URL must be the canonical razorpay.com URL."""
    found, _ = fetch_full(conn, ["https://razorpay.com/docs/webhooks"])
    assert found
    assert "raw.githubusercontent.com" not in found[0].url

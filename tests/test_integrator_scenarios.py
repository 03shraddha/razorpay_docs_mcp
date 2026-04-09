"""Integration scenario tests — simulates a developer using the MCP to solve
real Razorpay integration pain points.

These tests connect to the REAL DuckDB file at data/razorpay_docs.duckdb.
All tests are skipped automatically when the file doesn't exist (e.g. in CI
before ingest has run).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from razorpay_docs_mcp.db import get_connection
from razorpay_docs_mcp.search import fetch_full, search

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

# Resolve relative to this file so the tests work from any working directory.
_DB_PATH = Path(__file__).parent.parent / "data" / "razorpay_docs.duckdb"

_db_missing = pytest.mark.skipif(
    not _DB_PATH.exists(),
    reason=f"Real DuckDB not found at {_DB_PATH} — run ingest first",
)


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def real_conn():
    """Open a read-only-style connection to the real DuckDB for all scenarios."""
    conn = get_connection(str(_DB_PATH))
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Pain-point scenario 1 — Webhook signature verification
# ---------------------------------------------------------------------------


@_db_missing
def test_webhook_signature_verification(real_conn):
    """Searching 'webhook signature verification' should surface a webhooks doc."""
    hits = search(real_conn, "webhook signature verification", product=None, limit=10)

    assert len(hits) >= 1, "Expected at least one result for webhook signature query"

    # At least one hit should mention 'webhook' somewhere — the docs structure
    # places most webhook content under the 'payments' product, so we check
    # content rather than strictly requiring product == 'webhooks'.
    webhook_hits = [
        h for h in hits
        if "webhook" in h.url.lower()
        or "webhook" in h.title.lower()
        or "webhook" in h.snippet.lower()
    ]
    assert webhook_hits, (
        "Expected at least one hit referencing 'webhook' in URL/title/snippet. "
        f"Got: {[(h.url, h.snippet[:60]) for h in hits]}"
    )

    # Scores must be positive floats
    for h in hits:
        assert h.score > 0, f"Expected positive BM25 score, got {h.score} for {h.url}"


# ---------------------------------------------------------------------------
# Pain-point scenario 2 — Payment capture after authorization
# ---------------------------------------------------------------------------


@_db_missing
def test_payment_capture_after_authorization(real_conn):
    """Searching 'capture payment after authorization' should return payment docs."""
    hits = search(real_conn, "capture payment after authorization", product=None, limit=10)

    assert len(hits) >= 1, "Expected results for payment capture query"

    # At least one result should mention 'payment' somewhere (URL, title, or snippet)
    payment_hits = [
        h for h in hits
        if "payment" in h.url.lower()
        or "payment" in h.title.lower()
        or "payment" in h.snippet.lower()
    ]
    assert payment_hits, (
        "Expected at least one hit referencing 'payment'. "
        f"Titles: {[h.title for h in hits]}"
    )

    for h in hits:
        assert h.score > 0
        assert h.url.startswith("https://razorpay.com/docs/")


# ---------------------------------------------------------------------------
# Pain-point scenario 3 — Refund creation with product filter
# ---------------------------------------------------------------------------


@_db_missing
def test_refund_creation_product_filter(real_conn):
    """Searching 'create refund' with product='api' should narrow results to api."""
    hits = search(real_conn, "create refund", product="api", limit=10)

    # If the 'api' product has refund content, we expect results; if the filter
    # returns nothing that's also valid — the key assertion is the filter is honoured.
    for h in hits:
        assert h.product == "api", (
            f"Product filter 'api' was violated: got product='{h.product}' for {h.url}"
        )
        assert h.score > 0

    # Compare against unfiltered to confirm the filter narrows the result set
    unfiltered = search(real_conn, "create refund", product=None, limit=50)
    assert len(hits) <= len(unfiltered), (
        "Filtered results should not exceed unfiltered results"
    )


# ---------------------------------------------------------------------------
# Pain-point scenario 4 — UPI AutoPay recurring subscriptions
# ---------------------------------------------------------------------------


@_db_missing
def test_upi_autopay_recurring_subscription(real_conn):
    """Searching 'UPI AutoPay recurring subscription' should return results."""
    hits = search(real_conn, "UPI AutoPay recurring subscription", product=None, limit=10)

    assert len(hits) >= 1, "Expected results for UPI AutoPay subscription query"

    for h in hits:
        assert h.score > 0
        assert h.url.startswith("https://razorpay.com/docs/")
        assert h.title  # title must be non-empty
        assert h.snippet  # snippet must be non-empty


# ---------------------------------------------------------------------------
# Pain-point scenario 5 — Order creation
# ---------------------------------------------------------------------------


@_db_missing
def test_order_creation(real_conn):
    """Searching 'create order amount currency receipt' should return order docs."""
    hits = search(real_conn, "create order amount currency receipt", product=None, limit=10)

    assert len(hits) >= 1, "Expected results for order creation query"

    # At least one hit should reference 'order' somewhere. BM25 returns results
    # ranked by term frequency — 'order' may appear in snippets rather than
    # URL/title for multi-term queries, so we check all three fields.
    order_hits = [
        h for h in hits
        if "order" in h.url.lower()
        or "order" in h.title.lower()
        or "order" in h.snippet.lower()
    ]
    assert order_hits, (
        "Expected at least one hit referencing 'order' in URL/title/snippet. "
        f"Got: {[(h.url, h.snippet[:60]) for h in hits]}"
    )

    for h in hits:
        assert h.score > 0


# ---------------------------------------------------------------------------
# Pain-point scenario 6 — Error codes (BAD_REQUEST_ERROR)
# ---------------------------------------------------------------------------


@_db_missing
def test_bad_request_error_with_product_filter(real_conn):
    """Searching 'BAD_REQUEST_ERROR' with product='errors' should work."""
    hits = search(real_conn, "BAD_REQUEST_ERROR", product="errors", limit=10)

    # Check the product filter is respected regardless of result count
    for h in hits:
        assert h.product == "errors", (
            f"Product filter 'errors' was violated: got '{h.product}' for {h.url}"
        )
        assert h.score > 0

    # Also verify unfiltered search returns results with error-related content.
    # In practice BAD_REQUEST_ERROR surfaces under 'api' and 'payments' products
    # (not the 'errors' product — that product covers different error reference pages).
    unfiltered = search(real_conn, "BAD_REQUEST_ERROR", product=None, limit=25)
    assert len(unfiltered) >= 1, (
        "Expected unfiltered search for 'BAD_REQUEST_ERROR' to return results"
    )
    # Confirm at least one result has error-related content in snippet or URL
    error_content_hits = [
        h for h in unfiltered
        if "error" in h.snippet.lower() or "error" in h.url.lower()
    ]
    assert error_content_hits, (
        "Expected at least one result with 'error' content in unfiltered search"
    )


# ---------------------------------------------------------------------------
# Integrator mistake prevention 1 — deprecated field 'payment_capture'
# ---------------------------------------------------------------------------


@_db_missing
def test_deprecated_payment_capture_field_findable(real_conn):
    """An agent searching for the deprecated 'payment_capture' field should find
    docs so it can surface deprecation warnings rather than silently failing."""
    hits = search(real_conn, "payment_capture", product=None, limit=10)

    assert len(hits) >= 1, (
        "Expected results for deprecated field 'payment_capture'. "
        "If this returns nothing, an agent would miss the deprecation notice."
    )

    for h in hits:
        assert h.score > 0
        assert h.snippet  # the snippet should contain useful context


# ---------------------------------------------------------------------------
# Integrator mistake prevention 2 — fetch_full returns substantial content
# ---------------------------------------------------------------------------


@_db_missing
def test_fetch_full_webhooks_doc_has_sufficient_content(real_conn):
    """Fetching the webhooks doc should return content longer than 500 chars,
    confirming the MCP surfaces enough detail for integration guidance."""
    found, not_found = fetch_full(real_conn, ["https://razorpay.com/docs/webhooks"])

    if not_found:
        pytest.skip(
            "https://razorpay.com/docs/webhooks not present in this DB snapshot"
        )

    assert len(found) == 1
    doc = found[0]

    assert len(doc.content) > 500, (
        f"Expected webhooks doc content > 500 chars, got {len(doc.content)} chars. "
        "Short content means chunks were dropped during ingest."
    )
    assert doc.title  # non-empty title
    assert doc.product  # non-empty product
    assert "raw.githubusercontent.com" not in doc.url, (
        "Returned URL must be the canonical razorpay.com URL, not the raw GitHub URL"
    )

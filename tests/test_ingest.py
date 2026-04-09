"""Tests for parse_llms_txt and chunk_markdown."""

from pathlib import Path

import pytest

from razorpay_docs_mcp.ingest import chunk_markdown, parse_llms_txt

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_parse_llms_txt_count():
    """Fixture has exactly 5 links."""
    text = load_fixture("llms_sample.txt")
    entries = parse_llms_txt(text)
    assert len(entries) == 5


def test_parse_llms_txt_api_entry():
    text = load_fixture("llms_sample.txt")
    entries = parse_llms_txt(text)
    by_url = {e.url: e for e in entries}

    e = by_url["https://razorpay.com/docs/api"]
    assert e.title == "Razorpay API Documentation"
    assert e.product == "api"
    assert e.raw_url == "https://raw.githubusercontent.com/razorpay/markdown-docs/master/api.md"
    assert "Razorpay APIs" in (e.description or "")


def test_parse_llms_txt_webhooks_entry():
    text = load_fixture("llms_sample.txt")
    entries = parse_llms_txt(text)
    by_url = {e.url: e for e in entries}

    e = by_url["https://razorpay.com/docs/webhooks"]
    assert e.title == "About Webhooks"
    assert e.product == "webhooks"


def test_parse_llms_txt_errors_entry():
    text = load_fixture("llms_sample.txt")
    entries = parse_llms_txt(text)
    by_url = {e.url: e for e in entries}

    e = by_url["https://razorpay.com/docs/errors"]
    assert e.product == "errors"


def test_parse_llms_txt_products():
    """Each entry maps to a distinct product."""
    text = load_fixture("llms_sample.txt")
    entries = parse_llms_txt(text)
    products = {e.product for e in entries}
    assert products == {"api", "errors", "payments", "webhooks", "x"}


# ---------------------------------------------------------------------------
# chunk_markdown tests
# ---------------------------------------------------------------------------

_SHORT_DOC = """\
# My Doc

Intro paragraph.

## Section A

Content for section A.

## Section B

Content for section B.
"""

_LONG_SECTION = "word " * 500  # ~2500 chars — forces sub-split


def test_chunk_markdown_short_doc():
    """A doc with two H2 sections produces at least 2 chunks."""
    chunks = chunk_markdown(_SHORT_DOC)
    assert len(chunks) >= 2


def test_chunk_markdown_heading_path():
    """Chunks track the H1 > H2 breadcrumb."""
    chunks = chunk_markdown(_SHORT_DOC)
    heading_paths = [c.heading_path for c in chunks if c.heading_path]
    # Should have "My Doc > Section A" and "My Doc > Section B"
    assert any("Section A" in (p or "") for p in heading_paths)
    assert any("Section B" in (p or "") for p in heading_paths)


def test_chunk_markdown_long_section_splits():
    """A single H2 section longer than 2000 chars is sub-split into multiple chunks."""
    doc = f"# Big Doc\n\n## Long Section\n\n{_LONG_SECTION}"
    chunks = chunk_markdown(doc)
    assert len(chunks) >= 2, "Long section should produce multiple chunks"


def test_chunk_markdown_no_headings():
    """A doc with no headings at all produces exactly 1 chunk."""
    doc = "Just some plain text with no headings whatsoever."
    chunks = chunk_markdown(doc)
    assert len(chunks) == 1
    assert chunks[0].content == doc


def test_chunk_markdown_chunk_index_sequential():
    """chunk_index values are 0-based and sequential."""
    chunks = chunk_markdown(_SHORT_DOC)
    for i, ch in enumerate(chunks):
        assert ch.chunk_index == i

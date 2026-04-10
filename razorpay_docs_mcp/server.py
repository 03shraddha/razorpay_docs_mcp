"""MCP server entry point — exposes search_razorpay_docs and get_razorpay_docs."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from mcp.server import FastMCP
from pydantic import Field

from .db import get_connection
from .search import fetch_full, search

# Resolve DB path relative to repo root (parent of this package)
_DB_PATH = str(Path(__file__).parent.parent / "data" / "razorpay_docs.duckdb")

mcp = FastMCP(
    name="razorpay-docs-mcp",
    instructions=(
        "Search and fetch Razorpay's official documentation. "
        "Use search_razorpay_docs to find relevant docs by query, "
        "then get_razorpay_docs to read the full content of specific pages."
    ),
)

# Connection is opened lazily on first tool call so the server can complete
# the MCP handshake before any slow DB/extension initialisation runs.
_conn = None


def _get_conn():
    global _conn
    if _conn is None:
        _conn = get_connection(_DB_PATH)
    return _conn


@mcp.tool()
def search_razorpay_docs(
    query: Annotated[str, Field(description="What to search for in Razorpay docs")],
    product: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "Optional product filter. One of: payments, api, x, partners, "
                "payroll, pos, webhooks, errors"
            ),
        ),
    ] = None,
    limit: Annotated[
        int,
        Field(default=10, ge=1, le=25, description="Max results (1–25, default 10)"),
    ] = 10,
) -> dict:
    """Search Razorpay documentation using BM25 full-text search.

    Returns a ranked list of matching doc chunks with snippets and source URLs.
    """
    hits = search(_get_conn(), query, product, limit)
    return {
        "results": [
            {
                "url": h.url,
                "title": h.title,
                "heading_path": h.heading_path,
                "snippet": h.snippet,
                "product": h.product,
                "score": h.score,
            }
            for h in hits
        ]
    }


@mcp.tool()
def get_razorpay_docs(
    urls: Annotated[
        list[str],
        Field(
            description=(
                "List of canonical razorpay.com/docs/... URLs to fetch. Max 20."
            ),
            max_length=20,
        ),
    ],
) -> dict:
    """Fetch full markdown content for one or more Razorpay doc pages.

    Pass canonical razorpay.com/docs/... URLs (from search results).
    Returns full markdown for each found URL and a list of any not found.
    """
    found, not_found = fetch_full(_get_conn(), urls[:20])
    return {
        "documents": [
            {
                "url": d.url,
                "title": d.title,
                "product": d.product,
                "content": d.content,
            }
            for d in found
        ],
        "not_found": not_found,
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Razorpay Docs MCP server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport to use: 'stdio' for local tools (Claude Desktop, Cursor), "
             "'http' for web-based AI clients (claude.ai, ChatGPT)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (only used with --transport http)",
    )
    args = parser.parse_args()

    if args.transport == "http":
        # Override host/port on the already-constructed FastMCP settings object
        mcp.settings.host = "0.0.0.0"
        mcp.settings.port = args.port
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

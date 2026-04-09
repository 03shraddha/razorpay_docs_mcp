"""CLI entry point: python -m razorpay_docs_mcp.refresh

Downloads llms.txt, fetches all docs, indexes into DuckDB.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import httpx

from .db import get_connection
from .ingest import fetch_all, index_all, parse_llms_txt

LLMS_TXT_URL = "https://razorpay.com/docs/llms.txt"
# DB lives at data/razorpay_docs.duckdb, relative to the repo root.
# We resolve relative to this file's parent's parent (the repo root).
_REPO_ROOT = Path(__file__).parent.parent
DB_PATH = str(_REPO_ROOT / "data" / "razorpay_docs.duckdb")


def main() -> None:
    print("=== Razorpay Docs MCP — Refresh ===\n")

    # 1. Download llms.txt
    print(f"Fetching {LLMS_TXT_URL} …")
    try:
        resp = httpx.get(LLMS_TXT_URL, timeout=60.0, follow_redirects=True)
        resp.raise_for_status()
    except Exception as exc:
        print(f"ERROR: could not fetch llms.txt: {exc}")
        sys.exit(1)

    llms_txt = resp.text
    print(f"  Downloaded {len(llms_txt):,} bytes")

    # 2. Parse
    entries = parse_llms_txt(llms_txt)
    print(f"  Found {len(entries):,} doc URLs\n")

    if not entries:
        print("ERROR: no entries parsed from llms.txt — check the URL format.")
        sys.exit(1)

    # 3. Fetch all markdown files concurrently
    print(f"Fetching {len(entries):,} markdown files (concurrency=20) …")
    fetched = asyncio.run(fetch_all(entries, concurrency=20))
    failed = len(entries) - len(fetched)
    print(f"  Fetched: {len(fetched):,}  |  Failed/skipped: {failed:,}\n")

    # 4. Open DB and index
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    print(f"Opening database: {DB_PATH}")
    conn = get_connection(DB_PATH)

    print("Indexing …")
    chunk_count = index_all(conn, fetched)
    conn.close()

    print(f"\n=== Done ===")
    print(f"  Docs indexed : {len(fetched):,}")
    print(f"  Chunks       : {chunk_count:,}")
    print(f"  Failures     : {failed:,}")
    print(f"  DB path      : {DB_PATH}")


if __name__ == "__main__":
    main()

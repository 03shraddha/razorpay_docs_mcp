"""DuckDB connection and schema bootstrap."""

from __future__ import annotations

import duckdb


def get_connection(path: str) -> duckdb.DuckDBPyConnection:
    """Open or create the DuckDB database, install FTS, and ensure schema exists."""
    conn = duckdb.connect(path)

    conn.execute("LOAD fts")

    # Docs table: one row per document from llms.txt
    conn.execute("""
        CREATE TABLE IF NOT EXISTS docs (
            url          TEXT PRIMARY KEY,
            raw_url      TEXT NOT NULL,
            title        TEXT NOT NULL,
            description  TEXT,
            product      TEXT NOT NULL,
            fetched_at   TIMESTAMP NOT NULL
        )
    """)

    # Chunks table: one row per chunk, FK back to docs
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            chunk_id     INTEGER PRIMARY KEY,
            url          TEXT NOT NULL REFERENCES docs(url),
            chunk_index  INTEGER NOT NULL,
            heading_path TEXT,
            content      TEXT NOT NULL
        )
    """)

    return conn


def create_fts_index(conn: duckdb.DuckDBPyConnection) -> None:
    """Create (or recreate) the BM25 full-text index on chunks.

    Must be called AFTER data is inserted, not before.
    Safe to call repeatedly — drops the old index first if it exists.
    """
    try:
        conn.execute("PRAGMA drop_fts_index('chunks')")
    except Exception:
        pass  # Index didn't exist yet — that's fine

    conn.execute(
        "PRAGMA create_fts_index('chunks', 'chunk_id', 'content', 'heading_path')"
    )

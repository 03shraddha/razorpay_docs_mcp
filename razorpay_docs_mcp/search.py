"""DuckDB FTS query layer: search chunks and fetch full docs."""

from __future__ import annotations

import re
from dataclasses import dataclass

import duckdb

_SNIPPET_LEN = 200


@dataclass
class SearchHit:
    url: str
    title: str
    heading_path: str | None
    snippet: str
    product: str
    score: float


@dataclass
class FullDoc:
    url: str
    title: str
    product: str
    content: str


def _make_snippet(content: str, query: str) -> str:
    """Return a ~200-char excerpt centred on the first query-term match."""
    # Try to find the first query term in content (case-insensitive)
    terms = query.split()
    pos = -1
    for term in terms:
        m = re.search(re.escape(term), content, re.IGNORECASE)
        if m:
            pos = m.start()
            break

    if pos == -1:
        # No term found — return the start of the content
        return content[:_SNIPPET_LEN].strip()

    start = max(0, pos - _SNIPPET_LEN // 2)
    end = start + _SNIPPET_LEN
    if end > len(content):
        end = len(content)
        start = max(0, end - _SNIPPET_LEN)

    snippet = content[start:end].strip()
    # Pad with ellipsis if we're not at the edges
    if start > 0:
        snippet = "…" + snippet
    if end < len(content):
        snippet = snippet + "…"
    return snippet


def search(
    conn: duckdb.DuckDBPyConnection,
    query: str,
    product: str | None,
    limit: int,
) -> list[SearchHit]:
    """BM25 full-text search over chunks, optionally filtered by product.

    DuckDB FTS uses a scalar function: fts_main_{table}.match_bm25(row_id, query)
    returns a score (float) or NULL if the row doesn't match.
    """
    if product:
        sql = """
            SELECT
                c.chunk_id,
                c.url,
                c.heading_path,
                c.content,
                d.title,
                d.product,
                fts_main_chunks.match_bm25(c.chunk_id, ?) AS score
            FROM chunks c
            JOIN docs d ON d.url = c.url
            WHERE d.product = ?
              AND score IS NOT NULL
            ORDER BY score DESC
            LIMIT ?
        """
        rows = conn.execute(sql, [query, product, limit]).fetchall()
    else:
        sql = """
            SELECT
                c.chunk_id,
                c.url,
                c.heading_path,
                c.content,
                d.title,
                d.product,
                fts_main_chunks.match_bm25(c.chunk_id, ?) AS score
            FROM chunks c
            JOIN docs d ON d.url = c.url
            WHERE score IS NOT NULL
            ORDER BY score DESC
            LIMIT ?
        """
        rows = conn.execute(sql, [query, limit]).fetchall()

    hits: list[SearchHit] = []
    for row in rows:
        _chunk_id, url, heading_path, content, title, doc_product, score = row
        hits.append(SearchHit(
            url=url,
            title=title,
            heading_path=heading_path,
            snippet=_make_snippet(content, query),
            product=doc_product,
            score=round(float(score), 4),
        ))
    return hits


def fetch_full(
    conn: duckdb.DuckDBPyConnection,
    urls: list[str],
) -> tuple[list[FullDoc], list[str]]:
    """Reassemble full markdown for each requested URL from stored chunks."""
    found: list[FullDoc] = []
    not_found: list[str] = []

    for url in urls:
        doc_row = conn.execute(
            "SELECT title, product FROM docs WHERE url = ?", [url]
        ).fetchone()

        if doc_row is None:
            not_found.append(url)
            continue

        title, product = doc_row

        chunk_rows = conn.execute(
            "SELECT content FROM chunks WHERE url = ? ORDER BY chunk_index",
            [url],
        ).fetchall()

        content = "\n\n".join(row[0] for row in chunk_rows)
        found.append(FullDoc(url=url, title=title, product=product, content=content))

    return found, not_found

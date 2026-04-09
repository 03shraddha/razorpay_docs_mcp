"""Parse llms.txt, fetch markdown, chunk, and index into DuckDB."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timezone

import duckdb
import httpx

# Prefix to strip when deriving canonical razorpay.com URLs
# Format confirmed live 2026-04-09 against https://razorpay.com/docs/llms.txt
_RAW_PREFIX = "https://raw.githubusercontent.com/razorpay/markdown-docs/master/"
_CANONICAL_PREFIX = "https://razorpay.com/docs/"

# Regex: captures [Title](raw_url): optional description
_LINK_RE = re.compile(
    r"\[([^\]]+)\]\((https://raw\.githubusercontent\.com/razorpay/markdown-docs/master/[^)]+\.md)\)"
    r"(?::\s*(.+))?"
)


@dataclass
class DocEntry:
    url: str          # canonical razorpay.com/docs/...
    raw_url: str      # raw.githubusercontent.com/...
    title: str
    description: str | None
    product: str      # first path segment after llm-content/


@dataclass
class FetchedDoc:
    entry: DocEntry
    content: str


@dataclass
class Chunk:
    chunk_index: int
    heading_path: str | None
    content: str


def parse_llms_txt(text: str) -> list[DocEntry]:
    """Extract every raw GitHub link from llms.txt and derive canonical URLs.

    Deduplicates by canonical URL — first occurrence wins.
    """
    seen: set[str] = set()
    entries: list[DocEntry] = []
    for m in _LINK_RE.finditer(text):
        title = m.group(1).strip()
        raw_url = m.group(2).strip()
        description = m.group(3).strip() if m.group(3) else None

        if not raw_url.startswith(_RAW_PREFIX):
            continue  # Not a doc URL we know how to map

        # Derive canonical URL: strip prefix, strip .md, prepend razorpay.com/docs/
        path = raw_url[len(_RAW_PREFIX):]
        if path.endswith(".md"):
            path = path[:-3]
        canonical = _CANONICAL_PREFIX + path

        if canonical in seen:
            continue  # llms.txt lists some URLs more than once — skip duplicates
        seen.add(canonical)

        # Product = first path segment.
        # For flat files like "api.md" (path = "api"), the segment IS the product.
        # For nested files like "payments/pg.md", the first segment is "payments".
        product = path.split("/")[0]

        entries.append(DocEntry(
            url=canonical,
            raw_url=raw_url,
            title=title,
            description=description,
            product=product,
        ))
    return entries


async def _fetch_one(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    entry: DocEntry,
) -> FetchedDoc | None:
    async with sem:
        try:
            resp = await client.get(entry.raw_url, timeout=30.0)
            if resp.status_code == 200:
                return FetchedDoc(entry=entry, content=resp.text)
            else:
                print(f"  SKIP {resp.status_code}: {entry.raw_url}")
                return None
        except Exception as exc:
            print(f"  ERROR {entry.raw_url}: {exc}")
            return None


async def fetch_all(
    entries: list[DocEntry],
    concurrency: int = 20,
) -> list[FetchedDoc]:
    """Fetch all raw markdown URLs concurrently, skip failures."""
    sem = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [_fetch_one(client, sem, e) for e in entries]
        results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]


def chunk_markdown(text: str) -> list[Chunk]:
    """Split markdown into chunks at H2 (##) boundaries.

    Sub-splits chunks over 2000 chars at H3 (###) or paragraph boundaries.
    Tracks heading breadcrumbs as 'H1 > H2 > H3'.
    """
    chunks: list[Chunk] = []
    chunk_index = 0

    # Extract the H1 (first # heading) for the breadcrumb root
    h1 = ""
    h1_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if h1_match:
        h1 = h1_match.group(1).strip()

    # Split on H2 headings (## but NOT ###)
    # We keep the delimiter in the split result by using a capture group
    h2_parts = re.split(r"(?m)(?=^## )", text)

    for part in h2_parts:
        if not part.strip():
            continue

        # Extract the H2 heading if present
        h2 = ""
        h2_match = re.match(r"^## (.+)$", part, re.MULTILINE)
        if h2_match:
            h2 = h2_match.group(1).strip()

        heading = " > ".join(filter(None, [h1, h2])) or None

        if len(part) <= 2000:
            chunks.append(Chunk(chunk_index, heading, part.strip()))
            chunk_index += 1
        else:
            # Sub-split on H3 headings first
            h3_parts = re.split(r"(?m)(?=^### )", part)
            current_h3 = ""
            for sub in h3_parts:
                if not sub.strip():
                    continue
                h3_match = re.match(r"^### (.+)$", sub, re.MULTILINE)
                if h3_match:
                    current_h3 = h3_match.group(1).strip()
                sub_heading = " > ".join(filter(None, [h1, h2, current_h3])) or None

                if len(sub) <= 2000:
                    chunks.append(Chunk(chunk_index, sub_heading, sub.strip()))
                    chunk_index += 1
                else:
                    # Final fallback: split on paragraph boundaries
                    paragraphs = re.split(r"\n\n+", sub)
                    buffer = ""
                    for para in paragraphs:
                        if len(buffer) + len(para) + 2 > 2000 and buffer:
                            chunks.append(Chunk(chunk_index, sub_heading, buffer.strip()))
                            chunk_index += 1
                            buffer = para
                        else:
                            buffer = (buffer + "\n\n" + para).strip() if buffer else para
                    if buffer.strip():
                        chunks.append(Chunk(chunk_index, sub_heading, buffer.strip()))
                        chunk_index += 1

    # If nothing chunked (no headings at all), treat whole doc as one chunk
    if not chunks and text.strip():
        chunks.append(Chunk(0, h1 or None, text.strip()))

    return chunks


def index_all(conn: duckdb.DuckDBPyConnection, fetched: list[FetchedDoc]) -> int:
    """Insert all docs and their chunks into DuckDB. Returns total chunk count."""
    from .db import create_fts_index

    now = datetime.now(timezone.utc)

    # Clear existing data
    conn.execute("DELETE FROM chunks")
    conn.execute("DELETE FROM docs")

    # Bulk-insert docs
    doc_rows = [
        (
            doc.entry.url,
            doc.entry.raw_url,
            doc.entry.title,
            doc.entry.description,
            doc.entry.product,
            now,
        )
        for doc in fetched
    ]
    conn.executemany(
        "INSERT INTO docs (url, raw_url, title, description, product, fetched_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        doc_rows,
    )

    # Bulk-insert chunks
    chunk_rows: list[tuple] = []
    chunk_id = 0
    for doc in fetched:
        for ch in chunk_markdown(doc.content):
            chunk_rows.append((chunk_id, doc.entry.url, ch.chunk_index, ch.heading_path, ch.content))
            chunk_id += 1

    conn.executemany(
        "INSERT INTO chunks (chunk_id, url, chunk_index, heading_path, content) "
        "VALUES (?, ?, ?, ?, ?)",
        chunk_rows,
    )

    # Rebuild FTS index
    create_fts_index(conn)

    return len(chunk_rows)

import argparse
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_DB = r"D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Resume Search DB\resumes.sqlite"


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = 1800, overlap: int = 250) -> list[tuple[int, int, str]]:
    chunks: list[tuple[int, int, str]] = []
    if not text:
        return chunks
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        if end < text_len:
            boundary = text.rfind(" ", start + int(chunk_size * 0.65), end)
            if boundary > start:
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            chunks.append((start, end, chunk))
        if end >= text_len:
            break
        start = max(0, end - overlap)
    return chunks


def setup_krisp_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS krisp_documents (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            date TEXT NOT NULL,
            url TEXT NOT NULL,
            speakers TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            document TEXT NOT NULL,
            indexed_utc TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS krisp_documents_fts USING fts5(
            document_id UNINDEXED,
            title,
            date,
            speakers,
            document
        );
        CREATE TABLE IF NOT EXISTS krisp_chunks (
            id INTEGER PRIMARY KEY,
            document_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            char_start INTEGER NOT NULL,
            char_end INTEGER NOT NULL,
            FOREIGN KEY(document_id) REFERENCES krisp_documents(id)
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS krisp_chunks_fts USING fts5(
            text,
            content='krisp_chunks',
            content_rowid='id'
        );
        """
    )


def title_from_document(document: str, fallback: str) -> str:
    for line in document.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or fallback
    return fallback


def normalize_payload(payload: object) -> list[dict[str, object]]:
    if isinstance(payload, dict):
        if isinstance(payload.get("results"), list):
            return payload["results"]
        if isinstance(payload.get("documents"), list):
            return payload["documents"]
        if isinstance(payload.get("meetings"), list):
            return payload["meetings"]
    if isinstance(payload, list):
        return payload
    raise ValueError("Expected a Krisp get_multiple_documents response or a list of documents.")


def import_document(conn: sqlite3.Connection, item: dict[str, object]) -> bool:
    doc_id = str(item.get("id") or item.get("meeting_id") or item.get("document_id") or "").strip()
    document = item.get("document")
    if not doc_id or not isinstance(document, str) or not document.strip():
        return False

    title = str(item.get("title") or item.get("name") or title_from_document(document, doc_id))
    date = str(item.get("date") or "")
    url = str(item.get("url") or f"https://app.krisp.ai/m/{doc_id}?active_tab=ai_notes")
    speakers_value = item.get("speakers") or item.get("attendees") or []
    if isinstance(speakers_value, list):
        speakers = "; ".join(str(s) for s in speakers_value if s)
    else:
        speakers = str(speakers_value)

    searchable = normalize_text(f"{title} {date} {speakers} {document}")
    digest = hashlib.sha256(document.encode("utf-8")).hexdigest()
    indexed_utc = datetime.now(timezone.utc).isoformat()

    conn.execute(
        """
        INSERT INTO krisp_documents(id, title, date, url, speakers, sha256, document, indexed_utc)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            title=excluded.title,
            date=excluded.date,
            url=excluded.url,
            speakers=excluded.speakers,
            sha256=excluded.sha256,
            document=excluded.document,
            indexed_utc=excluded.indexed_utc
        """,
        (doc_id, title, date, url, speakers, digest, document, indexed_utc),
    )
    conn.execute("DELETE FROM krisp_documents_fts WHERE document_id = ?", (doc_id,))
    conn.execute(
        "INSERT INTO krisp_documents_fts(document_id, title, date, speakers, document) VALUES (?, ?, ?, ?, ?)",
        (doc_id, title, date, speakers, searchable),
    )

    old_ids = [row[0] for row in conn.execute("SELECT id FROM krisp_chunks WHERE document_id = ?", (doc_id,))]
    for chunk_id in old_ids:
        conn.execute("DELETE FROM krisp_chunks_fts WHERE rowid = ?", (chunk_id,))
    conn.execute("DELETE FROM krisp_chunks WHERE document_id = ?", (doc_id,))

    for index, (start, end, chunk) in enumerate(chunk_text(searchable)):
        cur = conn.execute(
            """
            INSERT INTO krisp_chunks(document_id, chunk_index, text, char_start, char_end)
            VALUES (?, ?, ?, ?, ?)
            """,
            (doc_id, index, chunk, start, end),
        )
        conn.execute("INSERT INTO krisp_chunks_fts(rowid, text) VALUES (?, ?)", (int(cur.lastrowid), chunk))
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--input", required=True, help="JSON exported from the Krisp connector.")
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    items = normalize_payload(payload)
    conn = sqlite3.connect(args.db)
    setup_krisp_db(conn)
    imported = 0
    skipped = 0
    with conn:
        for item in items:
            if import_document(conn, item):
                imported += 1
            else:
                skipped += 1
    chunks = conn.execute("SELECT COUNT(*) FROM krisp_chunks").fetchone()[0]
    docs = conn.execute("SELECT COUNT(*) FROM krisp_documents").fetchone()[0]
    print(f"Imported/updated {imported} Krisp documents; skipped {skipped}.")
    print(f"Krisp index now has {docs} documents and {chunks} chunks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

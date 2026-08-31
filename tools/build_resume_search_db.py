import argparse
import csv
import hashlib
import html
import os
import re
import sqlite3
import sys
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Iterable


WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9.+#&/-]{1,}")
EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
PHONE_RE = re.compile(r"(?:\+?\d[\d .()/-]{7,}\d)")
HTML_TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class ExtractedText:
    text: str
    status: str
    error: str = ""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_read_text(path: Path) -> ExtractedText:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return ExtractedText(data.decode(encoding, errors="replace"), "ok")
        except Exception:
            continue
    return ExtractedText("", "failed", "could not decode text")


def extract_docx(path: Path) -> ExtractedText:
    try:
        parts: list[str] = []
        with zipfile.ZipFile(path) as zf:
            names = [
                n
                for n in zf.namelist()
                if n.startswith("word/")
                and n.endswith(".xml")
                and (
                    n == "word/document.xml"
                    or n.startswith("word/header")
                    or n.startswith("word/footer")
                )
            ]
            for name in names:
                root = ET.fromstring(zf.read(name))
                for node in root.iter():
                    if node.tag.endswith("}t") and node.text:
                        parts.append(node.text)
                    elif node.tag.endswith("}p"):
                        parts.append("\n")
        text = " ".join(parts)
        return ExtractedText(normalize_text(text), "ok" if text.strip() else "empty")
    except Exception as exc:
        return ExtractedText("", "failed", str(exc))


def extract_xlsx_names(path: Path) -> ExtractedText:
    try:
        parts: list[str] = []
        with zipfile.ZipFile(path) as zf:
            for name in zf.namelist():
                if name.startswith("xl/sharedStrings") and name.endswith(".xml"):
                    root = ET.fromstring(zf.read(name))
                    for node in root.iter():
                        if node.tag.endswith("}t") and node.text:
                            parts.append(node.text)
        text = " ".join(parts)
        return ExtractedText(normalize_text(text), "ok" if text.strip() else "empty")
    except Exception as exc:
        return ExtractedText("", "failed", str(exc))


def extract_rtf(path: Path) -> ExtractedText:
    try:
        raw = path.read_text(encoding="cp1252", errors="replace")
        text = re.sub(r"\\'[0-9a-fA-F]{2}", " ", raw)
        text = re.sub(r"\\[a-zA-Z]+\d* ?", " ", text)
        text = re.sub(r"[{}]", " ", text)
        return ExtractedText(normalize_text(text), "ok" if text.strip() else "empty")
    except Exception as exc:
        return ExtractedText("", "failed", str(exc))


def extract_html(path: Path) -> ExtractedText:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
        text = HTML_TAG_RE.sub(" ", raw)
        text = html.unescape(text)
        return ExtractedText(normalize_text(text), "ok" if text.strip() else "empty")
    except Exception as exc:
        return ExtractedText("", "failed", str(exc))


def extract_email(path: Path) -> ExtractedText:
    try:
        with path.open("rb") as f:
            msg = BytesParser(policy=policy.default).parse(f)
        parts: list[str] = []
        for part in msg.walk():
            if part.is_multipart():
                continue
            content_type = part.get_content_type()
            if content_type in {"text/plain", "text/html"}:
                payload = part.get_content()
                if content_type == "text/html":
                    payload = HTML_TAG_RE.sub(" ", str(payload))
                parts.append(str(payload))
        text = normalize_text(" ".join(parts))
        return ExtractedText(text, "ok" if text else "empty")
    except Exception as exc:
        return ExtractedText("", "failed", str(exc))


def extract_pdf_placeholder(path: Path) -> ExtractedText:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        parts: list[str] = []
        for page in reader.pages:
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                continue
        text = normalize_text(" ".join(parts))
        return ExtractedText(text, "ok" if text else "empty")
    except Exception as exc:
        return ExtractedText("", "failed", str(exc))


def extract_doc_placeholder(path: Path) -> ExtractedText:
    return ExtractedText("", "not_extracted", "legacy .doc text extractor not configured")


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def filename_terms(path: Path, root: Path) -> str:
    rel = str(path.relative_to(root))
    stem = path.stem
    parts = re.split(r"[^A-Za-z0-9+#.]+", rel + " " + stem)
    return " ".join(p for p in parts if p)


def extract_text(path: Path) -> ExtractedText:
    ext = path.suffix.lower()
    try:
        if ext in {".txt", ".md", ".csv", ".css"}:
            result = safe_read_text(path)
            result.text = normalize_text(result.text)
            return result
        if ext == ".docx":
            return extract_docx(path)
        if ext == ".xlsx":
            return extract_xlsx_names(path)
        if ext in {".html", ".htm"}:
            return extract_html(path)
        if ext == ".rtf":
            return extract_rtf(path)
        if ext in {".eml", ".msg"}:
            return extract_email(path)
        if ext == ".pdf":
            return extract_pdf_placeholder(path)
        if ext == ".doc":
            return extract_doc_placeholder(path)
        return ExtractedText("", "unsupported", f"unsupported extension {ext}")
    except Exception as exc:
        return ExtractedText("", "failed", str(exc))


def infer_tags(path: Path, text: str) -> str:
    haystack = (str(path) + " " + text[:5000]).lower()
    tags = []
    patterns = {
        "resume": r"\b(resume|cv|curriculum vitae)\b",
        "cover_letter": r"\bcover letter\b",
        "portfolio": r"\b(portfolio|work samples?)\b",
        "application": r"\b(application|candidate|shortlist)\b",
        "recruiting": r"\b(recruit|interview|position|job description|hiring)\b",
        "job_description": r"\b(job description|position description|role description|\bjd\b|jd-posting)\b",
        "linkedin": r"\blinkedin\b",
    }
    for tag, pattern in patterns.items():
        if re.search(pattern, haystack):
            tags.append(tag)
    return ",".join(tags)


def setup_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY,
            path TEXT NOT NULL UNIQUE,
            relative_path TEXT NOT NULL,
            filename TEXT NOT NULL,
            extension TEXT NOT NULL,
            bytes INTEGER NOT NULL,
            modified_utc TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            text_status TEXT NOT NULL,
            text_error TEXT NOT NULL,
            emails TEXT NOT NULL,
            phones TEXT NOT NULL,
            tags TEXT NOT NULL,
            text TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
            filename,
            relative_path,
            tags,
            text
        );
        CREATE TABLE IF NOT EXISTS run_info (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            char_start INTEGER NOT NULL,
            char_end INTEGER NOT NULL,
            FOREIGN KEY(file_id) REFERENCES files(id)
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            text,
            content='chunks',
            content_rowid='id'
        );
        """
    )


def upsert_file(conn: sqlite3.Connection, row: dict[str, object]) -> int:
    conn.execute(
        """
        INSERT INTO files (
            path, relative_path, filename, extension, bytes, modified_utc,
            sha256, text_status, text_error, emails, phones, tags, text
        )
        VALUES (
            :path, :relative_path, :filename, :extension, :bytes, :modified_utc,
            :sha256, :text_status, :text_error, :emails, :phones, :tags, :text
        )
        ON CONFLICT(path) DO UPDATE SET
            relative_path=excluded.relative_path,
            filename=excluded.filename,
            extension=excluded.extension,
            bytes=excluded.bytes,
            modified_utc=excluded.modified_utc,
            sha256=excluded.sha256,
            text_status=excluded.text_status,
            text_error=excluded.text_error,
            emails=excluded.emails,
            phones=excluded.phones,
            tags=excluded.tags,
            text=excluded.text
        """,
        row,
    )
    return int(conn.execute("SELECT id FROM files WHERE path = ?", (row["path"],)).fetchone()[0])


def refresh_fts(conn: sqlite3.Connection, rowid: int, row: dict[str, object]) -> None:
    conn.execute("DELETE FROM files_fts WHERE rowid = ?", (rowid,))
    conn.execute(
        "INSERT INTO files_fts(rowid, filename, relative_path, tags, text) VALUES (?, ?, ?, ?, ?)",
        (rowid, row["filename"], row["relative_path"], row["tags"], row["text"]),
    )


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


def refresh_chunks(conn: sqlite3.Connection, file_id: int, text: str) -> None:
    old_ids = [row[0] for row in conn.execute("SELECT id FROM chunks WHERE file_id = ?", (file_id,))]
    for chunk_id in old_ids:
        conn.execute("DELETE FROM chunks_fts WHERE rowid = ?", (chunk_id,))
    conn.execute("DELETE FROM chunks WHERE file_id = ?", (file_id,))
    for index, (start, end, chunk) in enumerate(chunk_text(text)):
        cur = conn.execute(
            """
            INSERT INTO chunks(file_id, chunk_index, text, char_start, char_end)
            VALUES (?, ?, ?, ?, ?)
            """,
            (file_id, index, chunk, start, end),
        )
        chunk_id = int(cur.lastrowid)
        conn.execute("INSERT INTO chunks_fts(rowid, text) VALUES (?, ?)", (chunk_id, chunk))


def iter_files(root: Path) -> Iterable[Path]:
    for base, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in {".git", "__MACOSX"}]
        for filename in filenames:
            yield Path(base) / filename


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--db", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    db_path = Path(args.db)
    report_path = Path(args.report)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    files = list(iter_files(root))
    conn = sqlite3.connect(db_path)
    setup_db(conn)
    conn.execute("DELETE FROM files")
    conn.execute("DELETE FROM files_fts")
    conn.execute("DELETE FROM chunks")
    conn.execute("DELETE FROM chunks_fts")

    statuses: dict[str, int] = {}
    with report_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "path",
                "relative_path",
                "extension",
                "bytes",
                "sha256",
                "text_status",
                "text_error",
                "emails",
                "phones",
                "tags",
            ],
        )
        writer.writeheader()
        for index, path in enumerate(files, 1):
            rel = str(path.relative_to(root))
            try:
                digest = sha256_file(path)
                extracted = extract_text(path)
                base_terms = filename_terms(path, root)
                searchable_text = normalize_text(base_terms + " " + extracted.text)
                emails = ";".join(sorted(set(EMAIL_RE.findall(searchable_text))))
                phones = ";".join(sorted(set(p.strip() for p in PHONE_RE.findall(searchable_text))))
                tags = infer_tags(path, searchable_text)
                stat = path.stat()
                row = {
                    "path": str(path),
                    "relative_path": rel,
                    "filename": path.name,
                    "extension": path.suffix.lower(),
                    "bytes": stat.st_size,
                    "modified_utc": str(stat.st_mtime),
                    "sha256": digest,
                    "text_status": extracted.status,
                    "text_error": extracted.error,
                    "emails": emails,
                    "phones": phones,
                    "tags": tags,
                    "text": searchable_text,
                }
                rowid = upsert_file(conn, row)
                refresh_fts(conn, rowid, row)
                refresh_chunks(conn, rowid, searchable_text)
                writer.writerow({k: row[k] for k in writer.fieldnames})
                statuses[extracted.status] = statuses.get(extracted.status, 0) + 1
            except Exception as exc:
                statuses["failed"] = statuses.get("failed", 0) + 1
                writer.writerow(
                    {
                        "path": str(path),
                        "relative_path": rel,
                        "extension": path.suffix.lower(),
                        "bytes": "",
                        "sha256": "",
                        "text_status": "failed",
                        "text_error": str(exc),
                        "emails": "",
                        "phones": "",
                        "tags": "",
                    }
                )
            if index % 250 == 0:
                conn.commit()
                print(f"indexed {index}/{len(files)}", flush=True)

    conn.execute("INSERT OR REPLACE INTO run_info(key, value) VALUES('root', ?)", (str(root),))
    conn.execute("INSERT OR REPLACE INTO run_info(key, value) VALUES('file_count', ?)", (str(len(files)),))
    conn.commit()
    conn.close()

    print(f"DB\t{db_path}")
    print(f"REPORT\t{report_path}")
    print("STATUS_SUMMARY")
    for status, count in sorted(statuses.items()):
        print(f"{status}\t{count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

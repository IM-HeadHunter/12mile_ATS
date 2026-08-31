import argparse
import csv
import hashlib
import json
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


DEFAULT_DB = r"D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Resume Search DB\resumes.sqlite"
DEFAULT_DEST_ROOT = r"D:\Work\Recruiting\Resumes"
DEFAULT_REPORT_DIR = r"D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Public Profile Import"


def safe_name(value: str, limit: int = 110) -> str:
    value = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", " ", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return (value[:limit].rstrip(" .") or "untitled")


def name_key(value: str) -> str:
    return re.sub(r"[^a-z]", "", value.lower())


def setup_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS candidate_public_profiles (
            id INTEGER PRIMARY KEY,
            url TEXT NOT NULL UNIQUE,
            candidate_id INTEGER,
            candidate_name TEXT NOT NULL,
            platform TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            evidence TEXT NOT NULL,
            confidence TEXT NOT NULL,
            review_status TEXT NOT NULL,
            source_query TEXT NOT NULL,
            note_path TEXT NOT NULL,
            imported_utc TEXT NOT NULL
        )
        """
    )


def find_candidate(conn: sqlite3.Connection, entry: dict) -> sqlite3.Row | None:
    if str(entry.get("review_status") or "").lower() in {"review_needed", "unmatched", "rejected"}:
        return None
    candidate_id = entry.get("candidate_id")
    expected = str(entry.get("candidate_name") or "").strip()
    if candidate_id:
        row = conn.execute(
            """
            SELECT c.id, c.canonical_name, c.emails, c.file_count, f.path AS best_path
            FROM candidates c
            LEFT JOIN files f ON f.id = c.best_file_id
            WHERE c.id = ?
            """,
            (candidate_id,),
        ).fetchone()
        if row and expected:
            expected_key = name_key(expected)
            actual_key = name_key(str(row["canonical_name"]))
            if expected_key in actual_key or actual_key in expected_key:
                return row
        elif row:
            return row

    if not expected:
        return None
    return conn.execute(
        """
        SELECT c.id, c.canonical_name, c.emails, c.file_count, f.path AS best_path
        FROM candidates c
        LEFT JOIN files f ON f.id = c.best_file_id
        WHERE lower(c.canonical_name) = lower(?)
        ORDER BY c.file_count DESC
        LIMIT 1
        """,
        (expected,),
    ).fetchone()


def format_list(value: object) -> str:
    if isinstance(value, list):
        lines = [str(item).strip() for item in value if str(item).strip()]
        return "\n".join(f"- {line}" for line in lines) if lines else "_None recorded._"
    text = str(value or "").strip()
    return text or "_None recorded._"


def build_markdown(entry: dict, candidate: sqlite3.Row | None) -> str:
    candidate_name = str(entry.get("candidate_name") or "").strip()
    platform = str(entry.get("platform") or "public web").strip()
    title = str(entry.get("title") or entry.get("url") or "Public profile").strip()
    candidate_id = str(candidate["id"]) if candidate else ""
    canonical = str(candidate["canonical_name"]) if candidate else ""
    best_path = str(candidate["best_path"] or "") if candidate else ""
    return "\n".join(
        [
            f"# Public Profile Note - {title}",
            "",
            f"Candidate: {candidate_name}",
            f"Matched candidate: {'Yes' if candidate else 'No'}",
            f"Candidate DB ID: {candidate_id}",
            f"Candidate DB name: {canonical}",
            f"Best resume path: {best_path}",
            f"Platform: {platform}",
            f"URL: {entry.get('url', '')}",
            f"Title: {title}",
            f"Confidence: {entry.get('confidence', '')}",
            f"Review status: {entry.get('review_status', '')}",
            f"Source query: {entry.get('source_query', '')}",
            f"Imported UTC: {datetime.now(UTC).isoformat()}",
            "Source: Public web profile",
            "",
            "## Summary",
            str(entry.get("summary") or "").strip() or "_No summary recorded._",
            "",
            "## Evidence",
            format_list(entry.get("evidence")),
            "",
            "## Notes",
            str(entry.get("notes") or "").strip() or "_None recorded._",
            "",
        ]
    )


def note_destination(dest_root: Path, entry: dict, candidate: sqlite3.Row | None) -> Path:
    platform = safe_name(str(entry.get("platform") or "public-web"), 40)
    title = safe_name(str(entry.get("title") or entry.get("url") or "public profile"), 90)
    url_hash = hashlib.sha256(str(entry.get("url") or title).encode("utf-8")).hexdigest()[:12]
    filename = f"{platform} - {title} - {url_hash}.md"
    if candidate and candidate["best_path"]:
        best_parent = Path(str(candidate["best_path"])).parent
        if best_parent == dest_root:
            return dest_root / safe_name(str(entry.get("candidate_name") or candidate["canonical_name"])) / "Public Profile Notes" / filename
        return best_parent / "Public Profile Notes" / filename
    if str(entry.get("review_status") or "").lower() in {"approved", "profile_first", "create_candidate"}:
        return dest_root / safe_name(str(entry.get("candidate_name") or "Unknown Candidate")) / "Public Profile Notes" / filename
    return dest_root / "Public Profile Notes - Review Needed" / safe_name(str(entry.get("candidate_name") or "Unknown Candidate")) / filename


def import_status(entry: dict, candidate: sqlite3.Row | None) -> str:
    if candidate:
        return "matched"
    if str(entry.get("review_status") or "").lower() in {"approved", "profile_first", "create_candidate"}:
        return "profile_first"
    return "review_needed"


def normalize_payload(payload: object) -> list[dict]:
    if isinstance(payload, dict) and isinstance(payload.get("profiles"), list):
        return payload["profiles"]
    if isinstance(payload, list):
        return payload
    raise ValueError("Expected a list or an object with a profiles list.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--dest-root", default=DEFAULT_DEST_ROOT)
    parser.add_argument("--report-dir", default=DEFAULT_REPORT_DIR)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    entries = normalize_payload(json.loads(Path(args.input).read_text(encoding="utf-8")))
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    setup_db(conn)
    dest_root = Path(args.dest_root)
    report_dir = Path(args.report_dir)
    report_path = report_dir / f"Public-Profile-Import-{datetime.now():%Y%m%d-%H%M%S}.csv"
    rows = []

    for entry in entries:
        candidate = find_candidate(conn, entry)
        destination = note_destination(dest_root, entry, candidate)
        status = import_status(entry, candidate)
        if not args.dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(build_markdown(entry, candidate), encoding="utf-8")
            conn.execute(
                """
                INSERT INTO candidate_public_profiles(
                    url, candidate_id, candidate_name, platform, title, summary,
                    evidence, confidence, review_status, source_query, note_path, imported_utc
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    candidate_id=excluded.candidate_id,
                    candidate_name=excluded.candidate_name,
                    platform=excluded.platform,
                    title=excluded.title,
                    summary=excluded.summary,
                    evidence=excluded.evidence,
                    confidence=excluded.confidence,
                    review_status=excluded.review_status,
                    source_query=excluded.source_query,
                    note_path=excluded.note_path,
                    imported_utc=excluded.imported_utc
                """,
                (
                    entry.get("url", ""),
                    candidate["id"] if candidate else None,
                    entry.get("candidate_name", ""),
                    entry.get("platform", ""),
                    entry.get("title", ""),
                    entry.get("summary", ""),
                    json.dumps(entry.get("evidence") or [], ensure_ascii=False),
                    entry.get("confidence", ""),
                    entry.get("review_status", ""),
                    entry.get("source_query", ""),
                    str(destination),
                    datetime.now(UTC).isoformat(),
                ),
            )
        rows.append(
            {
                "candidate_name": entry.get("candidate_name", ""),
                "platform": entry.get("platform", ""),
                "url": entry.get("url", ""),
                "candidate_id": candidate["id"] if candidate else "",
                "candidate_db_name": candidate["canonical_name"] if candidate else "",
                "destination": str(destination),
                "status": status,
                "confidence": entry.get("confidence", ""),
                "review_status": entry.get("review_status", ""),
            }
        )

    if not args.dry_run:
        report_dir.mkdir(parents=True, exist_ok=True)
        with report_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        conn.commit()
        print(f"Report: {report_path}")

    for row in rows:
        print(f"{row['status']}: {row['candidate_name']} {row['platform']} -> {row['destination']}")
    print(f"Matched {sum(1 for r in rows if r['status'] == 'matched')} of {len(rows)} profile notes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import argparse
import csv
import json
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


DEFAULT_DB = r"D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Resume Search DB\resumes.sqlite"
DEFAULT_DEST_ROOT = r"D:\Work\Recruiting\Resumes"
DEFAULT_REPORT_DIR = r"D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Krisp Notes Import"


def safe_name(value: str, limit: int = 120) -> str:
    value = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", " ", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return (value[:limit].rstrip(" .") or "untitled")


def setup_link_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS candidate_krisp_notes (
            meeting_id TEXT PRIMARY KEY,
            candidate_id INTEGER,
            candidate_name TEXT NOT NULL,
            title TEXT NOT NULL,
            meeting_date TEXT NOT NULL,
            url TEXT NOT NULL,
            note_path TEXT NOT NULL,
            confidence TEXT NOT NULL,
            imported_utc TEXT NOT NULL
        )
        """
    )


def find_candidate(conn: sqlite3.Connection, note: dict) -> sqlite3.Row | None:
    if str(note.get("confidence") or "").startswith("review_needed"):
        return None

    expected_name = str(note.get("candidate_name") or "").strip()
    candidate_id = note.get("candidate_id")
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
        if row and expected_name:
            expected_key = re.sub(r"[^a-z]", "", expected_name.lower())
            actual_key = re.sub(r"[^a-z]", "", str(row["canonical_name"]).lower())
            if expected_key in actual_key or actual_key in expected_key:
                return row

    name = expected_name
    if not name:
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
        (name,),
    ).fetchone()


def format_list(items: object) -> str:
    if not items:
        return "_None recorded._\n"
    lines = []
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                title = str(item.get("title") or item.get("description") or "").strip()
                assignee = str(item.get("assignee") or "").strip()
                completed = item.get("completed")
                suffix = ""
                if assignee:
                    suffix += f" Assignee: {assignee}."
                if completed is not None:
                    suffix += f" Completed: {completed}."
                if title:
                    lines.append(f"- {title}{suffix}")
            else:
                text = str(item).strip()
                if text:
                    lines.append(f"- {text}")
    return "\n".join(lines) + ("\n" if lines else "_None recorded._\n")


def format_detail(items: object) -> str:
    if not items:
        return ""
    if not isinstance(items, list):
        return str(items).strip()
    sections = []
    for item in items:
        if isinstance(item, dict):
            title = str(item.get("title") or "").strip()
            desc = str(item.get("description") or "").strip()
            if title or desc:
                sections.append(f"## {title}\n{desc}".strip())
        else:
            text = str(item).strip()
            if text:
                sections.append(text)
    return "\n\n".join(sections)


def build_markdown(note: dict, candidate: sqlite3.Row | None) -> str:
    title = str(note.get("title") or "Krisp meeting").strip()
    candidate_name = str(note.get("candidate_name") or "").strip()
    speakers = note.get("speakers") or []
    speakers_text = "; ".join(str(s) for s in speakers) if isinstance(speakers, list) else str(speakers)
    details = format_detail(note.get("detailed_summary"))
    key_points = format_list(note.get("key_points"))
    action_items = format_list(note.get("action_items"))
    matched = "No"
    candidate_id = ""
    canonical = ""
    best_path = ""
    if candidate:
        matched = "Yes"
        candidate_id = str(candidate["id"])
        canonical = str(candidate["canonical_name"])
        best_path = str(candidate["best_path"] or "")

    parts = [
        f"# Krisp Notes - {title}",
        "",
        f"Candidate: {candidate_name}",
        f"Matched candidate: {matched}",
        f"Candidate DB ID: {candidate_id}",
        f"Candidate DB name: {canonical}",
        f"Best resume path: {best_path}",
        f"Krisp meeting ID: {note.get('meeting_id', '')}",
        f"Krisp URL: {note.get('url', '')}",
        f"Meeting date: {note.get('date', '')}",
        f"Speakers: {speakers_text}",
        f"Match confidence: {note.get('confidence', '')}",
        "Source: Krisp",
        "",
        "## Key Points",
        key_points,
        "## Action Items",
        action_items,
    ]
    if details:
        parts.extend(["## Detailed Summary", details])
    return "\n".join(parts).strip() + "\n"


def note_destination(dest_root: Path, note: dict, candidate: sqlite3.Row | None) -> Path:
    date = str(note.get("date") or "")[:10] or "undated"
    title = safe_name(str(note.get("title") or "Krisp meeting"))
    meeting_id = safe_name(str(note.get("meeting_id") or "unknown"), 40)
    filename = f"{date} - {title} - {meeting_id}.md"
    if candidate and candidate["best_path"]:
        best_parent = Path(str(candidate["best_path"])).parent
        if best_parent == dest_root:
            return dest_root / safe_name(str(note.get("candidate_name") or candidate["canonical_name"])) / "Krisp Notes" / filename
        return best_parent / "Krisp Notes" / filename
    return dest_root / "Krisp Notes - Review Needed" / safe_name(str(note.get("candidate_name") or "Unknown Candidate")) / filename


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--dest-root", default=DEFAULT_DEST_ROOT)
    parser.add_argument("--report-dir", default=DEFAULT_REPORT_DIR)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    notes = json.loads(Path(args.input).read_text(encoding="utf-8"))
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    setup_link_table(conn)
    dest_root = Path(args.dest_root)
    report_dir = Path(args.report_dir)
    report_path = report_dir / f"Krisp-Candidate-Note-Import-{datetime.now():%Y%m%d-%H%M%S}.csv"
    rows = []

    for note in notes:
        candidate = find_candidate(conn, note)
        destination = note_destination(dest_root, note, candidate)
        status = "matched" if candidate else "review_needed"
        if not args.dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                destination.write_text(build_markdown(note, candidate), encoding="utf-8")
            status = status if destination.exists() else "write_failed"
            if candidate:
                conn.execute(
                    """
                    INSERT INTO candidate_krisp_notes(
                        meeting_id, candidate_id, candidate_name, title, meeting_date,
                        url, note_path, confidence, imported_utc
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(meeting_id) DO UPDATE SET
                        candidate_id=excluded.candidate_id,
                        candidate_name=excluded.candidate_name,
                        title=excluded.title,
                        meeting_date=excluded.meeting_date,
                        url=excluded.url,
                        note_path=excluded.note_path,
                        confidence=excluded.confidence,
                        imported_utc=excluded.imported_utc
                    """,
                    (
                        note.get("meeting_id", ""),
                        candidate["id"],
                        note.get("candidate_name", ""),
                        note.get("title", ""),
                        note.get("date", ""),
                        note.get("url", ""),
                        str(destination),
                        note.get("confidence", ""),
                        datetime.now(UTC).isoformat(),
                    ),
                )
        rows.append(
            {
                "meeting_id": note.get("meeting_id", ""),
                "title": note.get("title", ""),
                "date": note.get("date", ""),
                "candidate_name": note.get("candidate_name", ""),
                "candidate_id": candidate["id"] if candidate else "",
                "candidate_db_name": candidate["canonical_name"] if candidate else "",
                "destination": str(destination),
                "status": status,
                "confidence": note.get("confidence", ""),
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
        print(f"{row['status']}: {row['candidate_name']} -> {row['destination']}")
    print(f"Matched {sum(1 for r in rows if r['status'] == 'matched')} of {len(rows)} notes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import argparse
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path


DEFAULT_DB = r"D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Resume Search DB\resumes.sqlite"

NAME_RE = re.compile(r"\b([A-Z][a-z]{1,24})\s+([A-Z][a-z]{1,24})\b")
INITIAL_NAME_RE = re.compile(r"\b([A-Z][a-z]{1,24})\s+([A-Z])\b")
EMAIL_SPLIT_RE = re.compile(r"[;\s,]+")
NOISE_WORDS = {
    "archive",
    "resume",
    "resumes",
    "cv",
    "candidate",
    "candidates",
    "selected",
    "applicant",
    "applicants",
    "application",
    "applications",
    "package",
    "packages",
    "profile",
    "linkedin",
    "indeed",
    "final",
    "updated",
    "upadted",
    "copy",
    "new",
    "old",
    "the",
    "work",
    "senior",
    "junior",
    "principal",
    "engineer",
    "developer",
    "data",
    "big",
    "delta",
    "lake",
    "azure",
    "synapse",
    "event",
    "hubs",
    "fabric",
    "onelake",
    "databricks",
    "redshift",
    "snowflake",
    "spark",
    "architect",
    "manager",
    "director",
    "specialist",
    "consultant",
    "coordinator",
    "administrator",
    "assistant",
    "officer",
    "lead",
    "cloud",
    "software",
    "systems",
    "system",
    "solutions",
    "solution",
    "toronto",
    "ontario",
    "waterloo",
    "kitchener",
    "canada",
    "armstrong",
    "aixal",
    "mailstore",
    "outlook",
    "inbox",
    "message",
    "import",
    "systemwide",
    "krisp",
    "notes",
    "note",
    "meeting",
    "interview",
    "screen",
    "introduction",
    "public",
    "web",
    "github",
    "stack",
    "overflow",
    "stackoverflow",
}
BAD_EMAIL_PARTS = {"noreply", "no-reply", "donotreply", "do-not-reply", "calendar-notification"}
NOTE_CANDIDATE_RE = re.compile(
    r"\bCandidate:\s*([A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){0,3})(?=\s+Matched candidate:|\s+Candidate DB ID:|$)"
)
JOB_DESCRIPTION_RE = re.compile(
    r"(?i)\b("
    r"job\s+description|position\s+description|role\s+description|"
    r"jd(?:\b|[-_ ]posting)|job\s+posting|"
    r"apply\s+directly\s+on\s+glassdoor|apply\s+now\s+share\s+on\s+linkedin|"
    r"job\s+types:\s*full-time|salary:\s*\$|"
    r"global\s+security\s+architect\s+jd|global\s+dev\s+lead"
    r")\b"
)
SUPPORTING_DOC_RE = re.compile(
    r"(?i)\b("
    r"employment\s+verification|reference\s+check|"
    r"independent\s+contractor\s+agreement|contractor\s+agreement|"
    r"signed\s+agreement|new\s+agreement|employment\s+agreement|"
    r"offer\s+signed|signed\s+offer|offer\s+letter|"
    r"invoice|statement\s+of\s+work|sow|msa|"
    r"org\s+charts?|organizational\s+charts?|"
    r"placements?\.csv|armstrong\s+placements|"
    r"\b60\s+days\.csv\b|\bsent\.csv\b"
    r")\b"
)


def setup_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY,
            candidate_key TEXT NOT NULL UNIQUE,
            canonical_name TEXT NOT NULL,
            emails TEXT NOT NULL,
            phones TEXT NOT NULL,
            tags TEXT NOT NULL,
            file_count INTEGER NOT NULL,
            best_file_id INTEGER,
            latest_modified_utc TEXT NOT NULL,
            text TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS candidate_files (
            candidate_id INTEGER NOT NULL,
            file_id INTEGER NOT NULL UNIQUE,
            PRIMARY KEY(candidate_id, file_id),
            FOREIGN KEY(candidate_id) REFERENCES candidates(id),
            FOREIGN KEY(file_id) REFERENCES files(id)
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS candidates_fts USING fts5(
            canonical_name,
            emails,
            phones,
            tags,
            text
        );
        """
    )


def clean_stem(filename: str) -> str:
    stem = Path(filename).stem
    stem = re.sub(r"([a-z])([A-Z])", r"\1 \2", stem)
    stem = re.sub(r"[_]+", " ", stem)
    stem = re.sub(r"\([^)]*\)", " ", stem)
    stem = re.sub(r"\[[^]]*\]", " ", stem)
    stem = re.split(r"\s+--\s+|\s+-\s+|\s+\|\s+", stem)[0]
    stem = re.sub(r"(?i)\b(resume|cv|curriculum vitae|updated|upadted|final|copy)\b", " ", stem)
    return re.sub(r"\s+", " ", stem).strip()


def normalize_name(name: str) -> str:
    parts = [p for p in re.split(r"\s+", name.strip()) if p]
    return " ".join(part[:1].upper() + part[1:].lower() for part in parts)


def name_key(name: str) -> str:
    return re.sub(r"[^a-z]", "", name.lower())


def usable_email(email: str) -> bool:
    lower = email.lower()
    if "@" not in lower:
        return False
    local, domain = lower.split("@", 1)
    if any(part in local for part in BAD_EMAIL_PARTS):
        return False
    if domain.endswith(("microsoft.com", "google.com", "slack.com", "amazon.ca")):
        return False
    return True


def extract_emails(value: str) -> list[str]:
    emails = [e.strip().lower() for e in EMAIL_SPLIT_RE.split(value or "") if e.strip()]
    return sorted({e for e in emails if usable_email(e)})


def infer_name(row: sqlite3.Row) -> str:
    note_match = NOTE_CANDIDATE_RE.search(row["text"] or "")
    if note_match:
        return normalize_name(note_match.group(1))

    review_match = re.search(r"(?i)Krisp Notes - Review Needed[\\/]+([^\\/]+)", row["path"] or "")
    if review_match:
        return normalize_name(review_match.group(1))

    stem = clean_stem(row["filename"])
    stem_match = NAME_RE.search(stem)
    if stem_match:
        return normalize_name(stem_match.group(0))
    initial_match = INITIAL_NAME_RE.search(stem)
    if initial_match:
        return normalize_name(initial_match.group(0))

    candidates: Counter[str] = Counter()
    for first, last in NAME_RE.findall((row["text"] or "")[:2500]):
        if first.lower() in NOISE_WORDS or last.lower() in NOISE_WORDS:
            continue
        if len(first) <= 2 or len(last) <= 2:
            continue
        name = normalize_name(f"{first} {last}")
        candidates[name] += 1
    if candidates:
        return candidates.most_common(1)[0][0]

    tokens = [
        token
        for token in re.split(r"[^A-Za-z]+", stem)
        if len(token) > 1 and token.lower() not in NOISE_WORDS
    ]
    if len(tokens) >= 2:
        return normalize_name(" ".join(tokens[:2]))
    return stem or row["filename"]


def build_candidate_key(row: sqlite3.Row, name: str, emails: list[str]) -> str:
    lower_path = (row["path"] or "").lower()
    if "krisp notes" in lower_path or "public profile notes" in lower_path:
        return f"name:{name_key(name)}"
    if emails:
        return f"email:{emails[0]}"
    phones = [p for p in (row["phones"] or "").split(";") if p and not re.fullmatch(r"\d{4}-\d{4}", p)]
    if phones:
        return f"phone:{phones[0]}"
    return f"name:{name_key(name)}"


def is_job_description(row: sqlite3.Row) -> bool:
    haystack = " ".join(
        str(row[key] or "")
        for key in ("filename", "path", "relative_path", "tags", "text")
        if key in row.keys()
    )
    return bool(JOB_DESCRIPTION_RE.search(haystack))


def is_supporting_doc(row: sqlite3.Row) -> bool:
    haystack = " ".join(
        str(row[key] or "")
        for key in ("filename", "path", "relative_path", "tags")
        if key in row.keys()
    )
    return bool(SUPPORTING_DOC_RE.search(haystack))


def is_review_needed_note(row: sqlite3.Row) -> bool:
    lower_path = (row["path"] or "").lower()
    text = (row["text"] or "").lower()
    return (
        "krisp notes - review needed" in lower_path
        or "public profile notes - review needed" in lower_path
        or "review status: review_needed" in text
        or "matched candidate: no" in text and "review_needed" in text
    )


def is_candidate_material(row: sqlite3.Row) -> bool:
    lower_path = (row["path"] or "").lower()
    lower_name = (row["filename"] or "").lower()
    tags = (row["tags"] or "").lower()
    if is_job_description(row) or is_supporting_doc(row) or is_review_needed_note(row):
        return False
    if "krisp notes" in lower_path or "public profile notes" in lower_path:
        return True
    if any(tag in tags.split(",") for tag in ("resume", "linkedin", "portfolio", "application")):
        return True
    if re.search(r"(?i)\b(resume|cv|curriculum vitae)\b", lower_name):
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=DEFAULT_DB)
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    setup_db(conn)
    rows = conn.execute(
        """
        SELECT id, filename, path, relative_path, modified_utc, emails, phones, tags, text
        FROM files
        WHERE tags LIKE '%resume%'
           OR tags LIKE '%application%'
           OR lower(filename) LIKE '%resume%'
           OR lower(filename) LIKE '%cv%'
           OR lower(path) LIKE '%resumes%'
        """
    ).fetchall()
    rows = [row for row in rows if is_candidate_material(row)]

    groups: dict[str, list[sqlite3.Row]] = defaultdict(list)
    names: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        name = infer_name(row)
        emails = extract_emails(row["emails"])
        key = build_candidate_key(row, name, emails)
        groups[key].append(row)
        names[key][name] += 1

    # Merge fallback and phone-only groups into email-backed groups when the names match.
    # This handles normal resume version drift such as "Ryan Chase", "Ryan Chase -- Sr SDE",
    # and "Chase-Ryan-Resume" where only some versions expose an email address.
    name_to_contact_key = {}
    for key in groups:
        if key.startswith("email:"):
            name_to_contact_key[name_key(names[key].most_common(1)[0][0])] = key
    for key in list(groups):
        if key.startswith("email:"):
            continue
        canonical = names[key].most_common(1)[0][0]
        contact_key = name_to_contact_key.get(name_key(canonical))
        if contact_key and contact_key != key:
            groups[contact_key].extend(groups.pop(key))
            names[contact_key].update(names.pop(key))

    with conn:
        conn.execute("DELETE FROM candidates_fts")
        conn.execute("DELETE FROM candidate_files")
        conn.execute("DELETE FROM candidates")
        for key, files in groups.items():
            canonical_name = names[key].most_common(1)[0][0]
            emails = sorted({email for row in files for email in extract_emails(row["emails"])})
            phones = sorted({p for row in files for p in (row["phones"] or "").split(";") if p})
            tags = sorted({t for row in files for t in (row["tags"] or "").split(",") if t})
            best = max(files, key=lambda row: (len(row["text"] or ""), row["modified_utc"] or ""))
            latest = max(str(row["modified_utc"] or "") for row in files)
            text = "\n\n".join(
                f"File: {row['filename']}\nPath: {row['path']}\n{(row['text'] or '')[:4500]}"
                for row in files[:8]
            )
            cur = conn.execute(
                """
                INSERT INTO candidates(
                    candidate_key, canonical_name, emails, phones, tags,
                    file_count, best_file_id, latest_modified_utc, text
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    key,
                    canonical_name,
                    ";".join(emails),
                    ";".join(phones),
                    ",".join(tags),
                    len(files),
                    int(best["id"]),
                    latest,
                    text,
                ),
            )
            candidate_id = int(cur.lastrowid)
            for row in files:
                conn.execute(
                    "INSERT INTO candidate_files(candidate_id, file_id) VALUES (?, ?)",
                    (candidate_id, int(row["id"])),
                )
            conn.execute(
                "INSERT INTO candidates_fts(rowid, canonical_name, emails, phones, tags, text) VALUES (?, ?, ?, ?, ?, ?)",
                (candidate_id, canonical_name, ";".join(emails), ";".join(phones), ",".join(tags), text),
            )

    candidates = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
    linked_files = conn.execute("SELECT COUNT(*) FROM candidate_files").fetchone()[0]
    duplicate_groups = conn.execute("SELECT COUNT(*) FROM candidates WHERE file_count > 1").fetchone()[0]
    print(f"Built {candidates} candidate rollups from {linked_files} resume/application files.")
    print(f"{duplicate_groups} candidates have multiple underlying files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

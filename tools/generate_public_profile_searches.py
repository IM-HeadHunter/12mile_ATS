import argparse
import csv
import sqlite3
import urllib.parse
from pathlib import Path


DEFAULT_DB = r"D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Resume Search DB\resumes.sqlite"
DEFAULT_REPORT_DIR = r"D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Public Profile Import"


def make_search_url(query: str) -> str:
    return "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--out", default="")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--query", default="", help="Optional candidate name filter.")
    args = parser.parse_args()

    out = Path(args.out) if args.out else Path(DEFAULT_REPORT_DIR) / "public-profile-search-queue.csv"
    out.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    where = ""
    params: list[object] = []
    if args.query:
        where = "WHERE lower(canonical_name) LIKE ?"
        params.append("%" + args.query.lower() + "%")
    params.append(args.limit)
    rows = conn.execute(
        f"""
        SELECT id, canonical_name, emails, file_count
        FROM candidates
        {where}
        ORDER BY file_count DESC, canonical_name
        LIMIT ?
        """,
        params,
    ).fetchall()

    platforms = [
        ("LinkedIn public", 'site:linkedin.com/in "{name}"'),
        ("GitHub", 'site:github.com "{name}" developer OR engineer'),
        ("Stack Overflow", 'site:stackoverflow.com/users "{name}"'),
        ("Google Scholar", 'site:scholar.google.com "{name}" engineer OR software OR data'),
    ]
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["candidate_id", "candidate_name", "emails", "platform", "query", "search_url", "review_status"],
        )
        writer.writeheader()
        for row in rows:
            name = row["canonical_name"]
            for platform, template in platforms:
                query = template.format(name=name)
                writer.writerow(
                    {
                        "candidate_id": row["id"],
                        "candidate_name": name,
                        "emails": row["emails"],
                        "platform": platform,
                        "query": query,
                        "search_url": make_search_url(query),
                        "review_status": "pending_review",
                    }
                )
    print(f"Wrote {len(rows) * len(platforms)} search rows for {len(rows)} candidates: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

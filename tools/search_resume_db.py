import argparse
import sqlite3
from pathlib import Path


def search_files(conn: sqlite3.Connection, query: str, limit: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT
            files.filename,
            files.relative_path,
            files.path,
            files.extension,
            files.bytes,
            files.tags,
            files.emails,
            snippet(files_fts, 3, '[', ']', ' ... ', 18) AS snippet,
            bm25(files_fts) AS rank
        FROM files_fts
        JOIN files ON files.id = files_fts.rowid
        WHERE files_fts MATCH ?
        ORDER BY rank
        LIMIT ?
        """,
        (query, limit),
    ).fetchall()


def search_chunks(conn: sqlite3.Connection, query: str, limit: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT
            files.filename,
            files.relative_path,
            files.path,
            files.tags,
            chunks.chunk_index,
            snippet(chunks_fts, 0, '[', ']', ' ... ', 35) AS snippet,
            bm25(chunks_fts) AS rank
        FROM chunks_fts
        JOIN chunks ON chunks.id = chunks_fts.rowid
        JOIN files ON files.id = chunks.file_id
        WHERE chunks_fts MATCH ?
        ORDER BY rank
        LIMIT ?
        """,
        (query, limit),
    ).fetchall()


def main() -> int:
    parser = argparse.ArgumentParser(description="Search the local resume SQLite database.")
    parser.add_argument("query", help="SQLite FTS query, for example: python OR \"project manager\"")
    parser.add_argument("--db", default=r"D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Resume Search DB\resumes.sqlite")
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--chunks", action="store_true", help="Search LLM-sized text chunks instead of whole files.")
    args = parser.parse_args()

    db_path = Path(args.db)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = search_chunks(conn, args.query, args.limit) if args.chunks else search_files(conn, args.query, args.limit)
    for i, row in enumerate(rows, 1):
        print(f"{i}. {row['filename']}")
        print(f"   {row['path']}")
        if row["tags"]:
            print(f"   tags: {row['tags']}")
        if "emails" in row.keys() and row["emails"]:
            print(f"   emails: {row['emails']}")
        if "chunk_index" in row.keys():
            print(f"   chunk: {row['chunk_index']}")
        print(f"   {row['snippet']}")
        print()
    print(f"results: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

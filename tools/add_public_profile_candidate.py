import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a profile-first candidate from a reviewed public profile.")
    parser.add_argument("--candidate-name", required=True)
    parser.add_argument("--platform", required=True, help="LinkedIn public, GitHub, Stack Overflow, Google Scholar, etc.")
    parser.add_argument("--url", required=True)
    parser.add_argument("--title", default="")
    parser.add_argument("--summary", required=True)
    parser.add_argument("--evidence", action="append", default=[], help="Repeat for each corroborating evidence point.")
    parser.add_argument("--confidence", default="medium", choices=["high", "medium", "low"])
    parser.add_argument("--source-query", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--db", default=r"D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Resume Search DB\resumes.sqlite")
    parser.add_argument("--dest-root", default=r"D:\Work\Recruiting\Resumes")
    args = parser.parse_args()

    entry = {
        "candidate_name": args.candidate_name,
        "candidate_id": None,
        "platform": args.platform,
        "url": args.url,
        "title": args.title or f"{args.candidate_name} - {args.platform}",
        "summary": args.summary,
        "evidence": args.evidence,
        "confidence": args.confidence,
        "review_status": "profile_first",
        "source_query": args.source_query,
        "notes": args.notes,
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump([entry], f, ensure_ascii=False, indent=2)
        temp_path = f.name

    script = Path(__file__).with_name("import_public_profile_notes.py")
    cmd = [
        sys.executable,
        str(script),
        "--input",
        temp_path,
        "--db",
        args.db,
        "--dest-root",
        args.dest_root,
    ]
    try:
        return subprocess.call(cmd)
    finally:
        Path(temp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())

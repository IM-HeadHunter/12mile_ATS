# Local Recruiting Search Tools

This repository contains local utilities built during the D: cleanup and recruiting search project.

The tools index resume and recruiting material from:

```text
D:\Work\Recruiting\Resumes
```

The main generated database and reports live outside this repository under:

```text
D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Resume Search DB
```

## Main Tools

- `tools/build_resume_search_db.py` builds the SQLite full-text search database from resume files and related recruiting documents.
- `tools/build_candidate_rollups.py` groups related files into candidate-level records and filters out non-candidate material such as job descriptions and employment verification documents.
- `tools/resume_db_gui.py` runs the local browser interface for candidate search, job description matching, Krisp note search, public profile notes, and LM Studio analysis.
- `tools/attach_krisp_candidate_notes.py` imports reviewed Krisp meeting notes beside matching candidate files.
- `tools/import_public_profile_notes.py` imports reviewed public profile notes beside matching candidate files.
- `tools/add_public_profile_candidate.py` creates a candidate record from an approved public profile when no formal resume exists.
- `tools/generate_public_profile_searches.py` creates a review queue for public LinkedIn, GitHub, Stack Overflow, Google Scholar, and portfolio searches.

## Local Generated Files

Generated databases, search reports, archives, logs, and cleanup quarantine folders should stay outside Git. The `.gitignore` keeps local generated artifacts and synced project reference material out of the repository.

## Current Direction

The candidate search is intended to become the replacement path for TrackerRMS/LinkedIn Recruiter where practical:

- local resume database first
- candidate-level deduplication
- Krisp notes attached to candidate records
- public profile summaries attached to candidate records
- job description upload/paste matching against local candidates and public source searches
- local LLM analysis through LM Studio

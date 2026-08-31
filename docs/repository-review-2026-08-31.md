# Repository Review - 2026-08-31

Reviewed local shallow copies of these repositories for reuse in `IM-HeadHunter/12mile_ATS`:

- `IM-HeadHunter/12-mile.ca`
- `IM-HeadHunter/Invoice-Parser-`
- `IM-HeadHunter/vue-hawksearch`

## Recommendation

Do not merge any repository wholesale.

The best long-term path is to keep `12mile_ATS` as the local recruiting intelligence system and selectively pull patterns into it:

1. Adopt the `Invoice-Parser-` processing architecture.
2. Borrow search UX concepts from `vue-hawksearch`.
3. Reuse only branding/content direction from `12-mile.ca`.

## High-Value Merge Candidates

### 1. Invoice-Parser- architecture

This is the strongest fit.

Useful patterns:

- deterministic extraction before LLM analysis
- file SHA-256 hashing to prevent exact duplicate processing
- append-only source-of-truth ledgers
- JSONL audit logging for every run/file decision
- explicit data models for parsed rows
- regenerated outputs instead of hand-maintained workbooks
- focused tests for pinned business rules
- config-driven input/output paths

Recommended ATS adaptation:

- create a shared `ats_core` package under `src/`
- move resume extraction, candidate rollups, imports, and search helpers out of one-off scripts
- add `audit_jsonl` for import/search decisions
- add a processed-file ledger for resume, Krisp, MailStore attachment, and public-profile imports
- keep SQLite as the query database, but treat durable source folders plus audit logs as the source of truth
- add small tests for candidate dedupe, non-candidate filtering, public-profile candidate creation, and job-description matching

Do not copy invoice-specific parsing rules except where invoice/candidate revenue tracking becomes part of the ATS later.

### 2. vue-hawksearch search UX patterns

Do not merge the package directly. It is a Vue 2 Hawksearch SDK and does not match the current lightweight Python/local-browser app.

Useful patterns to borrow:

- URL-backed search state
- facets/filters as first-class state
- selected-filter chips
- sort controls
- pagination and load-more controls
- autocomplete/suggestion model
- separate loading/error/empty states
- mobile facet rail behavior

Recommended ATS adaptation:

- add facets for source type, candidate status, location, title/seniority, company, skill tags, note type, and public-profile presence
- make candidate search URLs shareable/bookmarkable
- show selected filters above results
- add explicit sort options: relevance, candidate name, most recent file, number of supporting files, public-profile coverage
- add pagination before the candidate database grows much further

### 3. 12-mile.ca branding and positioning

This is not an architecture source, but it is useful product direction.

Useful pieces:

- 12mile brand positioning around direct conversations, trust, context, and long-term relationships
- industrial technology / advanced manufacturing focus language
- public contact and LinkedIn links
- approved visual assets, if we later build a client/candidate-facing portal

Recommended ATS adaptation:

- keep the internal ATS UI quiet and work-focused
- optionally add 12mile branding only to exported reports, candidate briefing documents, or a future external portal
- do not bring the marketing-page card layout into the internal search tool

## Proposed Refactor Plan

### Phase 1 - Stabilize the current local app

- add `src/ats_core/`
- move shared extraction helpers into `ats_core/extract.py`
- move candidate grouping/filtering into `ats_core/candidates.py`
- move audit and ledger helpers into `ats_core/audit.py` and `ats_core/ledger.py`
- keep `tools/` as thin command-line wrappers
- add `requirements.txt`
- add tests for the current resume/candidate rules

### Phase 2 - Improve search UX

- add URL-backed query/filter state
- add facets and selected-filter chips
- add pagination
- add better candidate detail view sections:
  - resumes
  - Krisp notes
  - public profiles
  - MailStore attachments
  - LLM analysis

### Phase 3 - Broaden import pipelines

- add MailStore attachment extraction as a tracked import source
- add public-profile review/import ledger
- add TrackerRMS and LinkedIn export importers if exports are available
- add revenue/placement import later by adapting the invoice parser architecture

## Licensing / Ownership Notes

- `vue-hawksearch` includes `LICENSE` and `NOTICE` files and should be treated as third-party Apache-licensed code.
- `12-mile.ca` and `Invoice-Parser-` did not show license files in the shallow review copy. Treat them as internal/private source material unless confirmed otherwise.
- Prefer reimplementing small patterns over copying third-party code into the ATS.

## Immediate Next Step

Start with Phase 1. The current ATS works, but the architecture should move from one large GUI script plus build scripts into a small, testable Python package before adding more import sources.

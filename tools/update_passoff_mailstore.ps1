$path = 'D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Server-Cleanup-Passoff-20260827.md'

$content = @'
# Server Cleanup Passoff

Last updated: 2026-08-28, America/Toronto

## Current status

The main `D:\Work` cleanup is functionally complete. The live work tree now uses the cleaned top-level structure:

| Folder | Files | Size |
| --- | ---: | ---: |
| `D:\Work\Admin` | 796 | 0.30 GB |
| `D:\Work\Archive` | 581 | 0.48 GB |
| `D:\Work\Contractors` | 870 | 0.55 GB |
| `D:\Work\Finance` | 19 | 0.01 GB |
| `D:\Work\Marketing & Media` | 800 | 0.38 GB |
| `D:\Work\Recruiting` | 3,336 | 1.31 GB |
| `D:\Work\Reference` | 23 | 0.06 GB |

Current broader cleanup state:

| Location | Files | Size |
| --- | ---: | ---: |
| `D:\Work` | 6,699 | 3.90 GB |
| `D:\Documents` | 36,428 | 18.91 GB |
| `D:\_Duplicate Quarantine` | 12,939 | 20.27 GB |
| `D:\_Download Cleanup Quarantine` | 2,607 | 3.78 GB |

## Completed work

- Cleaned the old nested `D:\Work` structures into the final top-level folders.
- Removed verified duplicates from the live work tree into quarantine rather than deleting them.
- Retired OneDrive and OneNote legacy structures from the live work hierarchy.
- Moved personal documents and media out of `D:\Work` and into appropriate `D:\Documents` locations.
- Flattened and normalized contractor expense material.
- Cleaned `C:\Users\m_DAW\Downloads`; it now contains only the hidden Windows `desktop.ini` file.
- Preserved/imported Downloads material into `D:\Work`, `D:\Documents`, `D:\Music`, and quarantine as appropriate.
- Wrote a Downloads cleanup inventory at `D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Downloads-Cleanup-Final-Inventory-20260827.csv`.
- Verified `Resumes.zip` against `D:\Work\Recruiting\Resumes`; all non-metadata files were already covered by exact hashes.
- Quarantined exact duplicate resume copies from the live resume tree.
- Performed a systemwide likely-resume sweep across `C:\` and `D:\`.
- Imported missing unique likely resumes and likely-resume archive contents into `D:\Work\Recruiting\Resumes\Systemwide Import - 2026-08-27`.
- Exported the completed MailStore archive to EML at `D:\Documents\Mailstore Exports\All Mail EML Export 2026-08-28`.
- Extracted 22,197 MailStore attachment rows to `D:\Documents\Mailstore Exports\Attachment Staging 2026-08-28`.
- Imported 1,986 unique MailStore attachments into the appropriate `D:\Work` and `D:\Documents` folders.
- Imported 321 unique likely-resume attachments into `D:\Work\Recruiting\Resumes\MailStore Attachment Import - 2026-08-28`.
- Verified `D:\Work\Recruiting\Resumes` after the MailStore import: 2,892 files / 702.85 MB and 0 exact duplicate SHA-256 hash groups.
- Verified each MailStore attachment import destination has 0 exact duplicate SHA-256 hash groups.

## Important reports

- `D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Downloads-Cleanup-Final-Inventory-20260827.csv`
- `D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Downloads-Cleanup-Resume-Moves-20260827.csv`
- `D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Resumes Zip Import\Resumes-Zip-Coverage-After-Dedupe-20260827.csv`
- `D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Resumes Zip Import\Live-Resume-Root-Duplicate-Quarantine-Actions-20260827.csv`
- `D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Systemwide Resume Sweep\Systemwide-Document-Candidate-Coverage-Final-20260827.csv`
- `D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Systemwide Resume Sweep\Systemwide-Resume-Import-Detail-20260827.csv`
- `D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Systemwide Resume Sweep\Systemwide-Resume-Archive-Import-Detail-20260827.csv`
- `D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Systemwide Resume Sweep\Systemwide-Live-Resume-Exact-Duplicates-Final-20260827.csv`
- `D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\D-Downloads-Cleanup-Moves-20260827.csv`
- `D:\Documents\Mailstore Exports\Attachment Staging 2026-08-28\MailStore-Attachment-Extraction-20260828.csv`
- `D:\Documents\Mailstore Exports\Attachment Staging 2026-08-28\Import Reports\MailStore-Attachment-Import-Detail-20260828.csv`
- `D:\Documents\Mailstore Exports\Attachment Staging 2026-08-28\Import Reports\MailStore-Attachment-Import-Summary-20260828.csv`
- `D:\Documents\Mailstore Exports\Attachment Staging 2026-08-28\Import Reports\MailStore-Attachment-Existing-Hash-Scan-Errors-20260828.csv`

## MailStore attachment import details

MailStore data remains at `D:\Documents\Mailstore`. The EML export and attachment staging folders are preserved for audit/recovery and should not be deleted yet.

Import results:

| Result | Files | Size |
| --- | ---: | ---: |
| Already covered somewhere on `D:\` | 20,211 | 927.03 MB |
| Imported unique attachments | 1,986 | 565.64 MB |
| Not accounted for | 0 | 0.00 MB |

Imported unique destination summary:

| Destination | Files | Size |
| --- | ---: | ---: |
| `D:\Work\Admin\MailStore Attachment Import - 2026-08-28` | 104 | 53.48 MB |
| `D:\Work\Contractors\MailStore Attachment Import - 2026-08-28` | 308 | 89.25 MB |
| `D:\Work\Finance\MailStore Attachment Import - 2026-08-28` | 9 | 6.18 MB |
| `D:\Work\Marketing & Media\MailStore Attachment Import - 2026-08-28` | 612 | 252.19 MB |
| `D:\Work\Recruiting\MailStore Attachment Import - 2026-08-28` | 252 | 76.80 MB |
| `D:\Work\Recruiting\Resumes\MailStore Attachment Import - 2026-08-28` | 321 | 77.77 MB |
| `D:\Documents\Security Recovery\MailStore Attachment Import - 2026-08-28` | 2 | 0.01 MB |
| `D:\_Download Cleanup Quarantine\2026-08-28\MailStore Inline Images and Noise` | 378 | 9.97 MB |

The existing-file hash scan skipped 7 locked MusicAssistant database/log files. Those files are unrelated to the MailStore export and import destinations.

## Open items

1. Review uncertain Downloads leftovers.
   - Review `D:\Documents\Personal Archive\Downloads Review - 2026-08`.
   - These were preserved because they were not safe to discard automatically.

2. Review MailStore imported attachment folders.
   - Spot-check the imported folders for classification quality.
   - High-priority review folders:
     - `D:\Work\Recruiting\Resumes\MailStore Attachment Import - 2026-08-28`
     - `D:\Work\Recruiting\MailStore Attachment Import - 2026-08-28`
     - `D:\Work\Marketing & Media\MailStore Attachment Import - 2026-08-28`
   - Keep `D:\Documents\Mailstore Exports` until the imported folders have been reviewed and backed up.

3. Quarantine retention and final deletion decision.
   - Keep `D:\_Duplicate Quarantine` and `D:\_Download Cleanup Quarantine` for a few weeks.
   - Before deletion, run one final hash coverage check against the live keeper locations.
   - Delete quarantine only after explicit approval.

4. Backup confirmation.
   - Completed Kopia cloud snapshots on 2026-08-27 for selected personal/important document folders only:
     - `D:\Documents\Security Recovery`
     - `D:\Documents\Personal`
     - `D:\Documents\Personal Archive`
     - `D:\Documents\Lake`
     - `D:\Documents\Paperless`
     - `D:\Documents\Calendar Imports`
     - `D:\Documents\Pixel Backups`
     - `D:\Documents\App Archives`
   - Verified in Kopia repository snapshot list after creation.
   - Corrected exclusion: deleted the Kopia snapshot for `D:\Work\Archive\Cleanup Records`; cloud backup should not include Work, Navidrome, or cleanup records.
   - Verified no current Kopia snapshots match `D:\Work`, `D:\Documents\Navidrome`, or `Cleanup Records`.
   - Still planned for external-drive backup later:
     - `D:\Work`
     - `D:\Work\Recruiting\Resumes`
     - `D:\Documents\Navidrome` if desired
     - `D:\Documents\Mailstore`
     - `D:\Documents\Mailstore Exports`
     - `D:\_Duplicate Quarantine`
     - `D:\_Download Cleanup Quarantine`
   - Kopia still has no recurring schedule configured; current coverage is from manual snapshots.

5. Optional polish pass.
   - Review imported folders such as `Systemwide Import - 2026-08-27` and `MailStore Attachment Import - 2026-08-28`, then fold high-value batches into named client/project subfolders if desired.
   - This is organizational polish, not data-loss prevention.

## Rules for the next pass

- Do not permanently delete anything without explicit approval.
- Prefer quarantine over deletion.
- Preserve source-path evidence in import folders and reports.
- Use SHA-256 checks before treating files as duplicates.
- Keep personal material under `D:\Documents`, not `D:\Work`.
- Keep work/client/recruiting material under the cleaned `D:\Work` structure.
'@

Set-Content -LiteralPath $path -Value $content -Encoding UTF8
Write-Host "UPDATED $path"

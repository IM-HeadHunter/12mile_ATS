$path = 'D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Server-Cleanup-Passoff-20260827.md'
$content = Get-Content -LiteralPath $path -Raw

$completed = @'
- Built a local searchable SQLite resume database at `D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Resume Search DB\resumes.sqlite`.
- Indexed 2,892 files from `D:\Work\Recruiting\Resumes`; extracted readable text from 2,564 files and created 26,775 LLM-ready text chunks.
- Added a local resume search GUI served from this task at `http://127.0.0.1:8765`.
'@

if ($content -notmatch 'local searchable SQLite resume database') {
  $content = $content -replace '(- Verified each MailStore attachment import destination has 0 exact duplicate SHA-256 hash groups\.)', ('$1' + "`r`n" + $completed)
}

$reports = @'
- `D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Resume Search DB\resumes.sqlite`
- `D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Resume Search DB\resume-search-index-report-20260831.csv`
'@

if ($content -notmatch 'resume-search-index-report-20260831.csv') {
  $content = $content -replace '(- `D:\\Documents\\Mailstore Exports\\Attachment Staging 2026-08-28\\Import Reports\\MailStore-Attachment-Existing-Hash-Scan-Errors-20260828.csv`)', ('$1' + "`r`n" + $reports)
}

$newItem = @'

8. Improve the resume database and connect local LLM analysis.
   - Current database is usable for keyword search and local snippet retrieval.
   - Next improvements:
     - quarantine obvious non-resume noise that the database surfaced, such as Python documentation imported during the systemwide sweep
     - add better PDF/OCR handling for scanned resumes and malformed PDFs
     - add structured fields for candidate name, current title, company, location, skills, seniority, and source folder
     - connect a self-hosted LLM endpoint such as Ollama or LM Studio for candidate summaries and role-fit ranking
     - keep SQLite as the source of truth and store embeddings/summaries beside file hashes, not as replacement data
'@

if ($content -notmatch 'Improve the resume database and connect local LLM analysis') {
  $content = $content -replace '(?ms)(7\. Review quarantines and shift remaining keepers from `C:\\` to `D:\\`\..*?Preserve source-path evidence in reports for anything moved from `C:\\`\.)', ('$1' + $newItem)
}

Set-Content -LiteralPath $path -Value $content -Encoding UTF8
Write-Host "UPDATED $path"

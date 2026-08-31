$path = 'D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Server-Cleanup-Passoff-20260827.md'
$content = Get-Content -LiteralPath $path -Raw

$newItem = @'

7. Review quarantines and shift remaining keepers from `C:\` to `D:\`.
   - Review `D:\_Duplicate Quarantine` and `D:\_Download Cleanup Quarantine` before any deletion.
   - Do not permanently delete quarantine contents until:
     - live keeper locations have been rechecked by SHA-256 coverage
     - anything personally or operationally important has been restored or moved into the right `D:\` folder
     - explicit deletion approval has been given
   - Scan `C:\Users\m_DAW` and other non-system `C:\` locations for remaining personal/work data that should live on `D:\`.
   - Move keepers into the cleaned structure:
     - work/client/recruiting/admin material under `D:\Work`
     - personal documents under `D:\Documents`
     - photos under `D:\Photos` or `D:\Documents\Personal Archive`, depending on context
     - music/media under `D:\Music`, `D:\Movies`, or `D:\TV`
   - Leave installed applications, active app data, Windows system files, and browser/profile data on `C:\` unless there is a specific migration plan.
   - Preserve source-path evidence in reports for anything moved from `C:\`.
'@

if ($content -notmatch 'Review quarantines and shift remaining keepers from `C:\\` to `D:\\`') {
  $content = $content -replace '(?ms)(6\. Clean loose `D:\\` root files and review top-level folders\..*?with a dated subfolder\.)', ('$1' + $newItem)
}

Set-Content -LiteralPath $path -Value $content -Encoding UTF8
Write-Host "UPDATED $path"

$path = 'D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Server-Cleanup-Passoff-20260827.md'
$content = Get-Content -LiteralPath $path -Raw

$content = $content -replace 'Last updated: 2026-08-28, America/Toronto', 'Last updated: 2026-08-28, America/Toronto'

$newItem = @'

6. Clean loose `D:\` root files and review top-level folders.
   - Next active cleanup pass should start at the root of `D:\`.
   - Current loose root files are small metadata/autorun-style files:
     - `D:\._`
     - `D:\.VolumeIcon.icns`
     - `D:\.VolumeIcon.ico`
     - `D:\Autorun.inf`
   - Review whether `D:\Downloads` can remain empty or be removed.
   - Review top-level non-system folders for obvious stale/temp material, especially:
     - `D:\New`
     - `D:\Temp`
     - `D:\Programs`
     - `D:\Seagate`
     - `D:\RadioDJv3`
   - Do not permanently delete root files or folders during the first pass; move anything questionable to `D:\_Download Cleanup Quarantine` with a dated subfolder.
'@

if ($content -notmatch 'Clean loose `D:\\` root files') {
  $content = $content -replace '(?ms)(5\. Optional polish pass\..*?This is organizational polish, not data-loss prevention\.)', ('$1' + $newItem)
}

Set-Content -LiteralPath $path -Value $content -Encoding UTF8
Write-Host "UPDATED $path"

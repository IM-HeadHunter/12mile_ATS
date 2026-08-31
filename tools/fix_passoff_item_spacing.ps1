$path = 'D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Server-Cleanup-Passoff-20260827.md'
$content = Get-Content -LiteralPath $path -Raw
$content = $content -replace "dated subfolder\.\r?\n7\. Review", "dated subfolder.`r`n`r`n7. Review"
Set-Content -LiteralPath $path -Value $content -Encoding UTF8
Write-Host "FIXED $path"

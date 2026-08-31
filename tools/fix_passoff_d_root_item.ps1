$path = 'D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Server-Cleanup-Passoff-20260827.md'
$content = Get-Content -LiteralPath $path -Raw

$content = $content -replace "prevention\.\r?\n6\. Clean", "prevention.`r`n`r`n6. Clean"
$content = $content -replace "\s+- `D:\\\._.*?\r?\n", "     - one oddly named AppleDouble-style `D:\._...` file`r`n"

Set-Content -LiteralPath $path -Value $content -Encoding UTF8
Write-Host "FIXED $path"

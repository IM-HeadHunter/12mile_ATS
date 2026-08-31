$path = 'D:\Work\Archive\Cleanup Records\2026-08 D Work Cleanup\Server-Cleanup-Passoff-20260827.md'
$lines = Get-Content -LiteralPath $path
$fixed = foreach ($line in $lines) {
  if ($line -like '*D:\._*') {
    '     - one oddly named AppleDouble-style `D:\._...` file'
  } else {
    $line
  }
}
Set-Content -LiteralPath $path -Value $fixed -Encoding UTF8
Write-Host "FIXED $path"

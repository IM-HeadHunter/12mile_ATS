$paths = @(
  'D:\Work',
  'D:\Documents',
  'D:\_Duplicate Quarantine',
  'D:\_Download Cleanup Quarantine'
)

$rows = foreach ($path in $paths) {
  if (Test-Path -LiteralPath $path) {
    $files = @(Get-ChildItem -LiteralPath $path -File -Recurse -Force -ErrorAction SilentlyContinue)
    [PSCustomObject]@{
      Path = $path
      Files = $files.Count
      GB = [math]::Round((($files | Measure-Object Length -Sum).Sum / 1GB), 2)
    }
  }
}

$rows | Format-Table -AutoSize

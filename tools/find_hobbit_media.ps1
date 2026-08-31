$roots = @('C:\', 'D:\')
$terms = 'hobbit|tolkien|middle.?earth|lord.?of.?the.?rings|lotr'
$imageAndInstallerExtensions = @(
  '.iso', '.bin', '.cue', '.mdf', '.mds', '.ccd', '.img', '.sub', '.nrg',
  '.daa', '.uif', '.zip', '.7z', '.rar', '.exe', '.msi', '.cab'
)

$matches = foreach ($root in $roots) {
  Get-ChildItem -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match $terms } |
    ForEach-Object {
      $extension = if ($_.PSIsContainer) { '' } else { $_.Extension.ToLowerInvariant() }
      [PSCustomObject]@{
        Kind = if ($_.PSIsContainer) { 'Folder' } else { 'File' }
        LooksLikeMediaOrInstaller = (-not $_.PSIsContainer -and $imageAndInstallerExtensions -contains $extension)
        Extension = $extension
        MB = if ($_.PSIsContainer) { '' } else { [math]::Round($_.Length / 1MB, 2) }
        Modified = $_.LastWriteTime
        Path = $_.FullName
      }
    }
}

$matches |
  Sort-Object Path -Unique |
  Format-Table -AutoSize

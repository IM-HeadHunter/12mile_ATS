$roots = @(
  'D:\Work\Admin\MailStore Attachment Import - 2026-08-28',
  'D:\Work\Contractors\MailStore Attachment Import - 2026-08-28',
  'D:\Work\Finance\MailStore Attachment Import - 2026-08-28',
  'D:\Work\Marketing & Media\MailStore Attachment Import - 2026-08-28',
  'D:\Work\Recruiting\MailStore Attachment Import - 2026-08-28',
  'D:\Work\Recruiting\Resumes\MailStore Attachment Import - 2026-08-28',
  'D:\Documents\Security Recovery\MailStore Attachment Import - 2026-08-28',
  'D:\_Download Cleanup Quarantine\2026-08-28\MailStore Inline Images and Noise'
)

$rows = foreach ($root in $roots) {
  if (Test-Path -LiteralPath $root) {
    $files = @(Get-ChildItem -LiteralPath $root -File -Recurse -Force -ErrorAction SilentlyContinue)
    $hashRows = foreach ($file in $files) {
      $hash = Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256
      [PSCustomObject]@{
        Hash = $hash.Hash
        Path = $file.FullName
        Bytes = $file.Length
      }
    }
    $duplicateGroups = @($hashRows | Group-Object Hash | Where-Object { $_.Count -gt 1 })
    [PSCustomObject]@{
      Path = $root
      Files = $files.Count
      MB = [math]::Round((($files | Measure-Object Length -Sum).Sum / 1MB), 2)
      DuplicateGroups = $duplicateGroups.Count
    }
  }
}

$rows | Format-Table -AutoSize

$installerUrl = 'https://installers.lmstudio.ai/win32/x64/0.4.23-1/LM-Studio-0.4.23-1-x64.exe'
$installerDir = 'D:\Programs\Installers\LM Studio'
$installerPath = Join-Path $installerDir 'LM-Studio-0.4.23-1-x64.exe'

New-Item -ItemType Directory -Path $installerDir -Force | Out-Null

if (-not (Test-Path -LiteralPath $installerPath)) {
  Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath
}

$hash = Get-FileHash -LiteralPath $installerPath -Algorithm SHA256
Write-Host "INSTALLER $installerPath"
Write-Host "SHA256 $($hash.Hash)"

Start-Process -FilePath $installerPath

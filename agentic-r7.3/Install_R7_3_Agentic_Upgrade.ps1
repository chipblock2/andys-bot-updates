$ErrorActionPreference = 'Stop'
$Source = Split-Path -Parent $MyInvocation.MyCommand.Path
$Target = Join-Path $env:LOCALAPPDATA 'AndysBot\R7_3_Agentic_Companion'
$Desktop = [Environment]::GetFolderPath('Desktop')
$ShortcutPath = Join-Path $Desktop "Andy's Bot R7.3 Agentic.lnk"

Write-Host "ANDY'S BOT R7.3 - AGENTIC COMPANION INSTALL" -ForegroundColor Cyan
Write-Host "This installs beside R7.2.1. It does not overwrite the trading engine." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $Target | Out-Null

if (Test-Path (Join-Path $Target 'config.json')) {
  Copy-Item (Join-Path $Target 'config.json') (Join-Path $Target ('config.backup.' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.json')) -Force
}
Copy-Item (Join-Path $Source 'andys_agentic_companion.py') $Target -Force
Copy-Item (Join-Path $Source 'Start_Agentic_Upgrade.ps1') $Target -Force
Copy-Item (Join-Path $Source 'config.json') $Target -Force
Copy-Item (Join-Path $Source 'README.txt') $Target -Force

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = 'powershell.exe'
$Shortcut.Arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $Target 'Start_Agentic_Upgrade.ps1') + '"'
$Shortcut.WorkingDirectory = $Target
$Shortcut.Description = "Andy's Bot R7.3 Agentic Companion (Shadow Only)"
$Shortcut.Save()

Write-Host "Installed to: $Target" -ForegroundColor Green
Write-Host "Desktop shortcut created: Andy's Bot R7.3 Agentic" -ForegroundColor Green
Write-Host "Guardrails: 8 positions max, GBP10/order, GBP20 exposure; no live order/transfer/risk-change endpoints." -ForegroundColor Green
Write-Host "Starting companion..." -ForegroundColor Cyan
Start-Process powershell.exe -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',('"' + (Join-Path $Target 'Start_Agentic_Upgrade.ps1') + '"')

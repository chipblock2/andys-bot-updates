$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Here

$python = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
  $python = @('py','-3')
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
  $python = @('python')
} else {
  Add-Type -AssemblyName PresentationFramework
  [System.Windows.MessageBox]::Show("Python was not found. Start the normal Andy's Bot first, then reinstall R7.3 so the installer can use its Python runtime.", "Andy's Bot R7.3") | Out-Null
  exit 1
}

Write-Host "ANDY'S BOT R7.3 AGENTIC COMPANION" -ForegroundColor Cyan
Write-Host "SHADOW ONLY - no live orders, transfers or risk changes" -ForegroundColor Green
if ($python.Count -eq 2) {
  & $python[0] $python[1] "$Here\andys_agentic_companion.py"
} else {
  & $python[0] "$Here\andys_agentic_companion.py"
}

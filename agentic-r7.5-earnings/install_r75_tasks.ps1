$ErrorActionPreference='Stop'
$Here='C:\AndysBot\Andys_Bot_Desktop_Current\r7_5_earnings_shadow'
$Start=Join-Path $Here 'start_r75_shadow.ps1'
$Refresh=Join-Path $Here 'refresh_fee_validations.ps1'

schtasks.exe /Create /F /SC MINUTE /MO 5 /TN 'AndysBot R7.5 Shadow Watchdog' /TR ('powershell.exe -NoProfile -ExecutionPolicy Bypass -File "'+$Start+'"') | Out-Host
schtasks.exe /Create /F /SC DAILY /ST 03:15 /TN 'AndysBot R7.5 Fee Validation Refresh' /TR ('powershell.exe -NoProfile -ExecutionPolicy Bypass -File "'+$Refresh+'"') | Out-Host
Write-Host 'R7.5 watchdog and daily validation tasks installed.' -ForegroundColor Green

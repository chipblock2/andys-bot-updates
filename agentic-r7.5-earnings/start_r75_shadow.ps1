$ErrorActionPreference='Stop'
$Here=Split-Path -Parent $MyInvocation.MyCommand.Path
$Py='C:\Users\Andy\AppData\Local\Programs\Python\Python312\pythonw.exe'
$Target=Join-Path $Here 'live_shadow_bridge.py'
$running=Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^pythonw?\.exe$' -and $_.CommandLine -like '*live_shadow_bridge.py*' }
if (-not $running) { Start-Process -FilePath $Py -ArgumentList ('"' + $Target + '"') -WorkingDirectory $Here -WindowStyle Hidden }

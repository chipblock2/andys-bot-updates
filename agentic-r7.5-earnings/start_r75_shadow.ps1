$ErrorActionPreference='Stop'
$Here='C:\AndysBot\Andys_Bot_Desktop_Current\r7_5_earnings_shadow'
$Py='C:\Users\Andy\AppData\Local\Programs\Python\Python312\pythonw.exe'

$jobs=@(
  @{Name='R7.5 bridge'; File='live_shadow_bridge.py'},
  @{Name='R7.5 counterfactual'; File='execution_counterfactual.py'},
  @{Name='R7.5 exit advisor'; File='exit_advisor.py'},
  @{Name='R7.5 exit counterfactual'; File='exit_counterfactual.py'}
)
foreach($job in $jobs){
  $target=Join-Path $Here $job.File
  if(-not (Test-Path $target)){ continue }
  $running=Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^pythonw?\.exe$' -and $_.CommandLine -like ('*'+$job.File+'*')
  }
  if(-not $running){
    Start-Process -FilePath $Py -ArgumentList ('"'+$target+'"') -WorkingDirectory $Here -WindowStyle Hidden
  }
}
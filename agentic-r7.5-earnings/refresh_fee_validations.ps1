$ErrorActionPreference='Stop'
$Here='C:\AndysBot\Andys_Bot_Desktop_Current\r7_5_earnings_shadow'
$Py='C:\Users\Andy\AppData\Local\Programs\Python\Python312\python.exe'
$FeeFile='C:\AndysBot\Andys_Bot_Desktop_Current\coinbase_fee_override.json'
Set-Location $Here
$Products='BTC-GBP,ETH-GBP,DOT-GBP,SOL-GBP,ADA-GBP,UNI-GBP,DOGE-GBP,CRV-GBP,ALGO-GBP,LTC-GBP,ATOM-GBP,LINK-GBP,AAVE-GBP'

$maker=0.0006
$taker=0.0016
if(Test-Path $FeeFile){
  try{
    $f=Get-Content $FeeFile -Raw | ConvertFrom-Json
    if($f.maker_fee_rate -ne $null){$maker=[double]$f.maker_fee_rate}
    if($f.taker_fee_rate -ne $null){$taker=[double]$f.taker_fee_rate}
  }catch{}
}

& $Py .\lab.py scan --products $Products --fee $maker *> .\scan_live_fee.log
if($LASTEXITCODE -ne 0){ throw "Maker validation failed" }
Copy-Item .\results.csv .\results_maker.csv -Force
Copy-Item .\state\strategy_lab_status.json .\state\strategy_lab_maker_status.json -Force

& $Py .\lab.py scan --products $Products --fee $taker *> .\scan_taker_fee.log
if($LASTEXITCODE -ne 0){ throw "Taker validation failed" }
Copy-Item .\results.csv .\results_taker.csv -Force
Copy-Item .\state\strategy_lab_status.json .\state\strategy_lab_taker_status.json -Force

# R7.5 health intentionally uses maker validation as its primary long-run evidence.
Copy-Item .\state\strategy_lab_maker_status.json .\state\strategy_lab_status.json -Force
Copy-Item .\results_maker.csv .\results.csv -Force
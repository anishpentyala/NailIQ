$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$previewUrl = "http://127.0.0.1:5173"
$port = 5173
$backendPort = 5000
$outLog = Join-Path $projectRoot "phone-preview.out.log"
$errLog = Join-Path $projectRoot "phone-preview.err.log"
$backendOutLog = Join-Path $projectRoot "phone-preview-backend.out.log"
$backendErrLog = Join-Path $projectRoot "phone-preview-backend.err.log"

function Test-PortListening {
  param([int]$TargetPort)

  $listener = Get-NetTCPConnection -LocalPort $TargetPort -State Listen -ErrorAction SilentlyContinue |
    Select-Object -First 1

  return $null -ne $listener
}

function Get-BrowserPath {
  $candidates = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
  )

  return $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}

if (-not (Test-PortListening -TargetPort $backendPort)) {
  $backendExe = Join-Path $projectRoot "backend\venv\Scripts\python.exe"

  Start-Process `
    -FilePath $backendExe `
    -ArgumentList @("app.py") `
    -WorkingDirectory (Join-Path $projectRoot "backend") `
    -WindowStyle Hidden `
    -RedirectStandardOutput $backendOutLog `
    -RedirectStandardError $backendErrLog

  for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 1
    if (Test-PortListening -TargetPort $backendPort) { break }
  }
}

if (-not (Test-PortListening -TargetPort $port)) {
  Start-Process `
    -FilePath "npm.cmd" `
    -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1") `
    -WorkingDirectory (Join-Path $projectRoot "frontend") `
    -WindowStyle Hidden `
    -RedirectStandardOutput $outLog `
    -RedirectStandardError $errLog

  $started = $false

  for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1

    if (Test-PortListening -TargetPort $port) {
      $started = $true
      break
    }
  }

  if (-not $started) {
    throw "Vite dev server did not start on port $port. Check $outLog and $errLog."
  }
}

$browserPath = Get-BrowserPath

if (-not $browserPath) {
  throw "Chrome or Edge was not found."
}

Start-Process `
  -FilePath $browserPath `
  -ArgumentList @(
    "--app=$previewUrl",
    "--window-size=430,932",
    "--window-position=80,80"
  )

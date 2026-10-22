# Starts the backend, the frontend dev server and an HTTPS tunnel as independent background processes and prints the
# phone link. Run from the repo root:  powershell -ExecutionPolicy Bypass -File scripts\phone_test.ps1
# Stop everything:                      powershell -ExecutionPolicy Bypass -File scripts\phone_test.ps1 -Stop
param([switch]$Stop)

$root = Split-Path -Parent $PSScriptRoot
$logs = Join-Path $root "data\phone_test_logs"
New-Item -ItemType Directory -Force $logs | Out-Null
$pidFile = Join-Path $logs "pids.txt"

function Stop-All {
  if (Test-Path $pidFile) {
    Get-Content $pidFile | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
    Remove-Item $pidFile -Force
  }
}

Stop-All
if ($Stop) { Write-Host "Stopped."; return }

$cf = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
if (-not (Test-Path $cf)) { Write-Host "cloudflared not found: winget install Cloudflare.cloudflared"; return }

function Start-Bg($file, $argList, $workDir, $name) {
  $p = Start-Process -FilePath $file -ArgumentList $argList -WorkingDirectory $workDir -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $logs "$name.out.log") -RedirectStandardError (Join-Path $logs "$name.err.log")
  Add-Content $pidFile $p.Id
}

$py = Join-Path $root "backend\venv\Scripts\python.exe"
Start-Bg $py "app.py" (Join-Path $root "backend") "backend"
$npm = (Get-Command npm.cmd).Source
Start-Bg $npm "run dev" (Join-Path $root "frontend") "frontend"

# wait for both servers
$ok = $false
for ($i = 0; $i -lt 60; $i++) {
  Start-Sleep -Seconds 1
  try {
    Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 "http://localhost:5173/" | Out-Null
    Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 "http://localhost:5173/history" | Out-Null
    $ok = $true; break
  } catch {}
}
if (-not $ok) { Write-Host "Servers did not come up; see $logs"; return }

Start-Bg $cf "tunnel --no-autoupdate --url http://[::1]:5173" $root "tunnel"
$url = $null
for ($i = 0; $i -lt 40 -and -not $url; $i++) {
  Start-Sleep -Seconds 1
  $text = (Get-Content (Join-Path $logs "tunnel.err.log"), (Join-Path $logs "tunnel.out.log") -ErrorAction SilentlyContinue) -join "`n"
  if ($text -match "https://[a-z0-9-]+\.trycloudflare\.com") { $url = $Matches[0] }
}
if ($url) { Write-Host "`nOpen this in Safari on the iPhone:`n$url`n" } else { Write-Host "No tunnel URL yet; see $logs\tunnel.err.log" }

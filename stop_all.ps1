# ════════════════════════════════════════════════════════════════════════════
# stop_all.ps1 — Cairo Smart Traffic: Clean Shutdown
# ════════════════════════════════════════════════════════════════════════════

param(
    [switch]$KeepDocker
)

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Cairo Smart Traffic — Stopping Stack" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

# Stop Python processes (producer, consumer)
Write-Host "Stopping Python processes..." -ForegroundColor Cyan
Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*producer*" -or
    $_.CommandLine -like "*consumer*"
} | ForEach-Object {
    Write-Host "  Stopping PID $($_.Id) - $($_.ProcessName)" -ForegroundColor Gray
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}

# Stop Node processes (Express + Vite)
Write-Host "Stopping Node processes (dashboard)..." -ForegroundColor Cyan
Get-Process node -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "  Stopping PID $($_.Id) - $($_.ProcessName)" -ForegroundColor Gray
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}

# Stop Spark Streaming inside Docker
Write-Host "Stopping Spark Streaming inside container..." -ForegroundColor Cyan
docker exec infrastructure-spark-master-1 pkill -f spark_streaming 2>&1 | Out-Null

# Stop Docker stack
if (-not $KeepDocker) {
    Write-Host "Stopping Docker services..." -ForegroundColor Cyan
    Push-Location (Join-Path $PSScriptRoot "infrastructure")
    docker-compose down
    Pop-Location
} else {
    Write-Host "Skipping Docker shutdown (-KeepDocker)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Shutdown complete." -ForegroundColor Green
Write-Host ""

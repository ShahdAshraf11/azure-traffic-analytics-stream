# ============================================================================
# start_all.ps1 - One-click startup for Cairo Traffic project
# Tested for Windows PowerShell 5.1
# ============================================================================

$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

Write-Host ''
Write-Host '===============================================================' -ForegroundColor Cyan
Write-Host '  Cairo Smart Traffic - Starting Everything' -ForegroundColor Cyan
Write-Host '===============================================================' -ForegroundColor Cyan
Write-Host ''


# ----------------------------------------------------------------------------
# Helper: Open a new cmd.exe window that runs a command and stays open.
# We use cmd.exe instead of PowerShell-in-PowerShell because cmd has way
# simpler quoting rules - no escaping nightmares.
# The "/k" flag means "keep the window open after the command finishes".
# ----------------------------------------------------------------------------
function Start-ComponentWindow {
    param(
        [string]$Title,
        [string]$WorkingDir,
        [string]$Command
    )
    Write-Host ('  Starting ' + $Title + '...') -ForegroundColor Yellow

    # Build a small batch command that:
    # 1. Sets the window title
    # 2. Changes directory
    # 3. Activates the venv (if it exists)
    # 4. Runs the command
    # 5. Pauses on exit
    $venvActivate = Join-Path $ProjectRoot 'venv\Scripts\activate.bat'
    if (Test-Path $venvActivate) {
        $batCmd = 'title ' + $Title + ' && cd /d "' + $WorkingDir + '" && call "' + $venvActivate + '" && ' + $Command + ' && pause'
    }
    else {
        $batCmd = 'title ' + $Title + ' && cd /d "' + $WorkingDir + '" && ' + $Command + ' && pause'
    }

    Start-Process -FilePath 'cmd.exe' -ArgumentList '/k', $batCmd
}


# ----------------------------------------------------------------------------
# Helper: Wait for a TCP port to be listening.
# ----------------------------------------------------------------------------
function Wait-Port {
    param(
        [int]$Port,
        [string]$Service,
        [int]$TimeoutSeconds = 60
    )
    Write-Host ('    Waiting for ' + $Service + ' on port ' + $Port + '...') -ForegroundColor Gray
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $tcp = New-Object System.Net.Sockets.TcpClient
            $tcp.Connect('localhost', $Port)
            $tcp.Close()
            Write-Host ('    [OK] ' + $Service + ' responding') -ForegroundColor Green
            return $true
        }
        catch {
            Start-Sleep -Seconds 2
        }
    }
    Write-Host ('    [TIMEOUT] ' + $Service + ' did not respond in ' + $TimeoutSeconds + ' s') -ForegroundColor Red
    return $false
}


# ============================================================================
# STEP 1: Docker stack
# ============================================================================
Write-Host 'STEP 1: Starting Docker stack...' -ForegroundColor Cyan
Push-Location (Join-Path $ProjectRoot 'infrastructure')
docker compose up -d
Pop-Location

Wait-Port -Port 5432 -Service 'PostgreSQL' -TimeoutSeconds 30
Wait-Port -Port 9093 -Service 'Kafka' -TimeoutSeconds 30
Wait-Port -Port 8080 -Service 'Airflow Web UI' -TimeoutSeconds 90
Write-Host ''


# ============================================================================
# STEP 2: Producer
# ============================================================================
Write-Host 'STEP 2: Starting Producer...' -ForegroundColor Cyan
Start-ComponentWindow -Title 'Producer' -WorkingDir (Join-Path $ProjectRoot 'data_generator') -Command 'python producer.py'
Start-Sleep -Seconds 3
Write-Host ''


# ============================================================================
# STEP 3: Consumer
# ============================================================================
Write-Host 'STEP 3: Starting Consumer...' -ForegroundColor Cyan
Start-ComponentWindow -Title 'Consumer' -WorkingDir (Join-Path $ProjectRoot 'stream_processor') -Command 'python consumer.py'
Start-Sleep -Seconds 3
Write-Host ''


# ============================================================================
# STEP 4: Spark Streaming - submit via spark-submit inside spark-master
# ============================================================================
Write-Host 'STEP 4: Starting Spark Streaming...' -ForegroundColor Cyan
$sparkPath = Join-Path $ProjectRoot 'streaming\spark_streaming.py'
if (Test-Path $sparkPath) {
    $sparkCmd = 'docker exec -it spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --conf spark.jars.ivy=/tmp/.ivy2 --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,org.postgresql:postgresql:42.7.1 /opt/spark/work/spark_streaming.py'
    Start-ComponentWindow -Title 'Spark Streaming' -WorkingDir $ProjectRoot -Command $sparkCmd
    Start-Sleep -Seconds 5
}
else {
    Write-Host '  [SKIP] spark_streaming.py not found' -ForegroundColor Yellow
}
Write-Host ''


# ============================================================================
# STEP 5: Dashboard backend
# ============================================================================
Write-Host 'STEP 5: Starting Dashboard backend...' -ForegroundColor Cyan
$backendPath = Join-Path $ProjectRoot 'dashboard\server\package.json'
if (Test-Path $backendPath) {
    Start-ComponentWindow -Title 'Dashboard-Backend' -WorkingDir (Join-Path $ProjectRoot 'dashboard\server') -Command 'npm start'
    Start-Sleep -Seconds 3
    Wait-Port -Port 5000 -Service 'Dashboard API' -TimeoutSeconds 30
}
else {
    Write-Host '  [SKIP] dashboard/server not found' -ForegroundColor Yellow
}
Write-Host ''


# ============================================================================
# STEP 6: Dashboard frontend
# ============================================================================
Write-Host 'STEP 6: Starting Dashboard frontend...' -ForegroundColor Cyan
$frontendPath = Join-Path $ProjectRoot 'dashboard\client\package.json'
if (Test-Path $frontendPath) {
    Start-ComponentWindow -Title 'Dashboard-Frontend' -WorkingDir (Join-Path $ProjectRoot 'dashboard\client') -Command 'npm run dev'
    Start-Sleep -Seconds 5
}
else {
    Write-Host '  [SKIP] dashboard/client not found' -ForegroundColor Yellow
}
Write-Host ''


Write-Host '===============================================================' -ForegroundColor Green
Write-Host '  ALL SYSTEMS STARTED' -ForegroundColor Green
Write-Host '===============================================================' -ForegroundColor Green
Write-Host ''
Write-Host '  URLs to open:' -ForegroundColor Cyan
Write-Host '    Dashboard:  http://localhost:8081'
Write-Host '    Airflow:    http://localhost:8080  (admin / admin)'
Write-Host '    Kafdrop:    http://localhost:9001'
Write-Host '    Spark UI:   http://localhost:8082'
Write-Host ''
Write-Host '  To stop everything:'
Write-Host '    .\stop_all.ps1' -ForegroundColor Yellow
Write-Host ''

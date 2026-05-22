# ════════════════════════════════════════════════════════════════════════════
# diagnose.ps1 — Cairo Smart Traffic: System Health Report
# ════════════════════════════════════════════════════════════════════════════
#
# Run this anytime to check all components.
# ════════════════════════════════════════════════════════════════════════════

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Cairo Smart Traffic — Diagnostic Report" -ForegroundColor Cyan
Write-Host "  $(Get-Date)" -ForegroundColor Gray
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# ────────────────────────────────────────────────────────────────────────────
# Section 1: Docker Containers
# ────────────────────────────────────────────────────────────────────────────
Write-Host "[1] DOCKER CONTAINERS" -ForegroundColor Yellow
$containers = @(
    "infrastructure-postgres-1",
    "infrastructure-kafka-1",
    "infrastructure-zookeeper-1",
    "infrastructure-kafdrop-1",
    "infrastructure-spark-master-1",
    "infrastructure-spark-worker-1",
    "infrastructure-airflow-webserver-1",
    "infrastructure-airflow-scheduler-1",
    "infrastructure-airflow-postgres-1"
)

foreach ($container in $containers) {
    $status = docker inspect -f "{{.State.Status}}" $container 2>$null
    if ($status -eq "running") {
        Write-Host "  [OK]   $container" -ForegroundColor Green
    } else {
        Write-Host "  [DOWN] $container" -ForegroundColor Red
    }
}
Write-Host ""

# ────────────────────────────────────────────────────────────────────────────
# Section 2: Database Activity
# ────────────────────────────────────────────────────────────────────────────
Write-Host "[2] DATABASE ACTIVITY (last 1 hour)" -ForegroundColor Yellow

$queries = @{
    "raw_events"          = "SELECT COUNT(*) FROM raw_events WHERE request_time > NOW() - INTERVAL '1 hour';"
    "predictions"         = "SELECT COUNT(*) FROM predictions WHERE predicted_at > NOW() - INTERVAL '1 hour';"
    "anomalies"           = "SELECT COUNT(*) FROM anomalies WHERE detected_at > NOW() - INTERVAL '1 hour';"
    "forecasts"           = "SELECT COUNT(*) FROM forecasts WHERE forecast_made_at > NOW() - INTERVAL '1 hour';"
    "ai_summaries"        = "SELECT COUNT(*) FROM ai_summaries WHERE generated_at > NOW() - INTERVAL '1 hour';"
    "data_quality_events" = "SELECT COUNT(*) FROM data_quality_events WHERE checked_at > NOW() - INTERVAL '1 hour';"
    "fact_traffic"        = "SELECT COUNT(*) FROM warehouse.fact_traffic WHERE event_time > NOW() - INTERVAL '1 hour';"
}

foreach ($pair in $queries.GetEnumerator()) {
    $count = docker exec infrastructure-postgres-1 psql -U postgres -d traffic_db -t -c $pair.Value 2>&1
    if ($count -match '^\s*\d+\s*$') {
        $num = [int]$count.Trim()
        $color = if ($num -gt 0) { "Green" } else { "Yellow" }
        Write-Host ("  {0,-22} {1,8} rows" -f $pair.Key, $num) -ForegroundColor $color
    } else {
        Write-Host ("  {0,-22} ERROR" -f $pair.Key) -ForegroundColor Red
    }
}
Write-Host ""

# ────────────────────────────────────────────────────────────────────────────
# Section 3: Warehouse Tables
# ────────────────────────────────────────────────────────────────────────────
Write-Host "[3] WAREHOUSE TABLES" -ForegroundColor Yellow

$warehouseQuery = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'warehouse' ORDER BY table_name;"
$warehouseTables = docker exec infrastructure-postgres-1 psql -U postgres -d traffic_db -t -c $warehouseQuery 2>&1
$warehouseTables -split "`n" | ForEach-Object {
    $t = $_.Trim()
    if ($t) { Write-Host "  $t" -ForegroundColor Gray }
}
Write-Host ""

# ────────────────────────────────────────────────────────────────────────────
# Section 4: Forecast Buffer Status
# ────────────────────────────────────────────────────────────────────────────
Write-Host "[4] FORECAST BUFFER STATUS" -ForegroundColor Yellow

$forecastQuery = "SELECT horizon, COUNT(DISTINCT location_name) AS locations FROM forecasts WHERE forecast_made_at > NOW() - INTERVAL '15 minutes' GROUP BY horizon ORDER BY horizon;"
$forecastResult = docker exec infrastructure-postgres-1 psql -U postgres -d traffic_db -c $forecastQuery 2>&1
Write-Host $forecastResult -ForegroundColor Gray
Write-Host ""

# ────────────────────────────────────────────────────────────────────────────
# Section 5: API + Dashboard Availability
# ────────────────────────────────────────────────────────────────────────────
Write-Host "[5] API + DASHBOARD" -ForegroundColor Yellow

$urls = @{
    "Express API"     = "http://localhost:5000/api/health"
    "Vite Dashboard"  = "http://localhost:8081"
    "Airflow UI"      = "http://localhost:8080"
    "Kafdrop"         = "http://localhost:9001"
}

foreach ($pair in $urls.GetEnumerator()) {
    try {
        $response = Invoke-WebRequest -Uri $pair.Value -TimeoutSec 3 -UseBasicParsing
        Write-Host ("  [OK]    {0,-18} ({1})" -f $pair.Key, $pair.Value) -ForegroundColor Green
    } catch {
        Write-Host ("  [DOWN]  {0,-18} ({1})" -f $pair.Key, $pair.Value) -ForegroundColor Red
    }
}
Write-Host ""

# ────────────────────────────────────────────────────────────────────────────
# Section 6: Airflow DAGs
# ────────────────────────────────────────────────────────────────────────────
Write-Host "[6] AIRFLOW DAGS" -ForegroundColor Yellow

$dagOutput = docker exec infrastructure-airflow-webserver-1 airflow dags list 2>&1 | Select-String -Pattern "dbt_hourly|forecast_backfill|powerbi_weekly_export"
$dagOutput | ForEach-Object {
    Write-Host "  $($_.Line)" -ForegroundColor Gray
}
Write-Host ""

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Diagnostic complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

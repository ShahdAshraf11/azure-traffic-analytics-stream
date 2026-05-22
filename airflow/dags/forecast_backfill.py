
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator


default_args = {
    "owner": "data-engineering",
    "retries": 0,                       # NO retries — operator should investigate failures manually
    "depends_on_past": False,
    "email_on_failure": False,
}


with DAG(
    dag_id="forecast_backfill",
    default_args=default_args,
    description="Manually trigger forecast buffer backfill from raw_events",
    schedule_interval=None,             # NO schedule — manual only
    start_date=datetime(2026, 5, 1),
    catchup=False,
    max_active_runs=1,                  # never run two backfills at once
    tags=["forecast", "backfill", "manual", "recovery"],
) as dag:

    start = EmptyOperator(task_id="start")

    # ── Warning task — reminds the operator to stop the consumer first ──
    # This prints a banner in the logs. It's purely informational.
    warning_banner = BashOperator(
        task_id="warning_banner",
        bash_command=(
            "echo '═══════════════════════════════════════════════════════' && "
            "echo '  FORECAST BACKFILL STARTING' && "
            "echo '═══════════════════════════════════════════════════════' && "
            "echo 'IMPORTANT: The consumer should be STOPPED before this runs.' && "
            "echo 'If the consumer is running, the backfill might be overwritten.' && "
            "echo '═══════════════════════════════════════════════════════'"
        ),
    )

    # ── Run the backfill script ──
    # The script lives in the project root, mounted at /opt/project
    run_backfill = BashOperator(
        task_id="run_backfill",
        bash_command=(
            "cd /opt/project && "
            "python scripts/backfill_forecast_buffers.py "
            "--max-readings 200 "
            "--hours-back 72"
        ),
        env={
            "PGHOST":     "{{ var.value.get('traffic_db_host', 'postgres') }}",
            "PGPORT":     "{{ var.value.get('traffic_db_port', '5432') }}",
            "PGDATABASE": "{{ var.value.get('traffic_db_name', 'traffic_db') }}",
            "PGUSER":     "{{ var.value.get('traffic_db_user', 'postgres') }}",
            "PGPASSWORD": "{{ var.value.get('traffic_db_password', 'postgres') }}",
        },
    )

    # ── Verify the buffers file was created ──
    verify_buffers = BashOperator(
        task_id="verify_buffers",
        bash_command=(
            "FILE=/opt/project/logs/forecast_buffers.pkl && "
            "if [ ! -f \"$FILE\" ]; then "
            "  echo 'ERROR: forecast_buffers.pkl was not created'; exit 1; "
            "fi && "
            "SIZE=$(stat -c%s \"$FILE\") && "
            "echo \"Buffer file size: $SIZE bytes\" && "
            "if [ $SIZE -lt 10000 ]; then "
            "  echo 'WARNING: Buffer file is very small — backfill may have had little data'; "
            "fi"
        ),
    )

    # ── Final reminder ──
    completion_banner = BashOperator(
        task_id="completion_banner",
        bash_command=(
            "echo '═══════════════════════════════════════════════════════' && "
            "echo ' FORECAST BACKFILL COMPLETE' && "
            "echo '═══════════════════════════════════════════════════════' && "
            "echo 'NEXT STEP: Restart the consumer to load the warm buffers.' && "
            "echo '  python stream_processor/consumer.py' && "
            "echo '═══════════════════════════════════════════════════════'"
        ),
    )

    end = EmptyOperator(task_id="end")

    # ── Pipeline ──
    start >> warning_banner >> run_backfill >> verify_buffers >> completion_banner >> end

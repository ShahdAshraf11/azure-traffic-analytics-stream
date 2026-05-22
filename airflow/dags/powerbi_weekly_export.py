from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator


default_args = {
    "owner": "data-engineering",
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
    "depends_on_past": False,
    "email_on_failure": False,
}



# Helper function 

def cleanup_old_exports(**context):
    """
    Delete export files older than 30 days. Keeps disk usage in check.
    """
    import os
    import glob
    from datetime import datetime, timedelta

    export_dir = "/opt/project/exports"
    cutoff = datetime.now() - timedelta(days=30)

    if not os.path.exists(export_dir):
        print(f"Export dir {export_dir} doesn't exist — skipping cleanup")
        return

    deleted = 0
    for path in glob.glob(f"{export_dir}/traffic_export_*.sql"):
        mtime = datetime.fromtimestamp(os.path.getmtime(path))
        if mtime < cutoff:
            os.remove(path)
            print(f"Deleted old export: {path}")
            deleted += 1

    print(f"Cleanup done. Deleted {deleted} old export files.")



with DAG(
    dag_id="powerbi_weekly_export",
    default_args=default_args,
    description="Weekly Power BI data export (Sundays 3 AM Cairo)",
    # Cron syntax: minute hour day-of-month month day-of-week
    # "0 1 * * 0" = 1 AM UTC every Sunday = 3 AM Cairo (UTC+2)
    schedule_interval="0 1 * * 0",
    start_date=datetime(2026, 5, 1),
    catchup=False,
    max_active_runs=1,
    tags=["powerbi", "export", "weekly"],
) as dag:

    start = EmptyOperator(task_id="start")

    #  Make sure the exports directory exists 
    ensure_export_dir = BashOperator(
        task_id="ensure_export_dir",
        bash_command="mkdir -p /opt/project/exports",
    )

    #  Dump the warehouse schema to a timestamped .sql file 
    export_warehouse = BashOperator(
        task_id="export_warehouse",
        bash_command=(
            "PGPASSWORD=$TRAFFIC_DB_PASSWORD pg_dump "
            "-h $TRAFFIC_DB_HOST "
            "-p $TRAFFIC_DB_PORT "
            "-U $TRAFFIC_DB_USER "
            "-d $TRAFFIC_DB_NAME "
            "--schema=warehouse "
            "--no-owner "
            "--no-privileges "
            "-f /opt/project/exports/traffic_export_{{ ds }}.sql && "
            "ls -lh /opt/project/exports/traffic_export_{{ ds }}.sql"
        ),
    )

    #  Verify the file was created and has reasonable size 
    verify_export = BashOperator(
        task_id="verify_export",
        bash_command=(
            "FILE=/opt/project/exports/traffic_export_{{ ds }}.sql && "
            "if [ ! -f \"$FILE\" ]; then echo 'ERROR: File not created'; exit 1; fi && "
            "SIZE=$(stat -c%s \"$FILE\") && "
            "if [ $SIZE -lt 10000 ]; then "
            "  echo \"WARNING: File suspiciously small ($SIZE bytes)\"; exit 1; "
            "fi && "
            "echo \"Export OK: $FILE ($SIZE bytes)\""
        ),
    )

    #  Clean up old exports (keep last 30 days) 
    cleanup = PythonOperator(
        task_id="cleanup_old_exports",
        python_callable=cleanup_old_exports,
    )

    end = EmptyOperator(task_id="end", trigger_rule="all_done")

    #  Pipeline: start → ensure_dir → export → verify → cleanup → end 
    start >> ensure_export_dir >> export_warehouse >> verify_export >> cleanup >> end

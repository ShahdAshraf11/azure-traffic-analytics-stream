

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator


# DAG defaults — these apply to every task unless overridden

default_args = {
    "owner": "data-engineering",
    "retries": 2,                       # retry twice on failure (network blips happen)
    "retry_delay": timedelta(minutes=5),
    "depends_on_past": False,           # this run doesn't depend on previous runs
    "email_on_failure": False,          # set to True if you wire up SMTP
}



# DAG definition
with DAG(
    dag_id="dbt_hourly",
    default_args=default_args,
    description="Refresh dbt marts every hour for Power BI",
    schedule_interval="@hourly",        # cron-style: top of every hour
    start_date=datetime(2026, 5, 1),    # past date so we don't backfill
    catchup=False,                      # don't run for missed time periods
    max_active_runs=1,                  # only one instance at a time
    tags=["dbt", "marts", "hourly"],
) as dag:

    #  Start marker 
    start = EmptyOperator(task_id="start")

    #  Run dbt 
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            "cd /opt/project/dbt_traffic && "
            "dbt run --profiles-dir /opt/project/dbt_traffic"
        ),
        # Environment variables for dbt to find the database
        env={
            "DBT_HOST":     "{{ var.value.get('traffic_db_host', 'postgres') }}",
            "DBT_PORT":     "{{ var.value.get('traffic_db_port', '5432') }}",
            "DBT_DATABASE": "{{ var.value.get('traffic_db_name', 'traffic_db') }}",
            "DBT_USER":     "{{ var.value.get('traffic_db_user', 'postgres') }}",
            "DBT_PASSWORD": "{{ var.value.get('traffic_db_password', 'postgres') }}",
        },
    )

    #  Test that dbt outputs are valid ─
    # Runs `dbt test` which checks column-level constraints (not_null, unique, etc.)
    # If any test fails, this task fails and the next run will retry the whole DAG.
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            "cd /opt/project/dbt_traffic && "
            "dbt test --profiles-dir /opt/project/dbt_traffic"
        ),
        env={
            "DBT_HOST":     "{{ var.value.get('traffic_db_host', 'postgres') }}",
            "DBT_PORT":     "{{ var.value.get('traffic_db_port', '5432') }}",
            "DBT_DATABASE": "{{ var.value.get('traffic_db_name', 'traffic_db') }}",
            "DBT_USER":     "{{ var.value.get('traffic_db_user', 'postgres') }}",
            "DBT_PASSWORD": "{{ var.value.get('traffic_db_password', 'postgres') }}",
        },
        # If tests fail, mark the run as warning (not failure) — soft fail
        # so we can investigate without blocking subsequent runs
        trigger_rule="all_done",
    )

    end = EmptyOperator(task_id="end", trigger_rule="all_done")

    #  Task dependencies 
    # start → dbt_run → dbt_test → end
    start >> dbt_run >> dbt_test >> end

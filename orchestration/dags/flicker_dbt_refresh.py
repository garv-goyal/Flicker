"""flicker_dbt_refresh — rebuild the dbt models without re-ingesting.

Manual-trigger DAG (schedule=None). Useful when you change a model and just want
to re-run Silver/Gold + the data-quality tests against existing Bronze data.
"""
from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator

with DAG(
    dag_id="flicker_dbt_refresh",
    description="Re-run dbt build (models + tests) against current Bronze data.",
    schedule=None,
    start_date=datetime(2026, 6, 1),
    catchup=False,
    tags=["flicker", "dbt"],
) as dag:

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command='cd "$FLICKER_HOME/warehouse" && "$FLICKER_DBT" build --profiles-dir .',
    )

"""flicker_cdc_daily — sync TMDB now-playing into Postgres → drain CDC events → dbt.

Runs daily at 07:00. Each run:
  1. tmdb_now_playing_sync: fetches real TMDB data, issues genuine INSERT/UPDATE/DELETE
     on the Postgres film_lifecycle table. Debezium captures each change off the WAL
     and publishes it to Kafka automatically (no action needed here).
  2. drain_cdc: cdc_consumer.py --drain reads accumulated Kafka events and lands them
     in bronze.raw_cdc_film_lifecycle. Stops after 15 s of silence.
  3. dbt_build: rebuilds only the CDC models (Silver + Gold) rather than the full DAG,
     so this run never blocks or conflicts with flicker_daily_pipeline.

max_active_runs=1 prevents two syncs running simultaneously (DuckDB is single-writer).
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "flicker",
    "retries": 1,
    "retry_delay": timedelta(minutes=3),
}

with DAG(
    dag_id="flicker_cdc_daily",
    description="TMDB now-playing → Postgres → CDC consumer → dbt (CDC models only).",
    default_args=default_args,
    schedule="0 7 * * *",
    start_date=datetime(2026, 6, 1),
    catchup=False,
    max_active_runs=1,
    tags=["flicker", "cdc"],
) as dag:

    sync_now_playing = BashOperator(
        task_id="sync_now_playing",
        bash_command=(
            'cd "$FLICKER_HOME" && '
            '"$FLICKER_PY" streaming/cdc/tmdb_now_playing_sync.py'
        ),
    )

    drain_cdc = BashOperator(
        task_id="drain_cdc",
        bash_command=(
            'cd "$FLICKER_HOME" && '
            '"$FLICKER_PY" streaming/cdc/cdc_consumer.py --drain'
        ),
    )

    dbt_build_cdc = BashOperator(
        task_id="dbt_build_cdc",
        bash_command=(
            'cd "$FLICKER_HOME/warehouse" && '
            '"$FLICKER_DBT" build --profiles-dir . '
            '--select stg_film_lifecycle mart_film_lifecycle_current mart_lifecycle_changes'
        ),
    )

    sync_now_playing >> drain_cdc >> dbt_build_cdc

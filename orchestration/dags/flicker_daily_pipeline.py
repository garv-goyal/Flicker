"""flicker_daily_pipeline — the end-to-end ETL, scheduled daily.

    ingest_tmdb → enrich_omdb → fetch_trailers → dbt_build → health_check

The tasks run STRICTLY in sequence on purpose: DuckDB is a single-writer database,
so two ingestion tasks writing at once would deadlock on the file lock. Serializing
them is the correct design for this warehouse. Each task shells out to the project's
isolated virtualenv (FLICKER_PY / FLICKER_DBT) against the mounted project at
FLICKER_HOME. Daily batch sizes are small top-ups (the historical backfill is a
separate one-off run).
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "flicker",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="flicker_daily_pipeline",
    description="Ingest TMDB/OMDb/YouTube, then transform with dbt.",
    default_args=default_args,
    schedule="0 6 * * *",          # every day at 06:00
    start_date=datetime(2026, 6, 1),
    catchup=False,
    max_active_runs=1,             # never overlap runs (single DuckDB writer)
    tags=["flicker", "etl"],
) as dag:

    ingest_tmdb = BashOperator(
        task_id="ingest_tmdb",
        bash_command='cd "$FLICKER_HOME" && "$FLICKER_PY" ingestion/tmdb_movies.py 100',
    )

    enrich_omdb = BashOperator(
        task_id="enrich_omdb",
        bash_command='cd "$FLICKER_HOME" && "$FLICKER_PY" ingestion/omdb_enrich.py 100',
    )

    fetch_trailers = BashOperator(
        task_id="fetch_trailers",
        bash_command='cd "$FLICKER_HOME" && "$FLICKER_PY" ingestion/youtube_trailers.py 25',
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command='cd "$FLICKER_HOME/warehouse" && "$FLICKER_DBT" build --profiles-dir .',
    )

    health_check = BashOperator(
        task_id="health_check",
        bash_command='cd "$FLICKER_HOME" && "$FLICKER_PY" pipeline_health.py',
    )

    ingest_tmdb >> enrich_omdb >> fetch_trailers >> dbt_build >> health_check

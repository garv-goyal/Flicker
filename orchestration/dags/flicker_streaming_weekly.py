"""flicker_streaming_weekly — refresh YouTube comment buzz + VADER sentiment.

Runs every Sunday at 09:00. Each run:
  1. produce_comments: youtube_comments_producer.py fetches comments for all tracked
     trailers and publishes them to the Kafka buzz topic.
  2. consume_buzz: bluesky_consumer.py --drain reads new comments from Kafka into
     bronze.raw_buzz_events. Stops after 15 s of silence.
  3. score_sentiment: buzz_sentiment.py runs VADER over any un-scored comments and
     writes results to bronze.raw_buzz_sentiment.
  4. dbt_build_buzz: rebuilds the sentiment models (Silver + Gold) only.

Weekly cadence is sufficient — YouTube comment distributions on trailers shift slowly,
and the YouTube Data API quota (10,000 units/day) is consumed in step 1.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "flicker",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="flicker_streaming_weekly",
    description="YouTube comments → Kafka → Bronze → VADER sentiment → dbt.",
    default_args=default_args,
    schedule="0 9 * * 0",
    start_date=datetime(2026, 6, 1),
    catchup=False,
    max_active_runs=1,
    tags=["flicker", "streaming", "sentiment"],
) as dag:

    produce_comments = BashOperator(
        task_id="produce_comments",
        bash_command=(
            'cd "$FLICKER_HOME" && '
            '"$FLICKER_PY" streaming/youtube_comments_producer.py'
        ),
    )

    consume_buzz = BashOperator(
        task_id="consume_buzz",
        bash_command=(
            'cd "$FLICKER_HOME" && '
            '"$FLICKER_PY" streaming/bluesky_consumer.py --drain'
        ),
    )

    score_sentiment = BashOperator(
        task_id="score_sentiment",
        bash_command=(
            'cd "$FLICKER_HOME" && '
            '"$FLICKER_PY" streaming/buzz_sentiment.py'
        ),
    )

    dbt_build_buzz = BashOperator(
        task_id="dbt_build_buzz",
        bash_command=(
            'cd "$FLICKER_HOME/warehouse" && '
            '"$FLICKER_DBT" build --profiles-dir . '
            '--select stg_buzz mart_film_buzz mart_buzz_vs_critics'
        ),
    )

    produce_comments >> consume_buzz >> score_sentiment >> dbt_build_buzz

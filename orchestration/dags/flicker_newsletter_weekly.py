"""flicker_newsletter_weekly — send the Flicker weekly newsletter.

Runs every Sunday at 10:00, one hour after flicker_streaming_weekly finishes
refreshing the sentiment data and rebuilding Gold models.

Single task: send_newsletter runs newsletter/send_newsletter.py, which:
  1. Queries bronze.newsletter_subscribers for active emails.
  2. Calls get_picks() per subscriber (filtered by genre_pref if set).
  3. Renders the HTML email template.
  4. Sends via the Resend API.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "flicker",
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
}

with DAG(
    dag_id="flicker_newsletter_weekly",
    description="Build data-backed movie picks and email all active subscribers.",
    default_args=default_args,
    schedule="0 10 * * 0",
    start_date=datetime(2026, 6, 1),
    catchup=False,
    max_active_runs=1,
    tags=["flicker", "newsletter"],
) as dag:

    send_newsletter = BashOperator(
        task_id="send_newsletter",
        bash_command='cd "$FLICKER_HOME" && "$FLICKER_PY" newsletter/send_newsletter.py',
    )

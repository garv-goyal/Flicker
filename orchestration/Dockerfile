# Airflow image for Flicker. The project's runtime deps (duckdb, dbt, ingestion
# libraries) live in a SEPARATE virtualenv so they can't clash with Airflow's
# own dependency pins. DAGs shell out to /opt/flicker-venv/bin/{python,dbt}.
FROM apache/airflow:2.10.4-python3.12

COPY orchestration/airflow-requirements.txt /tmp/flicker-requirements.txt

# Build the isolated venv as root (the airflow user can't write to /opt). It only
# needs to be world-runnable afterwards, which venvs are by default.
USER root
RUN python -m venv /opt/flicker-venv \
    && /opt/flicker-venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/flicker-venv/bin/pip install --no-cache-dir -r /tmp/flicker-requirements.txt
USER airflow

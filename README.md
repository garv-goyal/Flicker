# Flicker - Entertainment Analytics Data Platform

A portfolio data engineering project that ingests from five sources (TMDB, OMDb,
YouTube, a live Kafka comment stream, and a simulated Postgres CDC feed), processes
through a Medallion architecture (Bronze → Silver → Gold), orchestrates with Airflow,
streams with Kafka + Debezium, models with dbt on DuckDB/MotherDuck, and serves a
Streamlit dashboard with a Text-to-SQL chatbot.

**Live dashboard →** https://flicker.streamlit.app

## Stack

Python · TMDB / OMDb / YouTube APIs · Apache Kafka · Debezium (CDC) · Apache Airflow · DuckDB + MotherDuck · dbt Core · VADER Sentiment · Streamlit · Gemini (Text-to-SQL) · Docker

## Architecture

```
APIs (TMDB, OMDb, YouTube)
  └─ ingestion/*.py ──────────────────────────────┐
                                                   │
Kafka + Debezium (CDC off Postgres WAL)            ▼
  └─ streaming/*.py ─────────────────── Bronze (DuckDB / MotherDuck)
                                                   │
                                              dbt Silver
                                                   │
                                              dbt Gold ── Streamlit dashboard
```

Batch ingestion pulls the ~2,000 most-popular films from TMDB and enriches them
with critic scores (OMDb), trailer engagement (YouTube), and YouTube comment
sentiment (VADER). A simulated Postgres operational database tracks each film's
theatrical run; Debezium streams every INSERT/UPDATE/DELETE off the WAL into Kafka
and then into the warehouse — current state is rebuilt entirely from the change
stream, not batch snapshots.

## Pages

| Page | What it shows |
|------|---------------|
| Overview | KPIs, ROI by decade, audience sentiment vs critics scatter |
| Critical Reception | Two-sided divergence — films audiences loved that critics panned, and vice versa |
| Hype vs Reality | Trailer buzz vs box-office ROI; does sentiment predict returns? |
| Genre Trends | Annual output, avg ROI, and total revenue per genre since 1990 |
| Operations | Live theatrical run rebuilt from CDC events — current state + change feed |
| Newsletter | Genre-personalised weekly pick (subscribe form → DuckDB) |
| Chat | Text-to-SQL chatbot powered by Gemini — ask anything about the dataset |

## Local setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in API keys
python warehouse/setup_duckdb.py
python verify_setup.py
```

## Batch pipeline

```bash
python ingestion/tmdb_movies.py        # TMDB → Bronze
python ingestion/omdb_enrich.py        # OMDb critic scores → Bronze
python ingestion/youtube_trailers.py   # YouTube trailer stats → Bronze
cd warehouse && dbt build --profiles-dir .
```

## Streaming (Kafka + sentiment)

```bash
docker compose up -d kafka
python streaming/youtube_comments_producer.py   # trailer comments → Kafka
python streaming/bluesky_consumer.py            # Kafka → Bronze
python streaming/buzz_sentiment.py              # VADER score comments → Bronze
cd warehouse && dbt build --profiles-dir .
```

## Change data capture (Postgres → Debezium → Kafka)

```bash
docker compose up -d kafka postgres connect
python streaming/cdc/cdc_seed.py --reset        # seed Postgres film_lifecycle table
python streaming/cdc/register_connector.py      # register Debezium connector
python streaming/cdc/cdc_simulator.py           # simulate INSERT/UPDATE/DELETE
python streaming/cdc/cdc_consumer.py --drain    # CDC events → Bronze
cd warehouse && dbt build --profiles-dir .
```

## Dashboard

```bash
streamlit run dashboard/app.py    # run from project root
```

## Orchestration

```bash
docker compose up -d --build airflow    # Airflow at http://localhost:8080
```

## Project layout

```
ingestion/          batch API → Bronze (TMDB, OMDb, YouTube)
streaming/          Kafka producers/consumers + sentiment scorer
streaming/cdc/      Postgres seed, Debezium connector, simulator, CDC consumer
warehouse/          dbt project — models for Bronze → Silver → Gold
orchestration/      Airflow DAGs (daily pipeline, weekly newsletter, CDC refresh)
dashboard/          Streamlit app + utils (queries, chatbot, UI helpers)
docker-compose.yml  Kafka, Postgres, Debezium Connect, Airflow
```

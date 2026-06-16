# Flicker — Entertainment Analytics Data Platform

Ingests data from multiple entertainment sources (TMDB, OMDb, YouTube data + a
streaming YouTube-comment buzz feed, and a simulated Postgres CDC source),
processes it through a Medallion architecture (Bronze → Silver → Gold),
orchestrates batch with Airflow, streams with Kafka (+ Debezium for change data
capture), models with dbt on DuckDB/MotherDuck, and serves a polished Streamlit
dashboard.

**Status:** Phases 0–5 complete (ingestion, warehouse, dashboard, Airflow,
Kafka streaming + sentiment, Debezium CDC). Remaining: Text-to-SQL chat + deploy.

## Stack
Python · TMDB/OMDb/YouTube APIs · Kafka · Debezium · Airflow · DuckDB + MotherDuck · dbt Core · VADER · Streamlit · Docker

The warehouse is **DuckDB** — a local `flicker.duckdb` file holds the
`bronze`/`silver`/`gold` schemas (no account, no card). The free **MotherDuck**
cloud tier hosts a copy so the deployed dashboard reads from a real cloud warehouse.

## Local setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then fill in your API keys
python warehouse/setup_duckdb.py
python verify_setup.py
```

## Batch pipeline

```bash
python ingestion/tmdb_movies.py        # TMDB → Bronze
python ingestion/omdb_enrich.py        # OMDb critical scores → Bronze
python ingestion/youtube_trailers.py   # YouTube trailer stats → Bronze
cd warehouse && dbt build --profiles-dir .
```

## Streaming buzz (Kafka + sentiment)

```bash
docker compose up -d kafka
python streaming/youtube_comments_producer.py   # trailer comments → Kafka
python streaming/bluesky_consumer.py             # Kafka → Bronze (source-neutral)
python streaming/buzz_sentiment.py               # VADER score each comment → Bronze
cd warehouse && dbt build --profiles-dir .
```

## Change data capture (Postgres → Debezium → Kafka)

```bash
docker compose up -d kafka postgres connect
python streaming/cdc/cdc_seed.py --reset         # seed operational Postgres table
python streaming/cdc/register_connector.py       # register Debezium connector
python streaming/cdc/cdc_simulator.py            # mutate rows (insert/update/delete)
python streaming/cdc/cdc_consumer.py --drain     # CDC events → Bronze
cd warehouse && dbt build --profiles-dir .
```

## Dashboard

```bash
streamlit run dashboard/app.py        # run from project root
```

## Orchestration

```bash
docker compose up -d --build airflow  # Airflow at http://localhost:8080
```

## Layout

```
ingestion/      # batch API → Bronze (TMDB, OMDb, YouTube)
streaming/      # Kafka producers/consumers + sentiment scorer
streaming/cdc/  # Postgres seed, Debezium connector, simulator, CDC consumer
warehouse/      # dbt project: Bronze → Silver → Gold models
orchestration/  # Airflow DAGs
dashboard/      # Streamlit app (Overview, Critical, Hype, Genres, Operations)
docker-compose.yml  # Kafka, Postgres, Debezium Connect, Airflow
```

See `FLICKER_PROJECT.md` (one level up) for the full blueprint.

# Flicker - Entertainment Analytics Data Platform

A data engineering project that ingests from five sources (TMDB, OMDb, YouTube, a
live Kafka comment stream, and a simulated Postgres CDC feed), processes through a
Medallion architecture (Bronze → Silver → Gold), orchestrates with Airflow, streams
with Kafka + Debezium, models with dbt on DuckDB/MotherDuck, and serves a Next.js
web app off the Gold layer.

**Live app →** <https://getflicker.vercel.app>

## Stack

Python · TMDB / OMDb / YouTube APIs · Apache Kafka · Debezium (CDC) · Apache Airflow · DuckDB + MotherDuck · dbt Core · VADER Sentiment · Next.js / TypeScript · Gemini · Docker · Vercel

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
                                              dbt Gold ── web/ (Next.js, on Vercel)
```

Batch ingestion pulls the ~2,000 most-popular films from TMDB and enriches them
with critic scores (OMDb), trailer engagement (YouTube), and YouTube comment
sentiment (VADER). A simulated Postgres operational database tracks each film's
theatrical run; Debezium streams every INSERT/UPDATE/DELETE off the WAL into Kafka
and then into the warehouse — current state is rebuilt entirely from the change
stream, not batch snapshots. The web app reads the Gold-layer tables from
MotherDuck.

## Web app (web/, Next.js)

| Page | What it shows |
| --- | --- |
| Pulse (home) | KPIs, ROI by decade, today's featured film, highest-ROI genres and films |
| Critics | Composite critic/audience scores, Oscar winners, where critics and audiences disagree |
| Hype vs Reality | Trailer buzz vs box-office ROI — overhyped films vs hidden gems |
| Discover | Mood-based film picker (prestige, blockbuster, feel-good, etc.) |
| Newsletter | Genre-personalised weekly pick (subscribe form → MotherDuck) |
| Chat (widget) | Conversational assistant — ask anything about the dataset, answers from live data |

### Web app environment variables

| Variable | Required | Notes |
| --- | --- | --- |
| `FLICKER_USE_MOTHERDUCK` | yes | `true` to read from MotherDuck cloud; `false` for a local `flicker.duckdb` file |
| `MOTHERDUCK_TOKEN` | if using MotherDuck | from motherduck.com |
| `MOTHERDUCK_DATABASE` | if using MotherDuck | defaults to `flicker` |
| `FLICKER_DB_PATH` | if not using MotherDuck | path to local `.duckdb` file |
| `GEMINI_API_KEY` | yes | powers the chat widget (Google AI Studio, free tier) |

### Web app architecture notes

- All data access goes through API routes (`web/src/app/api/*`), not server
  components — pages are client components that `fetch` from these routes. This
  keeps the native `@duckdb/node-api` binding out of the React render path.
- `web/src/lib/db.ts` holds a single shared DuckDB/MotherDuck connection per
  serverless invocation, serializes queries onto it, and retries on connect
  failure — the native binding isn't safe under concurrent connect/query calls.
- **Production builds use Webpack, not Turbopack** (`next build --webpack` in
  `web/package.json`). Turbopack does not correctly externalize `@duckdb/node-api`
  for dynamically-rendered routes (any route reading query params or a request
  body) — those routes built fine but crashed at runtime on Vercel under Turbopack.
- `db.ts` explicitly sets `home_directory` for DuckDB and falls back
  `process.env.HOME` to `/tmp` — Vercel's Lambda runtime doesn't set `HOME`, which
  DuckDB needs to resolve its config/extension directory.

### Deploying the web app

On Vercel: set **Root Directory** to `web`, **Framework Preset** to **Next.js**, add
the environment variables above (Production + Preview), and deploy. No `vercel.json`
is needed — Vercel's Root Directory setting handles the subdirectory.

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

## Web app

```bash
cd web && npm install
cp .env.local.example .env.local   # fill in MOTHERDUCK_TOKEN, GEMINI_API_KEY, etc.
npm run dev                        # http://localhost:3000
```

See "Web app environment variables" and "Deploying the web app" above for the
required env vars and Vercel setup.

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
web/                Next.js app (pages, API routes, chatbot) — deployed on Vercel
db_conn.py          shared DuckDB/MotherDuck connection helper for Python scripts
docker-compose.yml  Kafka, Postgres, Debezium Connect, Airflow
```

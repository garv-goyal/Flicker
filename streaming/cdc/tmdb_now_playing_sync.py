"""CDC source — sync TMDB "now playing" films into the operational Postgres table.

Replaces cdc_seed.py + cdc_simulator.py with real TMDB data.

On each run:
  - Fetches all films from TMDB /movie/now_playing (all pages)
  - INSERTs new films          → Debezium captures as INSERT
  - UPDATEs films whose data changed (only when popularity/votes actually differ)
    → Debezium captures as UPDATE
  - DELETEs films no longer in now_playing → Debezium captures as DELETE
  - Status derived from first_seen_at: <7d=Now Playing, 7-21d=Holdover, >21d=Leaving Soon

Run once manually or on a daily Airflow schedule — each run generates real CDC events
that flow: Postgres WAL → Debezium → Kafka → cdc_consumer → Bronze → dbt → Operations.

Usage:
    python streaming/cdc/tmdb_now_playing_sync.py
    python streaming/cdc/tmdb_now_playing_sync.py --reset   # drop + recreate table first
"""
import argparse
import os
import sys
import time

import psycopg2
import psycopg2.extras
import requests
from dotenv import load_dotenv

load_dotenv()

PG = dict(
    host=os.getenv("PG_HOST", "localhost"),
    port=int(os.getenv("PG_PORT", "5432")),
    user=os.getenv("PG_USER", "flicker"),
    password=os.getenv("PG_PASSWORD", "flicker"),
    dbname=os.getenv("PG_DB", "flicker_ops"),
)

TMDB_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_BASE = "https://api.themoviedb.org/3"

DDL = """
CREATE TABLE IF NOT EXISTS public.film_lifecycle (
    tmdb_id        INTEGER          PRIMARY KEY,
    title          TEXT             NOT NULL,
    status         TEXT             NOT NULL,
    popularity     DOUBLE PRECISION NOT NULL,
    vote_count     INTEGER          NOT NULL,
    vote_average   DOUBLE PRECISION NOT NULL,
    first_seen_at  TIMESTAMPTZ      NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ      NOT NULL DEFAULT now()
);
ALTER TABLE public.film_lifecycle REPLICA IDENTITY FULL;
"""

UPSERT = """
INSERT INTO public.film_lifecycle
    (tmdb_id, title, status, popularity, vote_count, vote_average)
VALUES %s
ON CONFLICT (tmdb_id) DO UPDATE
    SET title        = EXCLUDED.title,
        status       = CASE
            WHEN now() - film_lifecycle.first_seen_at < interval '7 days'  THEN 'Now Playing'
            WHEN now() - film_lifecycle.first_seen_at < interval '21 days' THEN 'Holdover'
            ELSE 'Leaving Soon'
        END,
        popularity   = EXCLUDED.popularity,
        vote_count   = EXCLUDED.vote_count,
        vote_average = EXCLUDED.vote_average,
        updated_at   = now()
    WHERE film_lifecycle.popularity   IS DISTINCT FROM EXCLUDED.popularity
       OR film_lifecycle.vote_count   IS DISTINCT FROM EXCLUDED.vote_count
       OR film_lifecycle.vote_average IS DISTINCT FROM EXCLUDED.vote_average
"""


def fetch_now_playing():
    if not TMDB_KEY:
        sys.exit("TMDB_API_KEY not set in environment")
    seen: dict = {}
    page, total_pages = 1, 1
    while page <= total_pages:
        r = requests.get(
            f"{TMDB_BASE}/movie/now_playing",
            params={"api_key": TMDB_KEY, "language": "en-US", "region": "US", "page": page},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        for f in data.get("results", []):
            fid = f["id"]
            if fid not in seen or f.get("popularity", 0) > seen[fid].get("popularity", 0):
                seen[fid] = f
        total_pages = min(data.get("total_pages", 1), 5)  # cap at 5 pages (~100 films)
        page += 1
        if page <= total_pages:
            time.sleep(0.25)
    return list(seen.values())


def derive_status(age_days: int) -> str:
    if age_days < 7:
        return "Now Playing"
    if age_days < 21:
        return "Holdover"
    return "Leaving Soon"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="drop + recreate table first")
    args = ap.parse_args()

    print("Fetching TMDB now_playing …")
    films = fetch_now_playing()
    print(f"  {len(films)} films returned by TMDB")

    incoming_ids = {f["id"] for f in films}

    conn = psycopg2.connect(**PG)
    conn.autocommit = True
    cur = conn.cursor()

    if args.reset:
        cur.execute("DROP TABLE IF EXISTS public.film_lifecycle")
        print("  Dropped existing table.")

    cur.execute(DDL)

    rows = [
        (
            f["id"],
            f.get("title") or f.get("name", "Unknown"),
            "Now Playing",  # initial status for new inserts; DO UPDATE recalculates for existing
            round(f.get("popularity", 0.0), 3),
            f.get("vote_count", 0),
            round(f.get("vote_average", 0.0), 1),
        )
        for f in films
    ]

    psycopg2.extras.execute_values(cur, UPSERT, rows, page_size=100)
    cur.execute("SELECT count(*) FROM public.film_lifecycle")
    total = cur.fetchone()[0]
    print(f"  Upserted {len(rows)} now-playing films; table holds {total} rows")

    cur.execute("SELECT tmdb_id FROM public.film_lifecycle")
    existing_ids = {row[0] for row in cur.fetchall()}
    to_delete = existing_ids - incoming_ids
    if to_delete:
        cur.executemany(
            "DELETE FROM public.film_lifecycle WHERE tmdb_id = %s",
            [(i,) for i in to_delete],
        )
        print(f"  Deleted {len(to_delete)} films no longer in now_playing")
    else:
        print("  No films to delete — all existing films still in now_playing")

    conn.close()
    print("Done. Debezium will have captured each INSERT / UPDATE / DELETE off the WAL.")


if __name__ == "__main__":
    main()

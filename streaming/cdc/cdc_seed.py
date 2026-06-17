"""Phase 5 / CDC — seed the simulated OPERATIONAL database (Postgres).

Creates public.film_lifecycle and populates it with recent films pulled from the
warehouse (gold.dim_titles). This table is the "source system": a row per film in
theatrical release, with mutable operational state (status, screen count, ticket
price, weekend gross). The simulator then mutates it and Debezium captures every
change off the write-ahead log.

REPLICA IDENTITY FULL makes Postgres log the *complete* previous row on every
UPDATE/DELETE, so CDC events carry a full before-image (we can show before→after
transitions, not just the changed columns).

Usage:
    python streaming/cdc/cdc_seed.py            # create + seed (~40 films)
    python streaming/cdc/cdc_seed.py --films 60 --reset
"""
import argparse
import os
import random
import sys

import duckdb
import psycopg2
import psycopg2.extras

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from db_conn import DEFAULT_DB_PATH

PG = dict(host=os.getenv("PG_HOST", "localhost"), port=int(os.getenv("PG_PORT", "5432")),
          user=os.getenv("PG_USER", "flicker"), password=os.getenv("PG_PASSWORD", "flicker"),
          dbname=os.getenv("PG_DB", "flicker_ops"))

DDL = """
CREATE TABLE IF NOT EXISTS public.film_lifecycle (
    tmdb_id        INTEGER PRIMARY KEY,
    title          TEXT        NOT NULL,
    status         TEXT        NOT NULL,
    screens        INTEGER     NOT NULL,
    ticket_price   NUMERIC(5,2) NOT NULL,
    weekend_gross  BIGINT      NOT NULL,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.film_lifecycle REPLICA IDENTITY FULL;
"""


def seed_rows(n_films: int):
    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    rows = con.execute(f"""
        select tmdb_id, title
        from gold.dim_titles
        where release_year >= 2022 and title is not null
        order by random()
        limit {n_films}
    """).fetchall()
    con.close()
    seeded = []
    for tmdb_id, title in rows:
        screens = random.randint(1800, 4200)
        price = round(random.uniform(9.5, 16.5), 2)
        gross = screens * random.randint(2000, 9000)
        seeded.append((tmdb_id, title, "Now Playing", screens, price, gross))
    return seeded


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--films", type=int, default=40)
    ap.add_argument("--reset", action="store_true", help="drop the table first")
    args = ap.parse_args()

    conn = psycopg2.connect(**PG)
    conn.autocommit = True
    cur = conn.cursor()
    if args.reset:
        cur.execute("DROP TABLE IF EXISTS public.film_lifecycle")
    cur.execute(DDL)

    rows = seed_rows(args.films)
    psycopg2.extras.execute_values(cur, """
        INSERT INTO public.film_lifecycle
            (tmdb_id, title, status, screens, ticket_price, weekend_gross)
        VALUES %s
        ON CONFLICT (tmdb_id) DO NOTHING
    """, rows)

    cur.execute("SELECT count(*) FROM public.film_lifecycle")
    total = cur.fetchone()[0]
    conn.close()
    print(f"Seeded {len(rows)} films; film_lifecycle now holds {total} rows "
          f"(all 'Now Playing'). REPLICA IDENTITY FULL set.")


if __name__ == "__main__":
    main()

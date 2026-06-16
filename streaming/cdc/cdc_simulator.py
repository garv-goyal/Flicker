"""Phase 5 / CDC — mutate the operational database so Debezium has changes to capture.

Simulates the life of films in theatrical release by issuing INSERT / UPDATE /
DELETE statements against public.film_lifecycle. Every statement is picked up off
the Postgres WAL by Debezium and streamed to Kafka — no polling, no "updated_at"
scanning. This is the whole point of CDC: the warehouse sees row mutations the
moment they happen.

Each tick does a few operations:
  • UPDATE  — a film drops screens, adjusts price, posts a lower weekend gross, and
              periodically advances status (Now Playing → Holdover → Leaving Soon → Ended)
  • INSERT  — a brand-new release opens wide as "Now Playing"
  • DELETE  — an "Ended" film is pulled from the operational system

Usage:
    python streaming/cdc/cdc_simulator.py                 # 40 ticks, ~0.4s apart
    python streaming/cdc/cdc_simulator.py --ticks 80 --sleep 0.2
"""
import argparse
import os
import random
import sys
import time

import duckdb
import psycopg2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from dashboard.utils.duckdb_conn import DEFAULT_DB_PATH

PG = dict(host=os.getenv("PG_HOST", "localhost"), port=int(os.getenv("PG_PORT", "5432")),
          user=os.getenv("PG_USER", "flicker"), password=os.getenv("PG_PASSWORD", "flicker"),
          dbname=os.getenv("PG_DB", "flicker_ops"))

NEXT_STATUS = {"Now Playing": "Holdover", "Holdover": "Leaving Soon",
               "Leaving Soon": "Ended"}


def candidate_pool(exclude_ids, limit=200):
    """New releases we can INSERT later — films not already in the op table."""
    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    rows = con.execute(f"""
        select tmdb_id, title from gold.dim_titles
        where release_year >= 2022 and title is not null
        order by random() limit {limit}
    """).fetchall()
    con.close()
    return [(t, n) for t, n in rows if t not in exclude_ids]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticks", type=int, default=40)
    ap.add_argument("--sleep", type=float, default=0.4)
    args = ap.parse_args()

    conn = psycopg2.connect(**PG)
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute("SELECT tmdb_id FROM public.film_lifecycle")
    live_ids = {r[0] for r in cur.fetchall()}
    pool = candidate_pool(live_ids)
    random.shuffle(pool)

    counts = {"insert": 0, "update": 0, "delete": 0}
    for _ in range(args.ticks):
        roll = random.random()

        # ~12% INSERT a new release
        if roll < 0.12 and pool:
            tmdb_id, title = pool.pop()
            screens = random.randint(2500, 4300)
            price = round(random.uniform(10.0, 16.5), 2)
            cur.execute("""INSERT INTO public.film_lifecycle
                (tmdb_id, title, status, screens, ticket_price, weekend_gross, updated_at)
                VALUES (%s,%s,'Now Playing',%s,%s,%s, now())
                ON CONFLICT (tmdb_id) DO NOTHING""",
                (tmdb_id, title, screens, price, screens * random.randint(3000, 9000)))
            if cur.rowcount:
                live_ids.add(tmdb_id); counts["insert"] += 1

        # ~10% DELETE an Ended film (pulled from the operational system)
        elif roll < 0.22:
            cur.execute("""SELECT tmdb_id FROM public.film_lifecycle
                           WHERE status='Ended' ORDER BY random() LIMIT 1""")
            r = cur.fetchone()
            if r:
                cur.execute("DELETE FROM public.film_lifecycle WHERE tmdb_id=%s", (r[0],))
                live_ids.discard(r[0]); counts["delete"] += 1

        # ~78% UPDATE a still-running film
        else:
            cur.execute("""SELECT tmdb_id, status, screens, weekend_gross
                           FROM public.film_lifecycle WHERE status <> 'Ended'
                           ORDER BY random() LIMIT 1""")
            r = cur.fetchone()
            if r:
                tmdb_id, status, screens, gross = r
                new_screens = max(80, int(screens * random.uniform(0.55, 0.9)))
                new_gross = int(gross * random.uniform(0.4, 0.85))
                new_price = round(random.uniform(9.0, 16.5), 2)
                # ~35% of updates also advance the lifecycle status
                new_status = NEXT_STATUS.get(status, status) if random.random() < 0.35 else status
                cur.execute("""UPDATE public.film_lifecycle
                    SET status=%s, screens=%s, ticket_price=%s, weekend_gross=%s, updated_at=now()
                    WHERE tmdb_id=%s""",
                    (new_status, new_screens, new_price, new_gross, tmdb_id))
                counts["update"] += 1

        time.sleep(args.sleep)

    cur.execute("SELECT count(*), count(*) FILTER (WHERE status='Ended') FROM public.film_lifecycle")
    total, ended = cur.fetchone()
    conn.close()
    print(f"Done. Issued {sum(counts.values())} changes: "
          f"{counts['insert']} inserts, {counts['update']} updates, {counts['delete']} deletes.")
    print(f"film_lifecycle now holds {total} rows ({ended} 'Ended').")


if __name__ == "__main__":
    main()

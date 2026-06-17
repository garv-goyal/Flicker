"""OMDb → Bronze. Enriches TMDB films with critical scores, box office, and awards.

OMDb's free tier allows 1,000 requests/day, so we enrich the most popular films
first and cap the run. Joined back to TMDB on tmdb_id.

Usage:
    python ingestion/omdb_enrich.py            # default cap
    python ingestion/omdb_enrich.py 500        # enrich 500 films
"""
import os
import sys
import time
from datetime import datetime, timezone

import pandas as pd
import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_conn import get_connection

load_dotenv()

OMDB_URL = "https://www.omdbapi.com/"
DEFAULT_CAP = 900            # stay safely under the 1,000/day free-tier limit
REQUEST_TIMEOUT = 15

COLUMNS = [
    "imdb_id", "tmdb_id", "box_office", "rotten_tomatoes", "metacritic",
    "imdb_rating", "imdb_votes", "rated", "awards", "_loaded_at",
]


def targets(cap: int) -> list[tuple[int, str]]:
    """(tmdb_id, imdb_id) for the most popular films that have an IMDb id and
    aren't enriched yet."""
    conn = get_connection()
    conn.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    existing = {
        r[0] for r in conn.execute(
            "select imdb_id from bronze.raw_omdb_enrichment"
        ).fetchall()
    } if conn.execute(
        "select count(*) from information_schema.tables "
        "where table_schema='bronze' and table_name='raw_omdb_enrichment'"
    ).fetchone()[0] else set()
    rows = conn.execute("""
        select tmdb_id, imdb_id
        from bronze.raw_tmdb_movies
        where imdb_id is not null and imdb_id <> ''
        order by popularity desc
    """).fetchall()
    conn.close()
    return [(t, i) for t, i in rows if i not in existing][:cap]


def rating(ratings: list, source: str) -> str | None:
    for r in ratings or []:
        if r.get("Source") == source:
            return r.get("Value")
    return None


def fetch(session, key, imdb_id) -> dict | None:
    r = session.get(OMDB_URL, params={"apikey": key, "i": imdb_id, "tomatoes": "true"},
                    timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    return data if data.get("Response") == "True" else None


def main() -> None:
    cap = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CAP
    key = os.getenv("OMDB_API_KEY")
    if not key:
        raise SystemExit("OMDB_API_KEY not set in .env")

    todo = targets(cap)
    print(f"enriching {len(todo)} films via OMDb...")
    session = requests.Session()
    loaded_at = datetime.now(timezone.utc)
    rows, misses = [], 0

    for i, (tmdb_id, imdb_id) in enumerate(todo, 1):
        try:
            d = fetch(session, key, imdb_id)
        except Exception as e:
            print(f"  warn: {imdb_id}: {e}")
            d = None
        if d is None:
            misses += 1
        else:
            rows.append({
                "imdb_id": imdb_id,
                "tmdb_id": tmdb_id,
                "box_office": d.get("BoxOffice"),
                "rotten_tomatoes": rating(d.get("Ratings"), "Rotten Tomatoes"),
                "metacritic": d.get("Metascore"),
                "imdb_rating": d.get("imdbRating"),
                "imdb_votes": d.get("imdbVotes"),
                "rated": d.get("Rated"),
                "awards": d.get("Awards"),
                "_loaded_at": loaded_at,
            })
        if i % 100 == 0:
            print(f"  {i}/{len(todo)}")
        time.sleep(0.05)

    df = pd.DataFrame(rows, columns=COLUMNS)
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bronze.raw_omdb_enrichment (
            imdb_id VARCHAR, tmdb_id BIGINT, box_office VARCHAR,
            rotten_tomatoes VARCHAR, metacritic VARCHAR, imdb_rating VARCHAR,
            imdb_votes VARCHAR, rated VARCHAR, awards VARCHAR, _loaded_at TIMESTAMP
        )
    """)
    conn.register("new_omdb", df)
    conn.execute("DELETE FROM bronze.raw_omdb_enrichment WHERE imdb_id IN "
                 "(SELECT imdb_id FROM new_omdb)")
    conn.execute(f"INSERT INTO bronze.raw_omdb_enrichment SELECT {', '.join(COLUMNS)} "
                 "FROM new_omdb")
    total = conn.execute("SELECT COUNT(*) FROM bronze.raw_omdb_enrichment").fetchone()[0]
    conn.close()
    print(f"\ndone — enriched {len(rows)} films ({misses} not found); "
          f"bronze.raw_omdb_enrichment now holds {total} rows")


if __name__ == "__main__":
    main()

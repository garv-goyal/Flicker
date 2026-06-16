"""TMDB → Bronze. Pulls movie details from the TMDB API and lands them raw in
DuckDB at bronze.raw_tmdb_movies.

Usage:
    python ingestion/tmdb_movies.py            # default target count
    python ingestion/tmdb_movies.py 1000       # fetch ~1000 movies

Strategy: /discover/movie gives popularity-ranked IDs (cheap, paginated), then
/movie/{id} gives full details (budget, revenue, runtime, genres, collection) —
fields the list endpoints don't return. Rows are upserted by tmdb_id so re-runs
are idempotent.
"""
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone

import pandas as pd
import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dashboard.utils.duckdb_conn import get_connection

load_dotenv()

API_BASE = "https://api.themoviedb.org/3"
DEFAULT_TARGET = 300          # movies to fetch when no count is passed
MIN_VOTE_COUNT = 50           # skip obscure titles with too little signal
REQUEST_TIMEOUT = 15

# Bronze column order — the contract for the DuckDB table and the insert.
COLUMNS = [
    "tmdb_id", "imdb_id", "title", "original_title", "release_date", "genres",
    "budget", "revenue", "runtime", "vote_average", "vote_count",
    "popularity", "status", "original_language", "production_companies",
    "belongs_to_collection", "overview", "_loaded_at", "_batch_id",
]


class TMDBClient:
    """Thin TMDB REST client. Prefers the v4 bearer token, falls back to v3 key."""

    def __init__(self):
        token = os.getenv("TMDB_API_READ_ACCESS_TOKEN")
        self.api_key = os.getenv("TMDB_API_KEY")
        if not token and not self.api_key:
            raise SystemExit("No TMDB credentials in .env (TMDB_API_KEY / "
                             "TMDB_API_READ_ACCESS_TOKEN)")
        self.session = requests.Session()
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    def get(self, path: str, **params) -> dict:
        if "Authorization" not in self.session.headers:
            params["api_key"] = self.api_key
        for attempt in range(5):
            r = self.session.get(f"{API_BASE}{path}", params=params,
                                 timeout=REQUEST_TIMEOUT)
            if r.status_code == 429:  # rate limited — respect Retry-After
                time.sleep(int(r.headers.get("Retry-After", 1)) + 1)
                continue
            r.raise_for_status()
            return r.json()
        raise RuntimeError(f"TMDB request failed after retries: {path}")

    def discover_ids(self, target: int) -> list[int]:
        """Collect popularity-ranked movie IDs until we have `target` of them."""
        ids, page = [], 1
        while len(ids) < target and page <= 500:  # TMDB caps discover at 500 pages
            data = self.get("/discover/movie", sort_by="popularity.desc",
                            include_adult="false", page=page,
                            **{"vote_count.gte": MIN_VOTE_COUNT})
            results = data.get("results", [])
            if not results:
                break
            ids.extend(m["id"] for m in results)
            page += 1
        # Popularity ordering can shift between pages → same id on two pages.
        # Dedupe preserving first-seen order so we don't fetch details twice.
        return list(dict.fromkeys(ids))[:target]

    def movie_details(self, movie_id: int) -> dict:
        return self.get(f"/movie/{movie_id}")


def to_row(d: dict, batch_id: str, loaded_at: datetime) -> dict:
    """Map a TMDB movie-details payload to a Bronze row (raw JSON kept as strings)."""
    return {
        "tmdb_id": d["id"],
        "imdb_id": d.get("imdb_id"),
        "title": d.get("title"),
        "original_title": d.get("original_title"),
        "release_date": d.get("release_date") or None,
        "genres": json.dumps(d.get("genres", [])),
        "budget": d.get("budget"),
        "revenue": d.get("revenue"),
        "runtime": d.get("runtime"),
        "vote_average": d.get("vote_average"),
        "vote_count": d.get("vote_count"),
        "popularity": d.get("popularity"),
        "status": d.get("status"),
        "original_language": d.get("original_language"),
        "production_companies": json.dumps(d.get("production_companies", [])),
        "belongs_to_collection": json.dumps(d.get("belongs_to_collection")),
        "overview": d.get("overview"),
        "_loaded_at": loaded_at,
        "_batch_id": batch_id,
    }


def load_to_duckdb(rows: list[dict]) -> int:
    """Create the Bronze table if needed and upsert rows by tmdb_id."""
    df = pd.DataFrame(rows, columns=COLUMNS)
    conn = get_connection()
    conn.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bronze.raw_tmdb_movies (
            tmdb_id BIGINT, imdb_id VARCHAR, title VARCHAR, original_title VARCHAR,
            release_date VARCHAR, genres VARCHAR, budget BIGINT, revenue BIGINT,
            runtime INTEGER, vote_average DOUBLE, vote_count INTEGER,
            popularity DOUBLE, status VARCHAR, original_language VARCHAR,
            production_companies VARCHAR, belongs_to_collection VARCHAR,
            overview VARCHAR, _loaded_at TIMESTAMP, _batch_id VARCHAR
        )
    """)
    conn.register("new_movies", df)
    conn.execute("DELETE FROM bronze.raw_tmdb_movies WHERE tmdb_id IN "
                 "(SELECT tmdb_id FROM new_movies)")
    conn.execute(f"INSERT INTO bronze.raw_tmdb_movies SELECT {', '.join(COLUMNS)} "
                 "FROM new_movies")
    total = conn.execute("SELECT COUNT(*) FROM bronze.raw_tmdb_movies").fetchone()[0]
    conn.close()
    return total


def main() -> None:
    target = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TARGET
    client = TMDBClient()
    batch_id = uuid.uuid4().hex[:12]
    loaded_at = datetime.now(timezone.utc)

    print(f"discovering up to {target} movie IDs...")
    ids = client.discover_ids(target)
    print(f"got {len(ids)} IDs — fetching full details...")

    rows = []
    for i, movie_id in enumerate(ids, 1):
        try:
            rows.append(to_row(client.movie_details(movie_id), batch_id, loaded_at))
        except Exception as e:
            print(f"  warn: skipped id {movie_id}: {e}")
        if i % 50 == 0:
            print(f"  {i}/{len(ids)}")

    total = load_to_duckdb(rows)
    print(f"\ndone — loaded {len(rows)} movies (batch {batch_id}); "
          f"bronze.raw_tmdb_movies now holds {total} rows")


if __name__ == "__main__":
    main()

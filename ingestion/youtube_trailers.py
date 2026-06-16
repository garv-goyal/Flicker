"""YouTube → Bronze. Finds each film's trailer and records its engagement
(views/likes/comments) as a hype signal.

YouTube Data API gives 10,000 quota units/day; a search costs 100 units, so we
can only search ~100 films/day. We cover the most popular films and cap the run.

Usage:
    python ingestion/youtube_trailers.py            # default cap
    python ingestion/youtube_trailers.py 50
"""
import os
import sys
from datetime import datetime, timezone, date

import pandas as pd
import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dashboard.utils.duckdb_conn import get_connection

load_dotenv()

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
DEFAULT_CAP = 90             # ~100 search-units/day budget → stay under
REQUEST_TIMEOUT = 15

COLUMNS = [
    "tmdb_id", "youtube_video_id", "video_title", "view_count", "like_count",
    "comment_count", "published_at", "snapshot_at", "days_before_release", "_loaded_at",
]


def targets(cap: int):
    """(tmdb_id, title, release_year, release_date) for popular, not-yet-fetched films."""
    conn = get_connection()
    conn.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    existing = {
        r[0] for r in conn.execute(
            "select tmdb_id from bronze.raw_youtube_trailer_stats"
        ).fetchall()
    } if conn.execute(
        "select count(*) from information_schema.tables "
        "where table_schema='bronze' and table_name='raw_youtube_trailer_stats'"
    ).fetchone()[0] else set()
    rows = conn.execute("""
        select tmdb_id, title, left(release_date, 4) as yr, release_date
        from bronze.raw_tmdb_movies
        where release_date is not null
        order by popularity desc
    """).fetchall()
    conn.close()
    return [r for r in rows if r[0] not in existing][:cap]


def search_trailer(session, key, title, year):
    r = session.get(SEARCH_URL, params={
        "key": key, "q": f"{title} {year} official trailer",
        "part": "snippet", "type": "video", "maxResults": 1, "order": "relevance",
    }, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    items = r.json().get("items", [])
    if not items:
        return None
    it = items[0]
    return {
        "video_id": it["id"]["videoId"],
        "video_title": it["snippet"]["title"],
        "published_at": it["snippet"]["publishedAt"],
    }


def video_stats(session, key, video_id):
    r = session.get(VIDEOS_URL, params={
        "key": key, "id": video_id, "part": "statistics",
    }, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    items = r.json().get("items", [])
    return items[0]["statistics"] if items else {}


def days_before(release_date_str, published_at_str):
    try:
        rel = date.fromisoformat(release_date_str)
        pub = datetime.fromisoformat(published_at_str.replace("Z", "+00:00")).date()
        return (rel - pub).days
    except Exception:
        return None


def main() -> None:
    cap = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CAP
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        raise SystemExit("YOUTUBE_API_KEY not set in .env")

    todo = targets(cap)
    print(f"fetching trailers for {len(todo)} films via YouTube...")
    session = requests.Session()
    now = datetime.now(timezone.utc)
    rows, misses = [], 0

    for i, (tmdb_id, title, year, release_date) in enumerate(todo, 1):
        try:
            hit = search_trailer(session, key, title, year)
            if not hit:
                misses += 1
                continue
            stats = video_stats(session, key, hit["video_id"])
            rows.append({
                "tmdb_id": tmdb_id,
                "youtube_video_id": hit["video_id"],
                "video_title": hit["video_title"],
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
                "published_at": hit["published_at"],
                "snapshot_at": now,
                "days_before_release": days_before(release_date, hit["published_at"]),
                "_loaded_at": now,
            })
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 403:
                print(f"  stopped at {i}: quota likely exhausted ({e})")
                break
            print(f"  warn: {title}: {e}")
        if i % 25 == 0:
            print(f"  {i}/{len(todo)}")

    df = pd.DataFrame(rows, columns=COLUMNS)
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bronze.raw_youtube_trailer_stats (
            tmdb_id BIGINT, youtube_video_id VARCHAR, video_title VARCHAR,
            view_count BIGINT, like_count BIGINT, comment_count BIGINT,
            published_at VARCHAR, snapshot_at TIMESTAMP,
            days_before_release INTEGER, _loaded_at TIMESTAMP
        )
    """)
    conn.register("new_yt", df)
    conn.execute("DELETE FROM bronze.raw_youtube_trailer_stats WHERE tmdb_id IN "
                 "(SELECT tmdb_id FROM new_yt)")
    conn.execute(f"INSERT INTO bronze.raw_youtube_trailer_stats SELECT {', '.join(COLUMNS)} "
                 "FROM new_yt")
    total = conn.execute("SELECT COUNT(*) FROM bronze.raw_youtube_trailer_stats").fetchone()[0]
    conn.close()
    print(f"\ndone — fetched {len(rows)} trailers ({misses} not found); "
          f"bronze.raw_youtube_trailer_stats now holds {total} rows")


if __name__ == "__main__":
    main()

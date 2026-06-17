"""YouTube comments → Kafka. Polls the comment threads on each tracked film's
trailer and publishes every comment as a buzz event to `flicker.buzz_events`.

Why this source: trailer comments are real audience discussion, and each comment
belongs to a known trailer → a known film, so the film mapping is EXACT (no
entity resolution against free text). A polling producer feeding Kafka is a
standard streaming-ingestion pattern.

Quota: commentThreads.list costs 1 unit/call (vs 100 for search), and the daily
budget is 10,000 — so one page (~100 comments) per trailer is ~85 units total.
Comment ids are used as event ids, so re-polling is idempotent (Silver dedupes).

Usage:
    python streaming/youtube_comments_producer.py                 # 1 page / trailer
    python streaming/youtube_comments_producer.py --pages 2 --max-videos 40
"""
import argparse
import os
import sys
import time

import requests
from dotenv import load_dotenv
from kafka import KafkaProducer
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_conn import get_connection

load_dotenv()

COMMENTS_URL = "https://www.googleapis.com/youtube/v3/commentThreads"
BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
TOPIC = "flicker.buzz_events"


def load_trailers(limit):
    """(tmdb_id, film_title, youtube_video_id) for tracked trailers."""
    conn = get_connection(read_only=True)
    rows = conn.execute(f"""
        select y.tmdb_id, m.title, y.youtube_video_id
        from bronze.raw_youtube_trailer_stats y
        join silver.stg_movies m on m.movie_id = y.tmdb_id
        order by y.view_count desc
        limit {limit}
    """).fetchall()
    conn.close()
    return rows


def fetch_comments(session, key, video_id, pages):
    """Yield top-level comments for a video, up to `pages` pages of 100."""
    page_token = None
    for _ in range(pages):
        params = {"key": key, "part": "snippet", "videoId": video_id,
                  "maxResults": 100, "order": "relevance", "textFormat": "plainText"}
        if page_token:
            params["pageToken"] = page_token
        r = session.get(COMMENTS_URL, params=params, timeout=15)
        if r.status_code == 403:      # comments disabled / not available
            return
        r.raise_for_status()
        data = r.json()
        for item in data.get("items", []):
            top = item["snippet"]["topLevelComment"]
            s = top["snippet"]
            yield {
                "comment_id": top["id"],
                "text": s.get("textDisplay", "")[:500],
                "author": s.get("authorDisplayName"),
                "published_at": s.get("publishedAt"),
                "likes": s.get("likeCount", 0),
            }
        page_token = data.get("nextPageToken")
        if not page_token:
            return


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=1, help="comment pages per trailer (100 each)")
    ap.add_argument("--max-videos", type=int, default=200, help="max trailers to poll")
    args = ap.parse_args()

    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        raise SystemExit("YOUTUBE_API_KEY not set in .env")

    trailers = load_trailers(args.max_videos)
    print(f"polling comments for {len(trailers)} trailers ({args.pages} page(s) each)...")
    session = requests.Session()
    producer = KafkaProducer(
        bootstrap_servers=BROKER,
        key_serializer=lambda k: str(k).encode(),
        value_serializer=lambda v: json.dumps(v).encode(),
    )
    total = calls = skipped = 0

    for tmdb_id, title, video_id in trailers:
        before = total
        try:
            for c in fetch_comments(session, key, video_id, args.pages):
                producer.send(TOPIC, key=tmdb_id, value={
                    "source": "youtube",
                    "event_id": c["comment_id"],
                    "tmdb_id": tmdb_id,
                    "title": title,
                    "page": video_id,
                    "text": c["text"],
                    "author": c["author"],
                    "event_time": c["published_at"],
                })
                total += 1
        except requests.HTTPError as e:
            print(f"  warn: {title}: {e}")
        calls += args.pages
        if total == before:
            skipped += 1
        else:
            print(f"  {title}: +{total - before} comments")
        time.sleep(0.05)

    producer.flush()
    producer.close()
    print(f"\ndone — produced {total} comment buzz events from {len(trailers)} trailers "
          f"({skipped} had no/disabled comments); ~{calls} quota units used")


if __name__ == "__main__":
    main()

"""Wikipedia → Kafka. Streams the live Wikimedia EventStreams feed (every edit to
every Wikipedia page, no auth) and publishes a buzz event whenever a *film* page
for one of our tracked titles is edited.

Why this source: film pages use a canonical, disambiguated title — e.g.
"Oppenheimer (film)", "Dune (2021 film)" — so matching against our catalog is an
EXACT key join, not free-text guessing. That eliminates the entity-resolution
noise inherent in scanning social posts, while still being a genuine real-time
stream through Kafka. Edits are an "editorial attention" proxy for buzz.

Usage:
    python streaming/wikipedia_producer.py              # until Ctrl-C
    python streaming/wikipedia_producer.py --seconds 90 # stop after 90s (testing)
"""
import argparse
import json
import os
import re
import sys
import time

import requests

from kafka import KafkaProducer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dashboard.utils.duckdb_conn import get_connection

STREAM = "https://stream.wikimedia.org/v2/stream/recentchange"
BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
TOPIC = "flicker.buzz_events"
# page titles like "Title (film)" / "Title (2021 film)" / "Title (2008 American film)"
FILM_PAGE = re.compile(r"^(.*?) \(([^)]*\bfilm\b[^)]*)\)$", re.IGNORECASE)


def load_titles():
    """{lowercased title: (tmdb_id, original title)} for the whole catalog."""
    conn = get_connection(read_only=True)
    rows = conn.execute("select title, movie_id from silver.stg_movies").fetchall()
    conn.close()
    return {t.lower(): (mid, t) for t, mid in rows}


def run(seconds: int | None):
    titles = load_titles()
    print(f"watching Wikipedia edits for {len(titles)} film pages...")
    producer = KafkaProducer(
        bootstrap_servers=BROKER,
        key_serializer=lambda k: str(k).encode(),
        value_serializer=lambda v: json.dumps(v).encode(),
    )
    deadline = time.time() + seconds if seconds else None
    seen = matched = 0

    # EventStreams is a long-lived SSE connection that can drop; reconnect until
    # the deadline (or forever). A production consumer would also resume from
    # Last-Event-ID; for a buzz feed, simple reconnection is sufficient.
    while not deadline or time.time() < deadline:
        try:
            resp = requests.get(STREAM, stream=True, timeout=(10, 90),
                                headers={"User-Agent": "flicker-portfolio/1.0"})
            for line in resp.iter_lines():
                if deadline and time.time() > deadline:
                    break
                if not line or not line.startswith(b"data: "):
                    continue
                try:
                    ev = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue
                if ev.get("wiki") != "enwiki" or ev.get("type") not in ("edit", "new"):
                    continue
                seen += 1
                m = FILM_PAGE.match(ev.get("title", ""))
                if not m or m.group(1).lower() not in titles:
                    continue
                tmdb_id, title = titles[m.group(1).lower()]
                producer.send(TOPIC, key=tmdb_id, value={
                    "source": "wikipedia",
                    "tmdb_id": tmdb_id,
                    "title": title,
                    "page": ev.get("title"),
                    "text": ev.get("comment") or "",      # the edit summary
                    "author": ev.get("user"),
                    "event_time": ev.get("meta", {}).get("dt") or ev.get("timestamp"),
                })
                matched += 1
                print(f"  buzz #{matched}: {ev.get('title')}  (edit by {ev.get('user')})")
            resp.close()
        except (requests.exceptions.ChunkedEncodingError,
                requests.exceptions.ConnectionError,
                requests.exceptions.ReadTimeout) as e:
            print(f"  stream dropped ({type(e).__name__}); reconnecting...")
            time.sleep(2)

    producer.flush()
    producer.close()
    print(f"\ndone — produced {matched} buzz events from {seen} enwiki edits scanned")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=None)
    args = ap.parse_args()
    try:
        run(args.seconds)
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()

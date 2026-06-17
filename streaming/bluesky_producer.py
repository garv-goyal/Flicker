"""Bluesky → Kafka. Connects to the public Bluesky Jetstream firehose (no auth),
filters posts that mention one of our tracked films, and publishes a buzz event
per match to the Kafka topic `flicker.social_buzz`.

Bluesky replaces the originally-planned Reddit source: as of 2026 Reddit closed
self-service API access (Responsible Builder Policy), whereas the AT Protocol
firehose is open to anyone without credentials — and a true real-time stream.

Usage:
    python streaming/bluesky_producer.py              # run until stopped (Ctrl-C)
    python streaming/bluesky_producer.py --seconds 90 # stop after 90s (for testing)
"""
import argparse
import asyncio
import json
import os
import re
import sys
import time

import websockets
from kafka import KafkaProducer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_conn import get_connection

JETSTREAM = ("wss://jetstream2.us-east.bsky.network/subscribe"
             "?wantedCollections=app.bsky.feed.post")
BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
TOPIC = "flicker.buzz_events"
TITLE_LIMIT = 500          # most-popular titles to watch
MIN_TITLE_LEN = 5

# Film titles are often everyday words/phrases ("Get Out", "After", "Normal"),
# so a post only counts as buzz if it ALSO contains an unambiguous film-context
# word. This trades recall for precision — the right call for a buzz metric.
# (Ambiguous words like bare "watch"/"cast"/"director" are deliberately excluded.)
FILM_KEYWORDS = re.compile(
    r"\b(movie|movies|film|films|cinema|theater|theatre|trailer|sequel|prequel|"
    r"premiere|screening|box ?office|rewatch|rewatched|rewatching|watched|"
    r"watching|streaming|oscar|oscars|filmmaker)\b",
    re.IGNORECASE)

_NEVER = re.compile(r"(?!x)x")   # matches nothing (placeholder for empty tiers)

# Common English words. A title is only watchable if it contains a token that
# ISN'T one of these — i.e. a distinctive anchor (a proper noun or coined word).
# This drops titles that are just everyday words/phrases ("Arrival", "Get Out",
# "Normal", "After"), which are hopeless to match precisely against social text.
COMMON_WORDS = set("""
the a an of to in on for and or but with from by at as is are was were be been
this that these those it its her his him she he they them we us you your my our
out up off over under after before about into onto down away back then than too
get got go going gone come comes came make made made take took get out time day
days night love life man woman men women girl boy kid home house world year years
new old big small good bad best worst real true free last first next one two three
normal wonder arrival closer shining inside about wicked frozen happy sorry only
just like dont cant wont not no yes now here there what when where why how who
michael obsession obsessed redeeming fault story stories thing things people
rock rocks conjuring samurai seven eight nine ten hundred
""".split())


def is_distinctive(title: str) -> bool:
    tokens = re.findall(r"[a-z0-9]+", title.lower())
    return any(len(t) >= 4 and t not in COMMON_WORDS for t in tokens)


def _pattern(titles):
    if not titles:
        return _NEVER
    alts = sorted((re.escape(t) for t in titles), key=len, reverse=True)
    return re.compile(r"\b(" + "|".join(alts) + r")\b", re.IGNORECASE)


def load_title_matcher():
    """Return (multiword_regex, singleword_regex, lookup). Multi-word titles match
    on their own; single-word titles must be paired with a film-context keyword."""
    conn = get_connection(read_only=True)
    rows = conn.execute(f"""
        select title, movie_id
        from silver.stg_movies
        where length(title) >= {MIN_TITLE_LEN}
        order by popularity_score desc
        limit {TITLE_LIMIT}
    """).fetchall()
    conn.close()
    # keep only distinctive titles (drop everyday-word titles → far less noise)
    lookup = {t.lower(): (mid, t) for t, mid in rows if is_distinctive(t)}
    multi = [t for t in lookup if " " in t]
    single = [t for t in lookup if " " not in t]
    return _pattern(multi), _pattern(single), lookup


def match_title(text, multi_re, single_re, lookup):
    """Return (tmdb_id, title) only when the post mentions a distinctive tracked
    title AND uses film-context language. Highest-precision config: rule-based
    matching of titles in free social text is inherently noisy, so we favour
    precision (few, clean signals) over recall (more, noisier ones)."""
    if not FILM_KEYWORDS.search(text):
        return None
    hit = multi_re.search(text) or single_re.search(text)
    return lookup[hit.group(1).lower()] if hit else None


async def run(seconds: int | None):
    multi_re, single_re, lookup = load_title_matcher()
    print(f"watching for {len(lookup)} film titles on the Bluesky firehose...")
    producer = KafkaProducer(
        bootstrap_servers=BROKER,
        key_serializer=lambda k: str(k).encode(),
        value_serializer=lambda v: json.dumps(v).encode(),
    )
    deadline = time.time() + seconds if seconds else None
    seen = matched = 0

    async with websockets.connect(JETSTREAM, max_size=None) as ws:
        async for raw in ws:
            if deadline and time.time() > deadline:
                break
            msg = json.loads(raw)
            commit = msg.get("commit") or {}
            if (msg.get("kind") != "commit" or commit.get("operation") != "create"
                    or commit.get("collection") != "app.bsky.feed.post"):
                continue
            seen += 1
            record = commit.get("record") or {}
            text = record.get("text", "")
            langs = record.get("langs")
            if not text or (langs and "en" not in langs):  # English posts only
                continue
            match = match_title(text, multi_re, single_re, lookup)
            if not match:
                continue
            tmdb_id, title = match
            event = {
                "source": "bluesky",
                "tmdb_id": tmdb_id,
                "title": title,
                "page": None,
                "text": text[:280],
                "author": msg.get("did"),
                "event_time": record.get("createdAt"),
            }
            producer.send(TOPIC, key=tmdb_id, value=event)
            matched += 1
            if matched % 10 == 0:
                print(f"  matched {matched} (scanned {seen} posts) — last: {title}")

    producer.flush()
    producer.close()
    print(f"\ndone — produced {matched} buzz events from {seen} posts scanned")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=None,
                    help="stop after N seconds (default: run until Ctrl-C)")
    args = ap.parse_args()
    try:
        asyncio.run(run(args.seconds))
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()

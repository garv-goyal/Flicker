"""Kafka → Bronze. Consumes buzz events from `flicker.buzz_events` and lands them
in DuckDB at bronze.raw_buzz_events, batching writes (DuckDB is single-writer, so
the consumer is the sole writer to this table).

Uses confluent-kafka (librdkafka) — the production-standard client. kafka-python's
consumer couldn't fetch from the Kafka 3.9 broker (protocol mismatch), so the
consumer runs on confluent-kafka while producers stay on kafka-python.

Source-neutral: works for any producer emitting the common buzz event shape
(source, tmdb_id, title, page, text, author, event_time, optional event_id).

Usage:
    python streaming/bluesky_consumer.py            # run until stopped (Ctrl-C)
    python streaming/bluesky_consumer.py --drain     # stop after 15s idle (testing)
"""
import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone

import pandas as pd
from confluent_kafka import Consumer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dashboard.utils.duckdb_conn import get_connection

BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
TOPIC = "flicker.buzz_events"
BATCH = 100
IDLE_STOP = 15          # --drain: stop after this many idle seconds

COLUMNS = ["event_id", "source", "tmdb_id", "title", "page", "text", "author",
           "event_time", "ingested_at", "kafka_partition", "kafka_offset"]


def ensure_table(conn):
    conn.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bronze.raw_buzz_events (
            event_id VARCHAR, source VARCHAR, tmdb_id BIGINT, title VARCHAR,
            page VARCHAR, text VARCHAR, author VARCHAR, event_time VARCHAR,
            ingested_at TIMESTAMP, kafka_partition INTEGER, kafka_offset BIGINT
        )
    """)


def flush(conn, buffer):
    if not buffer:
        return 0
    df = pd.DataFrame(buffer, columns=COLUMNS)
    conn.register("new_buzz", df)
    conn.execute(f"INSERT INTO bronze.raw_buzz_events SELECT {', '.join(COLUMNS)} FROM new_buzz")
    conn.unregister("new_buzz")
    n = len(buffer)
    buffer.clear()
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drain", action="store_true",
                    help="stop after 15s with no new messages (for testing)")
    args = ap.parse_args()

    consumer = Consumer({
        "bootstrap.servers": BROKER,
        "group.id": "flicker-buzz-consumer",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
    })
    consumer.subscribe([TOPIC])
    conn = get_connection()
    ensure_table(conn)
    print(f"consuming {TOPIC} from {BROKER}...")

    buffer, total, idle_since = [], 0, time.time()
    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                if buffer:
                    total += flush(conn, buffer)
                    print(f"  wrote {total} events to bronze.raw_buzz_events")
                if args.drain and time.time() - idle_since > IDLE_STOP:
                    break
                continue
            if msg.error():
                continue
            idle_since = time.time()
            v = json.loads(msg.value().decode())
            buffer.append({
                "event_id": v.get("event_id") or uuid.uuid4().hex[:16],
                "source": v.get("source"),
                "tmdb_id": v.get("tmdb_id"),
                "title": v.get("title"),
                "page": v.get("page"),
                "text": v.get("text"),
                "author": v.get("author"),
                "event_time": v.get("event_time"),
                "ingested_at": datetime.now(timezone.utc),
                "kafka_partition": msg.partition(),
                "kafka_offset": msg.offset(),
            })
            if len(buffer) >= BATCH:
                total += flush(conn, buffer)
                print(f"  wrote {total} events to bronze.raw_buzz_events")
    finally:
        total += flush(conn, buffer)
        consumer.close()
        grand = conn.execute("SELECT COUNT(*) FROM bronze.raw_buzz_events").fetchone()[0]
        conn.close()
        print(f"\ndone — wrote {total} this run; bronze.raw_buzz_events holds {grand} rows")


if __name__ == "__main__":
    main()

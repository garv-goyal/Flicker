"""Phase 5 / CDC — Kafka → Bronze. Consumes Debezium change events from
`flicker_cdc.public.film_lifecycle` and lands them in bronze.raw_cdc_film_lifecycle.

Each Debezium envelope is flattened into one row capturing the operation
(c/u/d/r → insert/update/delete/snapshot) plus the full before- and after-images,
so the warehouse can reconstruct both the current state and the change history.
Uses confluent-kafka (librdkafka), the same client as the buzz consumer.

Usage:
    python streaming/cdc/cdc_consumer.py            # run until Ctrl-C
    python streaming/cdc/cdc_consumer.py --drain     # stop after 15s idle (testing)
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import pandas as pd
from confluent_kafka import Consumer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from dashboard.utils.duckdb_conn import get_connection

BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
TOPIC = "flicker_cdc.public.film_lifecycle"
BATCH = 50
IDLE_STOP = 15

OP_LABEL = {"c": "insert", "u": "update", "d": "delete", "r": "snapshot"}

COLUMNS = ["change_id", "op", "op_label", "tmdb_id", "title",
           "after_status", "after_popularity", "after_vote_count", "after_vote_avg",
           "before_status", "before_popularity", "before_vote_count", "before_vote_avg",
           "source_ts", "lsn", "ingested_at", "kafka_partition", "kafka_offset"]


def ensure_table(conn):
    conn.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bronze.raw_cdc_film_lifecycle (
            change_id        VARCHAR,
            op               VARCHAR,
            op_label         VARCHAR,
            tmdb_id          BIGINT,
            title            VARCHAR,
            after_status     VARCHAR,
            after_popularity DOUBLE,
            after_vote_count BIGINT,
            after_vote_avg   DOUBLE,
            before_status    VARCHAR,
            before_popularity DOUBLE,
            before_vote_count BIGINT,
            before_vote_avg  DOUBLE,
            source_ts        TIMESTAMP,
            lsn              BIGINT,
            ingested_at      TIMESTAMP,
            kafka_partition  INTEGER,
            kafka_offset     BIGINT
        )
    """)


def flatten(msg):
    v = json.loads(msg.value())
    after, before, source = v.get("after"), v.get("before"), v.get("source", {})
    row = after or before or {}
    ts_ms = v.get("ts_ms")
    source_ts = (datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc) if ts_ms else None)
    return {
        "change_id": f"{msg.partition()}-{msg.offset()}",
        "op": v.get("op"),
        "op_label": OP_LABEL.get(v.get("op"), v.get("op")),
        "tmdb_id": row.get("tmdb_id"),
        "title": row.get("title"),
        "after_status": (after or {}).get("status"),
        "after_popularity": (after or {}).get("popularity"),
        "after_vote_count": (after or {}).get("vote_count"),
        "after_vote_avg": (after or {}).get("vote_average"),
        "before_status": (before or {}).get("status"),
        "before_popularity": (before or {}).get("popularity"),
        "before_vote_count": (before or {}).get("vote_count"),
        "before_vote_avg": (before or {}).get("vote_average"),
        "source_ts": source_ts,
        "lsn": source.get("lsn"),
        "ingested_at": datetime.now(timezone.utc),
        "kafka_partition": msg.partition(),
        "kafka_offset": msg.offset(),
    }


def flush(conn, rows):
    if not rows:
        return 0
    df = pd.DataFrame(rows, columns=COLUMNS)
    conn.register("cdc_batch", df)
    conn.execute("INSERT INTO bronze.raw_cdc_film_lifecycle SELECT * FROM cdc_batch")
    conn.unregister("cdc_batch")
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drain", action="store_true", help="stop after 15s with no new events")
    args = ap.parse_args()

    conn = get_connection(read_only=False)
    ensure_table(conn)
    consumer = Consumer({"bootstrap.servers": BROKER, "group.id": "flicker-cdc-consumer",
                         "auto.offset.reset": "earliest", "enable.auto.commit": True})
    consumer.subscribe([TOPIC])
    print(f"Consuming {TOPIC} from {BROKER} … (Ctrl-C to stop)")

    rows, total, last = [], 0, time.time()
    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                if rows:
                    total += flush(conn, rows); rows = []
                if args.drain and time.time() - last > IDLE_STOP:
                    print(f"Idle {IDLE_STOP}s — draining done."); break
                continue
            if msg.error():
                continue
            if msg.value() is None:
                continue  # Debezium tombstone (post-delete marker) — skip
            rows.append(flatten(msg)); last = time.time()
            if len(rows) >= BATCH:
                total += flush(conn, rows); rows = []
                print(f"  …landed {total} change events")
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        total += flush(conn, rows)
        consumer.close()
        conn.close()
        print(f"Total change events landed this run: {total}")


if __name__ == "__main__":
    main()

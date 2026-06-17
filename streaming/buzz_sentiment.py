"""Buzz enrichment: score the sentiment of each streamed trailer comment.

Reads un-scored comments from bronze.raw_buzz_events, runs VADER (a rule-based
sentiment model built for short social text — it understands emoji, slang, caps
and punctuation), and lands one row per comment in bronze.raw_buzz_sentiment.

This turns raw comment text into a metric: a compound score in [-1, 1] and a
positive/neutral/negative label. dbt then aggregates it per film so the web app
can compare *audience enthusiasm* against *critic scores* — the buzz stream stops
being a wall of text and becomes a signal tied to outcomes.

Idempotent: only comments whose event_id is not already scored get processed, so
it is safe to re-run after each consume. VADER runs locally — no API, no cost.

Usage:
    python streaming/buzz_sentiment.py            # score everything new
    python streaming/buzz_sentiment.py --rescore  # wipe and re-score all
"""
import argparse
import os
import sys
from datetime import datetime, timezone

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_conn import get_connection

# VADER's conventional thresholds for labelling a compound score.
POS_CUTOFF = 0.05
NEG_CUTOFF = -0.05


def label_for(compound: float) -> str:
    if compound >= POS_CUTOFF:
        return "positive"
    if compound <= NEG_CUTOFF:
        return "negative"
    return "neutral"


def ensure_table(conn):
    conn.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bronze.raw_buzz_sentiment (
            event_id   VARCHAR PRIMARY KEY,
            compound   DOUBLE,
            pos        DOUBLE,
            neu        DOUBLE,
            neg        DOUBLE,
            label      VARCHAR,
            scored_at  TIMESTAMP
        )
    """)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rescore", action="store_true",
                    help="drop existing scores and re-score every comment")
    args = ap.parse_args()

    conn = get_connection(read_only=False)
    ensure_table(conn)
    if args.rescore:
        conn.execute("DELETE FROM bronze.raw_buzz_sentiment")

    rows = conn.execute("""
        SELECT e.event_id, e.text
        FROM bronze.raw_buzz_events e
        LEFT JOIN bronze.raw_buzz_sentiment s USING (event_id)
        WHERE s.event_id IS NULL AND e.text IS NOT NULL
    """).fetchall()

    if not rows:
        print("Nothing to score — all comments already have sentiment.")
        conn.close()
        return

    analyzer = SentimentIntensityAnalyzer()
    now = datetime.now(timezone.utc)
    scored = []
    for event_id, text in rows:
        s = analyzer.polarity_scores(text)
        scored.append((event_id, s["compound"], s["pos"], s["neu"], s["neg"],
                       label_for(s["compound"]), now))

    df = pd.DataFrame(scored, columns=["event_id", "compound", "pos", "neu",
                                       "neg", "label", "scored_at"])
    conn.register("new_scores", df)
    conn.execute("INSERT INTO bronze.raw_buzz_sentiment SELECT * FROM new_scores")
    conn.unregister("new_scores")

    dist = conn.execute("""
        SELECT label, count(*) FROM bronze.raw_buzz_sentiment GROUP BY 1 ORDER BY 2 DESC
    """).fetchall()
    total = conn.execute("SELECT count(*) FROM bronze.raw_buzz_sentiment").fetchone()[0]
    conn.close()

    print(f"Scored {len(scored):,} new comments ({total:,} total).")
    for lbl, n in dist:
        print(f"  {lbl:<9} {n:>6,}  ({100*n/total:.1f}%)")


if __name__ == "__main__":
    main()

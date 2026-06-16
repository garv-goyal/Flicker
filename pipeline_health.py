"""Pipeline health check. Verifies each warehouse layer has data and reports row
counts and Bronze freshness. Exits non-zero if any layer is empty (so Airflow
marks the task failed). Usable locally too:  python pipeline_health.py
"""
import sys
from dashboard.utils.duckdb_conn import get_connection

CHECKS = [
    ("bronze.raw_tmdb_movies", "bronze"),
    ("silver.stg_movies", "silver"),
    ("gold.fact_title_performance", "gold"),
    ("gold.mart_hype_vs_revenue", "gold"),
]


def main() -> int:
    conn = get_connection(read_only=True)
    ok = True
    for table, layer in CHECKS:
        try:
            n = conn.execute(f"select count(*) from {table}").fetchone()[0]
        except Exception as e:
            print(f"FAIL  {table}: {e}")
            ok = False
            continue
        flag = "ok  " if n > 0 else "EMPTY"
        print(f"{flag}  {table:38} {n:>6} rows")
        ok = ok and n > 0

    fresh = conn.execute(
        "select max(_loaded_at) from bronze.raw_tmdb_movies"
    ).fetchone()[0]
    print(f"      bronze last loaded: {fresh}")
    conn.close()
    print("\nhealthy" if ok else "\nUNHEALTHY — see above")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

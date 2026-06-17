"""One-time warehouse setup. Creates the local flicker.duckdb file and the three
Medallion schemas. Run:  python warehouse/setup_duckdb.py

DuckDB uses one file with multiple schemas (vs Snowflake's separate databases):
  bronze.*  silver.*  gold.*
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_conn import get_connection, DEFAULT_DB_PATH


def main() -> None:
    conn = get_connection()
    for schema in ("bronze", "silver", "gold"):
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    schemas = conn.execute(
        "SELECT schema_name FROM information_schema.schemata "
        "WHERE schema_name IN ('bronze','silver','gold') ORDER BY schema_name"
    ).fetchall()
    conn.close()
    print(f"ok    warehouse ready at {DEFAULT_DB_PATH}")
    print(f"ok    schemas: {', '.join(s[0] for s in schemas)}")


if __name__ == "__main__":
    main()

"""Phase 0 verifier. Run after `python warehouse/setup_duckdb.py`:
    python verify_setup.py
Confirms the DuckDB warehouse opens and the bronze/silver/gold schemas exist."""
import sys
from db_conn import get_connection


def main() -> int:
    try:
        conn = get_connection()
    except Exception as e:
        print(f"FAIL  could not open DuckDB warehouse: {e}")
        return 1

    version = conn.execute("PRAGMA version").fetchone()[0]
    print(f"ok    DuckDB warehouse open — engine {version}")

    found = {row[0] for row in conn.execute(
        "SELECT schema_name FROM information_schema.schemata"
    ).fetchall()}
    conn.close()

    needed = {"bronze", "silver", "gold"}
    for s in sorted(needed):
        print(f"ok    schema {s} exists" if s in found
              else f"MISSING schema {s} — run: python warehouse/setup_duckdb.py")
    return 0 if needed <= found else 1


if __name__ == "__main__":
    sys.exit(main())

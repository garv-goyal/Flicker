"""Shared DuckDB connection helper.

Local-first: by default opens the local `flicker.duckdb` file (no account, no card).
Set FLICKER_USE_MOTHERDUCK=true (and MOTHERDUCK_TOKEN) to point at the free MotherDuck
cloud database instead — same SQL, used to serve the live web app.
"""
import os
import duckdb
from dotenv import load_dotenv

load_dotenv()

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flicker.duckdb")


def _open(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    use_md = os.getenv("FLICKER_USE_MOTHERDUCK", "false").lower() == "true"
    if use_md:
        token = os.environ["MOTHERDUCK_TOKEN"]
        db_name = os.getenv("MOTHERDUCK_DATABASE", "flicker")
        return duckdb.connect(f"md:{db_name}?motherduck_token={token}")
    return duckdb.connect(os.getenv("FLICKER_DB_PATH", DEFAULT_DB_PATH), read_only=read_only)


def get_connection(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Open a fresh DuckDB/MotherDuck connection."""
    return _open(read_only=read_only)

"""Shared DuckDB connection helper.

Local-first: by default opens the local `flicker.duckdb` file (no account, no card).
Set FLICKER_USE_MOTHERDUCK=true (and MOTHERDUCK_TOKEN) to point at the free MotherDuck
cloud database instead — same SQL, used to serve the live Streamlit dashboard.
"""
import os
import duckdb
from dotenv import load_dotenv

load_dotenv()

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DB_PATH = os.path.join(_PROJECT_ROOT, "flicker.duckdb")


def _open(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    use_md = os.getenv("FLICKER_USE_MOTHERDUCK", "false").lower() == "true"
    if use_md:
        token = os.environ["MOTHERDUCK_TOKEN"]
        db_name = os.getenv("MOTHERDUCK_DATABASE", "flicker")
        return duckdb.connect(f"md:{db_name}?motherduck_token={token}")
    return duckdb.connect(os.getenv("FLICKER_DB_PATH", DEFAULT_DB_PATH), read_only=read_only)


def get_shared_read_conn() -> duckdb.DuckDBPyConnection:
    """One persistent read-only connection per Streamlit process, cached via st.cache_resource.
    Avoids the round-trip cost of authenticating to MotherDuck on every query."""
    try:
        import streamlit as st

        @st.cache_resource(show_spinner=False)
        def _cached():
            return _open(read_only=True)

        return _cached()
    except ImportError:
        return _open(read_only=True)


def get_connection(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Open a fresh connection. Used only for write operations (subscribe, etc.)."""
    return _open(read_only=read_only)

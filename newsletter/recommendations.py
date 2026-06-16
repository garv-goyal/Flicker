"""Query the Gold layer and build this week's newsletter picks.

Scoring for the main pick:
  score = popularity * 0.3 + vote_average * 10 * 0.3 + pct_positive * 0.4
If a film has no audience sentiment data, pct_positive defaults to 50 (neutral).
"""
import os
import sys

import math

import duckdb
from dotenv import load_dotenv

load_dotenv()

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DB_PATH = os.path.join(_PROJECT_ROOT, "flicker.duckdb")


def _conn():
    use_md = os.getenv("FLICKER_USE_MOTHERDUCK", "false").lower() == "true"
    if use_md:
        token = os.environ["MOTHERDUCK_TOKEN"]
        db_name = os.getenv("MOTHERDUCK_DATABASE", "flicker")
        return duckdb.connect(f"md:{db_name}?motherduck_token={token}")
    return duckdb.connect(os.getenv("FLICKER_DB_PATH", _DB_PATH), read_only=True)


def get_picks(genre_pref: str | None = None) -> dict:
    """Return this week's newsletter picks from Gold models.

    genre_pref: if set, the main pick is filtered to that genre first,
                falling back to all genres if nothing qualifies.
    """
    conn = _conn()

    genre_filter = f"AND lc.primary_genre = '{genre_pref}'" if genre_pref else ""

    # ── Main pick: scored composite of popularity + rating + sentiment ────────
    main_pick_sql = f"""
    WITH current_films AS (
        SELECT
            lc.tmdb_id,
            lc.title,
            lc.status,
            lc.popularity,
            lc.vote_count,
            lc.vote_average,
            lc.primary_genre,
            lc.release_year,
            bvc.pct_positive,
            bvc.critic_score,
            bvc.divergence,
            bvc.avg_sentiment,
            -- weighted score; neutral 50 for films without sentiment
            (lc.popularity * 0.3)
              + (lc.vote_average * 10 * 0.3)
              + (COALESCE(bvc.pct_positive, 50) * 0.4) AS score
        FROM gold.mart_film_lifecycle_current lc
        LEFT JOIN gold.mart_buzz_vs_critics bvc ON bvc.tmdb_id = lc.tmdb_id
        WHERE lc.status IN ('Now Playing', 'Holdover')
          AND lc.vote_count >= 100
          {genre_filter}
    )
    SELECT * FROM current_films ORDER BY score DESC LIMIT 1
    """

    main = conn.execute(main_pick_sql).df()

    # Fallback: if genre filter returned nothing, retry without filter
    if main.empty and genre_pref:
        main = conn.execute(main_pick_sql.replace(genre_filter, "")).df()

    # ── Leaving Soon: best-rated film about to leave ──────────────────────────
    leaving_sql = """
    SELECT
        lc.tmdb_id, lc.title, lc.vote_average, lc.popularity,
        lc.primary_genre, lc.vote_count
    FROM gold.mart_film_lifecycle_current lc
    WHERE lc.status = 'Leaving Soon'
      AND lc.vote_count >= 50
    ORDER BY lc.vote_average DESC, lc.popularity DESC
    LIMIT 1
    """
    leaving = conn.execute(leaving_sql).df()

    # ── Critics vs Crowds: biggest divergences from mart_buzz_vs_critics ─────
    # Films where audience is warmer than critics (crowd underrated by critics)
    underrated_sql = """
    SELECT title, primary_genre, pct_positive, critic_score,
           ROUND(divergence, 1) AS divergence
    FROM gold.mart_buzz_vs_critics
    WHERE divergence > 5
    ORDER BY divergence DESC
    LIMIT 1
    """
    underrated = conn.execute(underrated_sql).df()  # crowd loves it, critics cold

    # Films where critics are warmer than audience
    overrated_sql = """
    SELECT title, primary_genre, pct_positive, critic_score,
           ROUND(divergence, 1) AS divergence
    FROM gold.mart_buzz_vs_critics
    WHERE divergence < -5
    ORDER BY divergence ASC
    LIMIT 1
    """
    overrated = conn.execute(overrated_sql).df()  # critics love it, crowd cold

    # ── Runners-up: next 3 top-scored Now Playing films (excluding main pick) ─
    main_id = int(main.iloc[0].tmdb_id) if not main.empty else -1
    runners_sql = f"""
    SELECT
        lc.title,
        lc.vote_average,
        lc.primary_genre,
        lc.status,
        COALESCE(bvc.pct_positive, NULL) AS pct_positive
    FROM gold.mart_film_lifecycle_current lc
    LEFT JOIN gold.mart_buzz_vs_critics bvc ON bvc.tmdb_id = lc.tmdb_id
    WHERE lc.status IN ('Now Playing', 'Holdover')
      AND lc.vote_count >= 100
      AND lc.tmdb_id != {main_id}
    ORDER BY (lc.popularity * 0.3) + (lc.vote_average * 10 * 0.3)
              + (COALESCE(bvc.pct_positive, 50) * 0.4) DESC
    LIMIT 3
    """
    runners = conn.execute(runners_sql).df()

    def _clean(d: dict) -> dict:
        """Replace float NaN with None so templates can safely check `is None`."""
        return {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in d.items()}

    conn.close()
    return {
        "main_pick": _clean(main.iloc[0].to_dict()) if not main.empty else None,
        "leaving_soon": _clean(leaving.iloc[0].to_dict()) if not leaving.empty else None,
        "underrated": _clean(underrated.iloc[0].to_dict()) if not underrated.empty else None,
        "overrated": _clean(overrated.iloc[0].to_dict()) if not overrated.empty else None,
        "runners": [_clean(r) for r in runners.to_dict("records")],
    }


if __name__ == "__main__":
    import json
    genre = sys.argv[1] if len(sys.argv) > 1 else None
    picks = get_picks(genre)
    print(json.dumps(picks, indent=2, default=str))

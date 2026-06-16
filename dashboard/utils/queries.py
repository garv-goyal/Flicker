"""Read-only query helpers for the dashboard. Each opens a fresh read-only DuckDB
connection, returns a DataFrame, and closes — so Streamlit can cache the results
and multiple page loads never contend for a write lock."""
from .duckdb_conn import get_connection


def _df(sql: str):
    conn = get_connection(read_only=True)
    try:
        return conn.execute(sql).df()
    finally:
        conn.close()


def headline_metrics():
    return _df("""
        select
            count(*)                                              as total_films,
            min(release_year)                                     as first_year,
            max(release_year)                                     as last_year,
            count(distinct primary_genre)                         as genres
        from gold.dim_titles
    """)


def roi_summary():
    return _df("""
        select
            round(avg(roi_ratio), 2)                              as avg_roi,
            round(median(roi_ratio), 2)                           as median_roi,
            round(100.0 * count(*) filter (where is_profitable)
                  / nullif(count(*) filter (where roi_ratio is not null), 0), 1) as profitable_pct
        from gold.fact_title_performance
    """)


def roi_by_decade():
    return _df("""
        select release_decade, film_count, avg_roi, median_roi, profitable_pct
        from gold.mart_roi_by_decade
        order by release_decade
    """)


def top_roi_films(limit: int = 10):
    return _df(f"""
        select d.title, d.release_year, d.primary_genre,
               f.budget_usd, f.revenue_usd, f.roi_ratio, f.tmdb_rating
        from gold.fact_title_performance f
        join gold.dim_titles d using (title_key)
        where f.roi_ratio is not null and f.budget_usd >= 1000000
        order by f.roi_ratio desc
        limit {limit}
    """)


# ---- Critical Reception page ------------------------------------------------
def critical_summary():
    return _df("""
        select
            count(*) filter (where composite_score is not null)   as scored,
            round(avg(composite_score), 1)                        as avg_composite,
            count(*) filter (where won_oscar)                     as oscar_winners,
            count(*) filter (where rt_score is not null)          as with_rt
        from gold.fact_title_performance
    """)


def best_reviewed(limit: int = 12):
    return _df(f"""
        select d.title, d.release_year, d.primary_genre,
               f.composite_score, f.rt_score, f.metacritic_score,
               f.imdb_rating, f.won_oscar, f.oscar_wins
        from gold.fact_title_performance f
        join gold.dim_titles d using (title_key)
        where f.composite_score is not null
        order by f.composite_score desc, f.rt_score desc
        limit {limit}
    """)


# Critics (Rotten Tomatoes %) vs audience (TMDB rating ×10). Restricted to films
# with real critical coverage (a Metacritic score exists) and a solid audience
# vote count, so the gap reflects genuine disagreement, not thin-sample noise.
_CVA_FILTER = """
    f.rt_score is not null and f.metacritic_score is not null
    and f.tmdb_rating is not null and f.tmdb_vote_count >= 1000
"""


def audience_over_critics(limit: int = 7):
    """Crowd-pleasers: audiences rated them far above the critics."""
    return _df(f"""
        select d.title, d.release_year, f.rt_score,
               round(f.tmdb_rating * 10) as audience_score,
               round(f.tmdb_rating * 10 - f.rt_score) as gap
        from gold.fact_title_performance f
        join gold.dim_titles d using (title_key)
        where {_CVA_FILTER}
        order by (f.tmdb_rating * 10 - f.rt_score) desc
        limit {limit}
    """)


def critics_over_audience(limit: int = 7):
    """Critical darlings: critics rated them well above the audience."""
    return _df(f"""
        select d.title, d.release_year, f.rt_score,
               round(f.tmdb_rating * 10) as audience_score,
               round(f.rt_score - f.tmdb_rating * 10) as gap
        from gold.fact_title_performance f
        join gold.dim_titles d using (title_key)
        where {_CVA_FILTER}
        order by (f.rt_score - f.tmdb_rating * 10) desc
        limit {limit}
    """)


# ---- Hype vs Reality page ---------------------------------------------------
def hype_scatter():
    return _df("""
        select title, release_year, primary_genre, trailer_views,
               roi_ratio, revenue_usd, composite_score, outcome_label
        from gold.mart_hype_vs_revenue
    """)


def hype_counts():
    return _df("""
        select outcome_label, count(*) as films,
               round(avg(roi_ratio), 1) as avg_roi,
               round(avg(trailer_views)) as avg_views
        from gold.mart_hype_vs_revenue
        group by 1
    """)


def hype_examples(label: str, limit: int = 5):
    return _df(f"""
        select title, release_year, trailer_views, roi_ratio
        from gold.mart_hype_vs_revenue
        where outcome_label = '{label}'
        order by trailer_views desc
        limit {limit}
    """)


# ---- Genre Trends page ------------------------------------------------------
def genre_year_trends(min_year: int = 1990):
    return _df(f"""
        select primary_genre, release_year, film_count,
               avg_roi, avg_tmdb_rating, avg_revenue_usd
        from gold.mart_genre_trends
        where release_year >= {min_year}
        order by release_year
    """)


def genre_totals():
    return _df("""
        select d.primary_genre,
               count(*)                    as films,
               round(avg(f.roi_ratio), 1)  as avg_roi,
               round(avg(f.composite_score), 1) as avg_score,
               round(sum(f.revenue_usd))   as total_revenue
        from gold.fact_title_performance f
        join gold.dim_titles d using (title_key)
        where d.primary_genre is not null
        group by 1
        having count(*) >= 10
        order by films desc
    """)


# ---- Audience sentiment (streaming buzz → VADER → metric) -------------------
def buzz_sentiment_summary():
    """Headline numbers for the audience-sentiment section."""
    return _df("""
        with s as (
            select count(sentiment_compound)                                 as scored,
                   count(distinct tmdb_id)                                    as films,
                   round(100.0 * count(*) filter (where sentiment_label = 'positive')
                         / nullif(count(sentiment_compound), 0), 1)           as pct_positive
            from silver.stg_buzz
        ),
        c as (  -- how closely comment enthusiasm tracks critic scores
            select round(corr(pct_positive, critic_score), 2) as corr_to_critics
            from gold.mart_buzz_vs_critics
        )
        select s.scored, s.films, s.pct_positive, c.corr_to_critics
        from s cross join c
    """)


def buzz_vs_critics():
    """One row per film: audience comment positivity vs critic score (RT %)."""
    return _df("""
        select title, release_year, primary_genre, buzz_events,
               pct_positive, critic_score, divergence
        from gold.mart_buzz_vs_critics
    """)


def buzz_vs_roi():
    """Per-film: trailer-comment positivity vs box-office ROI (films with 30+
    scored comments and a real ROI). Tests whether enthusiasm predicts returns."""
    return _df("""
        with buzz as (
            select tmdb_id, title, primary_genre, release_year,
                   buzz_events, pct_positive, avg_sentiment
            from gold.mart_film_buzz
            where scored_events >= 30
        )
        select b.title, b.release_year, b.primary_genre, b.buzz_events,
               b.pct_positive, b.avg_sentiment,
               f.roi_ratio, f.revenue_usd, f.is_profitable
        from buzz b
        join gold.dim_titles d on d.tmdb_id = b.tmdb_id
        join gold.fact_title_performance f using (title_key)
        where f.roi_ratio is not null
    """)


def buzz_roi_corr():
    """Single number: correlation between comment positivity and ROI."""
    return _df("""
        with buzz as (
            select tmdb_id, pct_positive from gold.mart_film_buzz where scored_events >= 30
        )
        select round(corr(b.pct_positive, f.roi_ratio), 2) as corr_to_roi,
               count(*)                                    as films
        from buzz b
        join gold.dim_titles d on d.tmdb_id = b.tmdb_id
        join gold.fact_title_performance f using (title_key)
        where f.roi_ratio is not null
    """)


def buzz_divergence(direction: str, limit: int = 6):
    """Films where crowd and critics most disagree.
    direction='crowd' → audiences warmer; 'critics' → critics warmer."""
    order = "desc" if direction == "crowd" else "asc"
    return _df(f"""
        select title, release_year, pct_positive, critic_score, divergence
        from gold.mart_buzz_vs_critics
        order by divergence {order}
        limit {limit}
    """)


# ---- Operations (CDC: Postgres → Debezium → Kafka → warehouse) --------------
def lifecycle_summary():
    """Headline numbers for the CDC / operations page."""
    return _df("""
        with cur as (
            select count(*) as live_films,
                   count(*) filter (where status = 'Now Playing') as now_playing,
                   round(avg(popularity), 1) as avg_popularity
            from gold.mart_film_lifecycle_current
        ),
        chg as (
            select count(*) as total_changes,
                   count(*) filter (where op_label = 'update') as updates,
                   count(*) filter (where op_label = 'insert') as inserts,
                   count(*) filter (where op_label = 'delete') as deletes,
                   count(*) filter (where status_changed) as transitions
            from gold.mart_lifecycle_changes
        )
        select * from cur cross join chg
    """)


def lifecycle_status_mix():
    return _df("""
        select status, count(*) as films, round(avg(popularity), 1) as avg_popularity
        from gold.mart_film_lifecycle_current
        group by 1
    """)


def lifecycle_current(limit: int = 12):
    return _df(f"""
        select title, status, popularity, vote_count, vote_average, last_change_ts
        from gold.mart_film_lifecycle_current
        order by popularity desc
        limit {limit}
    """)


def lifecycle_changes(limit: int = 14):
    """Recent change-data-capture events, newest first."""
    return _df(f"""
        select title, op_label, before_status, after_status, status_changed,
               before_popularity, after_popularity, source_ts
        from gold.mart_lifecycle_changes
        order by source_ts desc, change_id desc
        limit {limit}
    """)


def genre_leaderboard(limit: int = 8):
    return _df(f"""
        select d.primary_genre,
               count(*)                       as films,
               round(avg(f.roi_ratio), 2)     as avg_roi,
               round(avg(f.tmdb_rating), 2)    as avg_rating
        from gold.fact_title_performance f
        join gold.dim_titles d using (title_key)
        where d.primary_genre is not null
        group by 1
        having count(*) >= 10
        order by avg_roi desc
        limit {limit}
    """)

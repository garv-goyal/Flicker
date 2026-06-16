-- Gold mart: does audience enthusiasm match critical reception?
-- Joins the streaming buzz sentiment (share of positive trailer comments) to the
-- critic score (Rotten Tomatoes %) for every film with enough comments to be
-- meaningful. `divergence` > 0 means the crowd is warmer than the critics.
with buzz as (
    select tmdb_id, title, primary_genre, release_year,
           buzz_events, scored_events, avg_sentiment, pct_positive, pct_negative
    from {{ ref('mart_film_buzz') }}
    where scored_events >= 30
),

critics as (
    select d.tmdb_id, f.rt_score, f.composite_score, f.tmdb_rating, f.roi_ratio
    from {{ ref('fact_title_performance') }} f
    join {{ ref('dim_titles') }} d using (title_key)
    where f.rt_score is not null
)

select
    b.tmdb_id,
    b.title,
    b.primary_genre,
    b.release_year,
    b.buzz_events,
    b.scored_events,
    b.avg_sentiment,
    b.pct_positive,
    b.pct_negative,
    c.rt_score                              as critic_score,
    c.composite_score,
    c.tmdb_rating,
    c.roi_ratio,
    round(b.pct_positive - c.rt_score, 1)   as divergence
from buzz b
join critics c on c.tmdb_id = b.tmdb_id
order by b.buzz_events desc

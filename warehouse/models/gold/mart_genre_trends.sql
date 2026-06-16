-- Gold mart: one row per genre per year. Pre-aggregated for the dashboard.
select
    d.primary_genre,
    d.release_year,
    count(*)                                         as film_count,
    round(avg(f.budget_usd))                         as avg_budget_usd,
    round(avg(f.revenue_usd))                        as avg_revenue_usd,
    round(avg(f.roi_ratio), 2)                       as avg_roi,
    round(avg(f.tmdb_rating), 2)                     as avg_tmdb_rating,
    round(avg(f.popularity_score), 1)                as avg_popularity
from {{ ref('fact_title_performance') }} f
join {{ ref('dim_titles') }} d using (title_key)
where d.primary_genre is not null
group by 1, 2

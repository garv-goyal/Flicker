-- Gold fact: one row per title. Financial + critical + hype + awards metrics.
-- TMDB is the spine; OMDb (critical/awards) and YouTube (trailer hype) join in
-- as available (left joins), so films without enrichment still appear.
with movies as (
    select * from {{ ref('stg_movies') }}
),

reliable as (
    select
        *,
        -- TMDB has placeholder budgets (e.g. $12) that yield nonsense ROI.
        -- Only trust budgets of at least $1,000 for ROI; below that → null.
        case when budget_usd >= 1000 then budget_usd end as roi_budget_usd
    from movies
),

enr as (select * from {{ ref('stg_enrichment') }}),
trl as (select * from {{ ref('stg_trailer_engagement') }})

select
    {{ dbt_utils.generate_surrogate_key(['m.movie_id', "'movie'"]) }} as title_key,
    (strftime(m.release_date, '%Y%m%d'))::int                        as release_date_key,

    -- financial
    m.budget_usd,
    m.revenue_usd,
    e.box_office_usd,
    round(m.revenue_usd / nullif(m.roi_budget_usd, 0), 3)            as roi_ratio,
    (m.revenue_usd / nullif(m.roi_budget_usd, 0)) > 2.0             as is_profitable,

    -- critical
    m.tmdb_rating,
    m.tmdb_vote_count,
    e.rt_score,
    e.metacritic_score,
    e.imdb_rating,
    -- composite_score: mean of the available critical scores on a 0–100 scale
    round(list_avg(list_filter(
        [m.tmdb_rating * 10, e.rt_score::double, e.metacritic_score::double,
         e.imdb_rating * 10],
        x -> x is not null)), 1)                                     as composite_score,

    -- hype
    t.view_count                                                    as trailer_views,
    t.like_count                                                    as trailer_likes,
    t.engagement_rate                                               as trailer_engagement,
    t.days_before_release,

    -- awards
    coalesce(e.won_oscar, false)                                    as won_oscar,
    e.oscar_wins,
    e.total_award_wins,
    e.total_nominations,

    m.popularity_score
from reliable m
left join enr e on m.movie_id = e.tmdb_id
left join trl t on m.movie_id = t.tmdb_id

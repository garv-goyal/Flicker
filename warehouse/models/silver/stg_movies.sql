-- Silver: cleaned, typed, validated movies. One row per movie.
-- Parses the raw genres/collection JSON, casts dates, and nulls out zero
-- budgets/revenues (TMDB uses 0 to mean "unknown", which would skew ROI).

with deduped as (
    -- Bronze is raw and may contain duplicate ids; keep the latest row per movie.
    -- Dedup on plain Bronze columns (before any cast/JSON parse) so the window
    -- operates on simple types and projection pushdown stays correct.
    select *
    from {{ source('bronze', 'raw_tmdb_movies') }}
    qualify row_number() over (partition by tmdb_id order by _loaded_at desc) = 1
),

cleaned as (
    select
        tmdb_id as movie_id,
        title,
        original_title,

        -- dates
        try_cast(release_date as date)                       as release_date,
        extract(year from try_cast(release_date as date))    as release_year,
        -- floor-divide: ::int rounds in DuckDB (202.6→203), so 2026 would land in 2030s
        (extract(year from try_cast(release_date as date)) // 10 * 10)::int
                                                             as release_decade,

        -- genres (raw JSON array of {id, name})
        json_extract_string(genres, '$[*].name')             as genres_array,
        json_extract_string(genres, '$[0].name')             as primary_genre,

        -- financials (0 means unknown in TMDB → null)
        nullif(budget, 0)                                    as budget_usd,
        nullif(revenue, 0)                                   as revenue_usd,

        nullif(runtime, 0)                                   as runtime_minutes,
        round(vote_average, 1)                               as tmdb_rating,
        vote_count                                           as tmdb_vote_count,
        popularity                                           as popularity_score,
        status                                               as content_status,
        original_language,

        -- collection / franchise
        json_extract_string(belongs_to_collection, '$.id')   as collection_id,
        json_extract_string(belongs_to_collection, '$.name') as collection_name,

        -- lead production company
        json_extract_string(production_companies, '$[0].name') as production_company,

        _loaded_at
    from deduped
)

select *
from cleaned
where release_date is not null   -- drop unreleased/dateless rows from analytics

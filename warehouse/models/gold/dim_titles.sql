-- Gold dimension: one row per title with a surrogate key.
-- (Phase 1 = movies only; content_type is set up now for TV in a later phase.)
select
    {{ dbt_utils.generate_surrogate_key(['movie_id', "'movie'"]) }} as title_key,
    movie_id                                   as tmdb_id,
    'movie'                                    as content_type,
    title,
    release_date,
    release_year,
    release_decade,
    primary_genre,
    genres_array,
    runtime_minutes,
    original_language,
    production_company,
    (collection_id is not null)                as is_franchise,
    collection_name
from {{ ref('stg_movies') }}

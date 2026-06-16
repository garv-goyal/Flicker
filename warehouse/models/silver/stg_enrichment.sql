-- Silver: parse OMDb's display strings into clean typed metrics + awards.
with src as (
    select * from {{ source('bronze', 'raw_omdb_enrichment') }}
    qualify row_number() over (partition by imdb_id order by _loaded_at desc) = 1
)

select
    imdb_id,
    tmdb_id,

    -- "$104,757,650" → 104757650 ; "N/A" → null
    try_cast(regexp_replace(nullif(box_office, 'N/A'), '[^0-9]', '', 'g') as bigint)
        as box_office_usd,

    -- "95%" → 95
    try_cast(regexp_replace(nullif(rotten_tomatoes, 'N/A'), '[^0-9]', '', 'g') as integer)
        as rt_score,

    -- Metascore "77" → 77
    try_cast(nullif(metacritic, 'N/A') as integer)            as metacritic_score,

    try_cast(nullif(imdb_rating, 'N/A') as decimal(3, 1))     as imdb_rating,
    try_cast(regexp_replace(nullif(imdb_votes, 'N/A'), '[^0-9]', '', 'g') as bigint)
        as imdb_votes,
    nullif(rated, 'N/A')                                      as mpaa_rating,

    -- Awards text, e.g. "Won 2 Oscars. 10 wins & 5 nominations total"
    (awards ilike 'won%oscar%')                               as won_oscar,
    try_cast(regexp_extract(awards, 'Won (\d+) Oscar', 1) as integer)   as oscar_wins,
    try_cast(regexp_extract(awards, '(\d+) win', 1) as integer)         as total_award_wins,
    try_cast(regexp_extract(awards, '(\d+) nomination', 1) as integer)  as total_nominations,

    _loaded_at
from src

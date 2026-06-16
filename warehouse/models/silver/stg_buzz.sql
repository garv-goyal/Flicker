-- Silver: one clean row per streaming buzz event (deduped on event_id, typed ts),
-- enriched with the VADER sentiment score for the comment text.
with src as (
    select * from {{ source('bronze', 'raw_buzz_events') }}
    qualify row_number() over (partition by event_id order by ingested_at desc) = 1
),

sentiment as (
    select event_id, compound, label from {{ source('bronze', 'raw_buzz_sentiment') }}
)

select
    src.event_id,
    src.source,
    src.tmdb_id,
    src.title,
    src.page,
    src.text                              as edit_summary,
    src.author,
    try_cast(src.event_time as timestamp) as event_ts,
    src.ingested_at,
    s.compound                            as sentiment_compound,
    s.label                               as sentiment_label
from src
left join sentiment s on s.event_id = src.event_id
where src.tmdb_id is not null

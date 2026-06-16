-- Silver: one clean row per CDC change event (deduped on change_id = the Kafka
-- partition-offset, which is unique per change). Each row records the operation
-- and the full before/after image of the operational film_lifecycle row.
with src as (
    select * from {{ source('bronze', 'raw_cdc_film_lifecycle') }}
    qualify row_number() over (partition by change_id order by ingested_at desc) = 1
)

select
    change_id,
    op,
    op_label,
    tmdb_id,
    title,
    after_status,
    after_popularity,
    after_vote_count,
    after_vote_avg,
    before_status,
    before_popularity,
    before_vote_count,
    before_vote_avg,
    source_ts,
    ingested_at,
    kafka_offset
from src
where tmdb_id is not null

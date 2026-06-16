-- Gold: the change-history feed — every real mutation (insert/update/delete)
-- captured from the WAL, newest first, with the before→after values that changed.
-- Snapshot ('r') rows are excluded: they are the initial load, not a live change.
select
    change_id,
    tmdb_id,
    title,
    op_label,
    before_status,
    after_status,
    (before_status is distinct from after_status)         as status_changed,
    before_popularity,
    after_popularity,
    before_vote_count,
    after_vote_count,
    source_ts
from {{ ref('stg_film_lifecycle') }}
where op_label <> 'snapshot'
order by source_ts desc, kafka_offset desc

-- Gold: the CURRENT operational state of every film still in release, rebuilt
-- purely from the CDC stream. The latest change event per film wins; films whose
-- most recent event was a delete have left the operational system and drop out.
with latest as (
    select *
    from {{ ref('stg_film_lifecycle') }}
    qualify row_number() over (
        partition by tmdb_id order by source_ts desc, kafka_offset desc) = 1
)

select
    l.tmdb_id,
    l.title,
    l.after_status      as status,
    l.after_popularity  as popularity,
    l.after_vote_count  as vote_count,
    l.after_vote_avg    as vote_average,
    d.primary_genre,
    d.release_year,
    l.source_ts         as last_change_ts
from latest l
left join {{ ref('dim_titles') }} d on d.tmdb_id = l.tmdb_id
where l.op_label <> 'delete'
order by l.after_popularity desc

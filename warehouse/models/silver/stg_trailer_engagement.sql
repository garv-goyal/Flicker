-- Silver: trailer engagement, one row per film (latest snapshot).
with src as (
    select * from {{ source('bronze', 'raw_youtube_trailer_stats') }}
    qualify row_number() over (partition by tmdb_id order by snapshot_at desc) = 1
)

select
    tmdb_id,
    youtube_video_id,
    video_title,
    view_count,
    like_count,
    comment_count,
    -- engagement = (likes + comments) / views
    round((like_count + comment_count) / nullif(view_count, 0), 5) as engagement_rate,
    days_before_release,
    snapshot_at
from src

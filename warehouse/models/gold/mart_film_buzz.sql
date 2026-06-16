-- Gold mart: streaming buzz aggregated per film — discussion volume (YouTube
-- trailer comments), distinct authors, and the audience-sentiment metric derived
-- from VADER scores: mean compound score and the share of positive comments.
select
    b.tmdb_id,
    b.title,
    d.primary_genre,
    d.release_year,
    count(*)                                                  as buzz_events,
    count(distinct b.author)                                  as distinct_authors,
    count(b.sentiment_compound)                               as scored_events,
    round(avg(b.sentiment_compound), 3)                       as avg_sentiment,
    round(100.0 * count(*) filter (where b.sentiment_label = 'positive')
          / nullif(count(b.sentiment_compound), 0), 1)        as pct_positive,
    round(100.0 * count(*) filter (where b.sentiment_label = 'negative')
          / nullif(count(b.sentiment_compound), 0), 1)        as pct_negative,
    max(b.event_ts)                                           as last_event_ts
from {{ ref('stg_buzz') }} b
left join {{ ref('dim_titles') }} d on d.tmdb_id = b.tmdb_id
group by 1, 2, 3, 4
order by buzz_events desc, last_event_ts desc

-- Gold dimension: standard calendar, one row per day spanning the data's range.
with bounds as (
    select
        least(min(release_date), date '1930-01-01') as start_date,
        greatest(max(release_date), current_date)   as end_date
    from {{ ref('stg_movies') }}
),

dates as (
    select unnest(generate_series(
        (select start_date from bounds),
        (select end_date from bounds),
        interval 1 day
    ))::date as full_date
)

select
    (strftime(full_date, '%Y%m%d'))::int as date_key,
    full_date,
    extract(year   from full_date)       as year,
    extract(quarter from full_date)      as quarter,
    extract(month  from full_date)       as month,
    strftime(full_date, '%B')            as month_name,
    extract(week   from full_date)       as week_of_year,
    extract(dow    from full_date)       as day_of_week,
    strftime(full_date, '%A')            as day_name,
    extract(dow from full_date) in (0, 6) as is_weekend
from dates

-- Gold mart: one row per decade. Drives the home-page "ROI by decade" chart.
select
    d.release_decade,
    count(*)                                              as film_count,
    count(*) filter (where f.roi_ratio is not null)       as films_with_roi,
    round(avg(f.roi_ratio), 2)                            as avg_roi,
    round(median(f.roi_ratio), 2)                         as median_roi,
    round(avg(f.budget_usd))                              as avg_budget_usd,
    round(avg(f.revenue_usd))                             as avg_revenue_usd,
    round(100.0 * count(*) filter (where f.is_profitable)
          / nullif(count(*) filter (where f.roi_ratio is not null), 0), 1) as profitable_pct
from {{ ref('fact_title_performance') }} f
join {{ ref('dim_titles') }} d using (title_key)
group by 1
order by 1

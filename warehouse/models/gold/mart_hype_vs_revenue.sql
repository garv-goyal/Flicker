-- Gold mart: trailer hype vs box-office reality, one row per film that has both
-- a trailer-view signal and a computable ROI. Labels each film by comparing its
-- hype and its return against the medians of this set.
with base as (
    select
        d.title, d.release_year, d.primary_genre,
        f.budget_usd, f.revenue_usd, f.roi_ratio,
        f.trailer_views, f.trailer_engagement, f.composite_score
    from {{ ref('fact_title_performance') }} f
    join {{ ref('dim_titles') }} d using (title_key)
    where f.trailer_views is not null and f.roi_ratio is not null
),

thresholds as (
    select median(trailer_views) as med_hype, median(roi_ratio) as med_roi from base
)

select
    b.*,
    case
        when b.trailer_views >= t.med_hype and b.roi_ratio <  t.med_roi then 'Overhyped'
        when b.trailer_views <  t.med_hype and b.roi_ratio >= t.med_roi then 'Hidden gem'
        when b.trailer_views >= t.med_hype and b.roi_ratio >= t.med_roi then 'Delivered'
        else 'Overlooked'
    end as outcome_label
from base b
cross join thresholds t

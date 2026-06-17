import { query, queryOne } from "./db";

// ── Overview / Pulse ──────────────────────────────────────────────────────────

export async function headlineMetrics() {
  return queryOne<{
    total_films: number;
    first_year: number;
    last_year: number;
    genres: number;
  }>(`
    select count(*)                    as total_films,
           min(release_year)           as first_year,
           max(release_year)           as last_year,
           count(distinct primary_genre) as genres
    from gold.dim_titles
  `);
}

export async function roiSummary() {
  return queryOne<{
    avg_roi: number;
    median_roi: number;
    profitable_pct: number;
  }>(`
    select round(avg(roi_ratio), 2)  as avg_roi,
           round(median(roi_ratio), 2) as median_roi,
           round(100.0 * count(*) filter (where is_profitable)
                 / nullif(count(*) filter (where roi_ratio is not null), 0), 1)
               as profitable_pct
    from gold.fact_title_performance
  `);
}

export async function roiByDecade() {
  return query<{
    release_decade: number;
    film_count: number;
    avg_roi: number;
    median_roi: number;
    profitable_pct: number;
  }>(`
    select release_decade, film_count, avg_roi, median_roi, profitable_pct
    from gold.mart_roi_by_decade
    order by release_decade
  `);
}

export async function topRoiFilms(limit = 10) {
  return query<{
    title: string;
    release_year: number;
    primary_genre: string;
    budget_usd: number;
    revenue_usd: number;
    roi_ratio: number;
    tmdb_rating: number;
  }>(`
    select d.title, d.release_year, d.primary_genre,
           f.budget_usd, f.revenue_usd, f.roi_ratio, f.tmdb_rating
    from gold.fact_title_performance f
    join gold.dim_titles d using (title_key)
    where f.roi_ratio is not null and f.budget_usd >= 1000000
    order by f.roi_ratio desc
    limit ${limit}
  `);
}

export async function genreLeaderboard(limit = 8) {
  return query<{
    primary_genre: string;
    films: number;
    avg_roi: number;
    avg_rating: number;
  }>(`
    select d.primary_genre,
           count(*)                        as films,
           round(avg(f.roi_ratio), 2)      as avg_roi,
           round(avg(f.tmdb_rating), 2)    as avg_rating
    from gold.fact_title_performance f
    join gold.dim_titles d using (title_key)
    where d.primary_genre is not null
    group by 1
    having count(*) >= 10
    order by avg_roi desc
    limit ${limit}
  `);
}

export async function filmOfTheDay() {
  return query<{
    title: string;
    release_year: number;
    primary_genre: string;
    composite_score: number;
    tmdb_rating: number;
    rt_score: number;
    metacritic_score: number;
    roi_ratio: number | null;
    won_oscar: boolean;
    oscar_wins: number | null;
  }>(`
    select d.title, d.release_year, d.primary_genre,
           f.composite_score, f.tmdb_rating, f.rt_score, f.metacritic_score,
           f.roi_ratio, f.won_oscar, f.oscar_wins
    from gold.fact_title_performance f
    join gold.dim_titles d using (title_key)
    where f.composite_score >= 80
      and f.tmdb_rating is not null
      and f.rt_score is not null
    order by (f.composite_score + f.tmdb_rating * 5) desc
    limit 60
  `);
}

// ── Ticker (popularity movers) ────────────────────────────────────────────────

export async function tickerFilms() {
  return query<{
    title: string;
    popularity: number;
    status: string;
  }>(`
    select title, popularity, status
    from gold.mart_film_lifecycle_current
    order by popularity desc
    limit 30
  `);
}

// ── Critical Reception ────────────────────────────────────────────────────────

export async function criticalSummary() {
  return queryOne<{
    scored: number;
    avg_composite: number;
    oscar_winners: number;
    with_rt: number;
  }>(`
    select count(*) filter (where composite_score is not null)  as scored,
           round(avg(composite_score), 1)                        as avg_composite,
           count(*) filter (where won_oscar)                     as oscar_winners,
           count(*) filter (where rt_score is not null)          as with_rt
    from gold.fact_title_performance
  `);
}

export async function bestReviewed(limit = 12) {
  return query<{
    title: string;
    release_year: number;
    primary_genre: string;
    composite_score: number;
    rt_score: number | null;
    metacritic_score: number | null;
    imdb_rating: number | null;
    won_oscar: boolean;
    oscar_wins: number | null;
  }>(`
    select d.title, d.release_year, d.primary_genre,
           f.composite_score, f.rt_score, f.metacritic_score,
           f.imdb_rating, f.won_oscar, f.oscar_wins
    from gold.fact_title_performance f
    join gold.dim_titles d using (title_key)
    where f.composite_score is not null
    order by f.composite_score desc, f.rt_score desc
    limit ${limit}
  `);
}

const CVA_FILTER = `
  f.rt_score is not null and f.metacritic_score is not null
  and f.tmdb_rating is not null and f.tmdb_vote_count >= 1000
`;

export async function audienceOverCritics(limit = 7) {
  return query<{
    title: string;
    release_year: number;
    rt_score: number;
    audience_score: number;
    gap: number;
  }>(`
    select d.title, d.release_year, f.rt_score,
           round(f.tmdb_rating * 10) as audience_score,
           round(f.tmdb_rating * 10 - f.rt_score) as gap
    from gold.fact_title_performance f
    join gold.dim_titles d using (title_key)
    where ${CVA_FILTER}
    order by (f.tmdb_rating * 10 - f.rt_score) desc
    limit ${limit}
  `);
}

export async function criticsOverAudience(limit = 7) {
  return query<{
    title: string;
    release_year: number;
    rt_score: number;
    audience_score: number;
    gap: number;
  }>(`
    select d.title, d.release_year, f.rt_score,
           round(f.tmdb_rating * 10) as audience_score,
           round(f.rt_score - f.tmdb_rating * 10) as gap
    from gold.fact_title_performance f
    join gold.dim_titles d using (title_key)
    where ${CVA_FILTER}
    order by (f.rt_score - f.tmdb_rating * 10) desc
    limit ${limit}
  `);
}

// ── Hype vs Reality ───────────────────────────────────────────────────────────

export async function hypeScatter() {
  return query<{
    title: string;
    release_year: number;
    primary_genre: string;
    trailer_views: number;
    roi_ratio: number;
    composite_score: number;
    outcome_label: string;
  }>(`
    select title, release_year, primary_genre, trailer_views,
           roi_ratio, composite_score, outcome_label
    from gold.mart_hype_vs_revenue
  `);
}

export async function hypeCounts() {
  return query<{
    outcome_label: string;
    films: number;
    avg_roi: number;
    avg_views: number;
  }>(`
    select outcome_label, count(*) as films,
           round(avg(roi_ratio), 1) as avg_roi,
           round(avg(trailer_views)) as avg_views
    from gold.mart_hype_vs_revenue
    group by 1
  `);
}

export async function hypeExamples(label: string, limit = 6) {
  return query<{
    title: string;
    release_year: number;
    trailer_views: number;
    roi_ratio: number;
  }>(`
    select title, release_year, trailer_views, roi_ratio
    from gold.mart_hype_vs_revenue
    where outcome_label = '${label.replace(/'/g, "''")}'
    order by trailer_views desc
    limit ${limit}
  `);
}

// ── Verdict Search ────────────────────────────────────────────────────────────

export async function searchFilms(q: string) {
  const safe = q.replace(/'/g, "''");
  return query<{ title: string; release_year: number }>(`
    select d.title, d.release_year
    from gold.dim_titles d
    where lower(d.title) like lower('%${safe}%')
    order by d.release_year desc
    limit 8
  `);
}

export async function filmVerdict(title: string) {
  const safe = title.replace(/'/g, "''");
  return queryOne<{
    title: string;
    release_year: number;
    primary_genre: string;
    composite_score: number | null;
    rt_score: number | null;
    tmdb_rating: number | null;
    roi_ratio: number | null;
    outcome_label: string | null;
    won_oscar: boolean;
    oscar_wins: number | null;
  }>(`
    select d.title, d.release_year, d.primary_genre,
           f.composite_score, f.rt_score, f.tmdb_rating, f.roi_ratio,
           h.outcome_label, f.won_oscar, f.oscar_wins
    from gold.dim_titles d
    join gold.fact_title_performance f using (title_key)
    left join gold.mart_hype_vs_revenue h on h.title = d.title
    where lower(d.title) = lower('${safe}')
    limit 1
  `);
}

// ── Mood Discovery ────────────────────────────────────────────────────────────

export type Mood =
  | "prestige"
  | "blockbuster"
  | "feel-good"
  | "mind-bending"
  | "hidden-gem"
  | "dark-slow-burn";

export async function discoverByMood(mood: Mood, limit = 20) {
  const filters: Record<Mood, string> = {
    prestige: `
      d.primary_genre in ('Drama','Biography')
      and f.composite_score >= 75
      and (f.won_oscar = true or f.rt_score >= 80)
    `,
    blockbuster: `
      d.primary_genre in ('Action','Adventure','Science Fiction')
      and f.roi_ratio >= 2
      and f.budget_usd >= 50000000
    `,
    "feel-good": `
      d.primary_genre in ('Comedy','Animation','Family','Romance')
      and f.tmdb_rating >= 7.0
      and f.composite_score >= 60
    `,
    "mind-bending": `
      d.primary_genre in ('Science Fiction','Thriller','Mystery','Horror')
      and f.composite_score >= 65
      and f.tmdb_rating >= 6.5
    `,
    "hidden-gem": `
      h.outcome_label = 'Hidden gem'
      and f.composite_score >= 60
    `,
    "dark-slow-burn": `
      d.primary_genre in ('Drama','Thriller','Crime')
      and f.rt_score >= 75
      and f.composite_score >= 70
    `,
  };

  const where = filters[mood];
  return query<{
    title: string;
    release_year: number;
    primary_genre: string;
    composite_score: number;
    rt_score: number | null;
    tmdb_rating: number | null;
    roi_ratio: number | null;
  }>(`
    select d.title, d.release_year, d.primary_genre,
           f.composite_score, f.rt_score, f.tmdb_rating, f.roi_ratio
    from gold.fact_title_performance f
    join gold.dim_titles d using (title_key)
    left join gold.mart_hype_vs_revenue h on h.title = d.title
    where ${where}
    order by f.composite_score desc nulls last
    limit ${limit}
  `);
}

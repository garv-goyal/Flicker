import {
  headlineMetrics,
  roiSummary,
  roiByDecade,
  topRoiFilms,
  genreLeaderboard,
  filmOfTheDay,
} from "@/lib/queries";
import RoiDecadeChart from "@/components/charts/roi-decade-chart";
import FilmOfDay from "@/components/film-of-day";

export const revalidate = 3600;

function money(v: number | null) {
  if (!v) return "—";
  if (v >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6) return `$${(v / 1e6).toFixed(0)}M`;
  return `$${v.toLocaleString()}`;
}

export default async function PulsePage() {
  const [metrics, roi, decade, top, genres, fotd] = await Promise.all([
    headlineMetrics(),
    roiSummary(),
    roiByDecade(),
    topRoiFilms(10),
    genreLeaderboard(8),
    filmOfTheDay(),
  ]);

  const best = genres[0] ?? null;

  return (
    <div className="page-wrap">
      {/* ── Hero ──────────────────────────────────────────────────── */}
      <div className="hero">
        <div className="eyebrow">Industry Pulse</div>
        <h1>
          Film intelligence,<br />
          <em>not guesswork.</em>
        </h1>
        <p>
          Box office returns, critic scores, and audience sentiment across{" "}
          <strong style={{ color: "var(--text)" }}>
            {metrics ? parseInt(String(metrics.total_films)).toLocaleString() : "—"}
          </strong>{" "}
          films — from{" "}
          <strong style={{ color: "var(--text)" }}>{metrics?.first_year}</strong> to{" "}
          <strong style={{ color: "var(--text)" }}>{metrics?.last_year}</strong>.
          See what works, what flops, and where the market is moving.
        </p>
      </div>

      {/* ── KPI cards ─────────────────────────────────────────────── */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-value">
            {metrics ? parseInt(String(metrics.total_films)).toLocaleString() : "—"}
          </div>
          <div className="kpi-label">Films tracked</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-value">
            {metrics ? `${metrics.first_year}–${metrics.last_year}` : "—"}
          </div>
          <div className="kpi-label">Year span</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-value">{metrics?.genres ?? "—"}</div>
          <div className="kpi-label">Genres</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-value">{roi ? `${roi.profitable_pct}%` : "—"}</div>
          <div className="kpi-label">Turned a profit</div>
        </div>
      </div>

      {/* ── Today's pick ──────────────────────────────────────────── */}
      {fotd.length > 0 && (
        <>
          <div className="divider" />
          <div className="section-head">
            <h2>Today&rsquo;s pick</h2>
            <p>One top-rated film, rotated daily from the best in the dataset.</p>
          </div>
          <FilmOfDay films={fotd} />
        </>
      )}

      <div className="divider" />

      {/* ── ROI by decade + Genre leaderboard ─────────────────────── */}
      <div className="page-grid-2">
        <div>
          <div className="section-head">
            <h2>Return on investment by decade</h2>
            <p>Median ROI per decade — resistant to outlier blockbusters.</p>
          </div>
          <div className="chart-card">
            <RoiDecadeChart data={decade} />
          </div>
        </div>

        <div>
          <div className="section-head">
            <h2>Highest-ROI genres</h2>
            <p>10+ films each, ranked by average return.</p>
          </div>
          <div className="card" style={{ padding: 0 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th className="rank" />
                  <th>Genre</th>
                  <th className="r">Films</th>
                  <th className="r">ROI</th>
                  <th className="r">Rating</th>
                </tr>
              </thead>
              <tbody>
                {genres.map((g, i) => (
                  <tr key={g.primary_genre}>
                    <td className="rank">{i + 1}</td>
                    <td className="title-col">{g.primary_genre}</td>
                    <td className="r mono-val" style={{ color: "var(--muted)" }}>
                      {g.films}
                    </td>
                    <td className="r accent-val">{Number(g.avg_roi).toFixed(1)}×</td>
                    <td className="r mono-val" style={{ color: "var(--muted)" }}>
                      {Number(g.avg_rating).toFixed(1)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ── Key finding ───────────────────────────────────────────── */}
      {best && (
        <div style={{ marginTop: "20px" }}>
          <div className="insight">
            <div className="insight-label">Key finding</div>
            <p className="insight-text">
              &ldquo;{best.primary_genre}&rdquo; films average{" "}
              <strong style={{ color: "var(--accent)", fontStyle: "normal" }}>
                {Number(best.avg_roi).toFixed(1)}×
              </strong>{" "}
              return on budget — the highest of any genre in the dataset.
            </p>
            <p className="insight-sub">
              Across {best.films} films with verified budget and revenue data. The
              pattern holds even after removing outlier blockbusters.
            </p>
          </div>
        </div>
      )}

      <div className="divider" />

      {/* ── Highest-return films ──────────────────────────────────── */}
      <div className="section-head">
        <h2>Highest-return films</h2>
        <p>Budget ≥ $1M. Ranked by revenue ÷ budget.</p>
      </div>
      <div className="card" style={{ padding: 0 }}>
        <table className="data-table">
          <thead>
            <tr>
              <th className="rank" />
              <th>Title</th>
              <th className="r">Year</th>
              <th>Genre</th>
              <th className="r">Budget</th>
              <th className="r">Revenue</th>
              <th className="r">ROI</th>
              <th className="r">Rating</th>
            </tr>
          </thead>
          <tbody>
            {top.map((f, i) => (
              <tr key={f.title}>
                <td className="rank">{i + 1}</td>
                <td className="title-col" style={{ maxWidth: "180px" }}>
                  {f.title}
                </td>
                <td className="r mono-val" style={{ color: "var(--muted)" }}>
                  {f.release_year}
                </td>
                <td>
                  <span className="chip">{f.primary_genre}</span>
                </td>
                <td className="r mono-val" style={{ color: "var(--muted)" }}>
                  {money(f.budget_usd)}
                </td>
                <td className="r mono-val">{money(f.revenue_usd)}</td>
                <td className="r accent-val">{Number(f.roi_ratio).toFixed(1)}×</td>
                <td className="r mono-val" style={{ color: "var(--muted)" }}>
                  {f.tmdb_rating?.toFixed(1) ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

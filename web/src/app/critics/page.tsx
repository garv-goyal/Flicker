import {
  criticalSummary,
  bestReviewed,
  audienceOverCritics,
  criticsOverAudience,
} from "@/lib/queries";

export const revalidate = 3600;

function cell(v: number | null, suffix = "") {
  return v == null ? "—" : `${v}${suffix}`;
}

export default async function CriticsPage() {
  const [summary, best, audienceFav, criticsFav] = await Promise.all([
    criticalSummary(),
    bestReviewed(12),
    audienceOverCritics(7),
    criticsOverAudience(7),
  ]);

  const oscarPct =
    summary && summary.scored > 0
      ? ((summary.oscar_winners / summary.scored) * 100).toFixed(1)
      : "—";

  return (
    <div className="page-wrap">
      <div className="hero">
        <div className="eyebrow">Critics · Audience · Awards</div>
        <h1>
          The scores behind<br />
          <em>the acclaim.</em>
        </h1>
        <p>
          Rotten Tomatoes, Metacritic, IMDb, and TMDB — blended into a single composite
          so you can compare films regardless of which platform rated them.
        </p>
      </div>

      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-value">
            {summary ? parseInt(String(summary.scored)).toLocaleString() : "—"}
          </div>
          <div className="kpi-label">Films scored</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-value">{summary?.avg_composite ?? "—"}</div>
          <div className="kpi-label">Avg composite</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-value">{summary?.oscar_winners ?? "—"}</div>
          <div className="kpi-label">Oscar winners</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-value">
            {summary ? parseInt(String(summary.with_rt)).toLocaleString() : "—"}
          </div>
          <div className="kpi-label">With RT score</div>
        </div>
      </div>

      <div className="divider" />

      <div className="section-head">
        <h2>Best-reviewed films</h2>
        <p>Ranked by composite score. Awards column shows Oscar wins.</p>
      </div>
      <div className="card" style={{ padding: 0 }}>
        <table className="data-table">
          <thead>
            <tr>
              <th className="rank" />
              <th>Title</th>
              <th className="r">Year</th>
              <th>Genre</th>
              <th className="r">Composite</th>
              <th className="r">RT</th>
              <th className="r">Metacritic</th>
              <th className="r">IMDb</th>
              <th className="r">Awards</th>
            </tr>
          </thead>
          <tbody>
            {best.map((f, i) => (
              <tr key={f.title}>
                <td className="rank">{i + 1}</td>
                <td className="title-col">{f.title}</td>
                <td className="r mono-val" style={{ color: "var(--muted)" }}>
                  {f.release_year}
                </td>
                <td><span className="chip">{f.primary_genre}</span></td>
                <td className="r accent-val">{Math.round(f.composite_score)}</td>
                <td className="r mono-val" style={{ color: "var(--muted)" }}>
                  {cell(f.rt_score, "%")}
                </td>
                <td className="r mono-val" style={{ color: "var(--muted)" }}>
                  {cell(f.metacritic_score)}
                </td>
                <td className="r mono-val" style={{ color: "var(--muted)" }}>
                  {cell(f.imdb_rating)}
                </td>
                <td className="r">
                  {f.won_oscar && f.oscar_wins ? (
                    <span className="badge badge-oscar">
                      {f.oscar_wins}× Oscar
                    </span>
                  ) : (
                    <span style={{ color: "var(--faint)" }}>—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {summary && (
        <div style={{ marginTop: "16px" }}>
          <div className="insight">
            <div className="insight-label">Data note</div>
            <p className="insight-text">
              Oscar-winning films account for{" "}
              <strong style={{ color: "var(--accent)", fontStyle: "normal" }}>
                {oscarPct}%
              </strong>{" "}
              of scored titles — yet cluster almost entirely in the top quartile.
            </p>
            <p className="insight-sub">
              Critical consensus and Academy taste point to the same films more
              reliably than audiences typically assume. {summary.oscar_winners} winners in dataset.
            </p>
          </div>
        </div>
      )}

      <div className="divider" />

      <div className="section-head">
        <h2>Where critics and audiences disagree</h2>
        <p>
          Widest gaps between RT score and audience rating (TMDB), among films
          with broad critical coverage and 1,000+ votes.
        </p>
      </div>

      <div className="page-grid-equal">
        <div>
          <div className="section-head">
            <h2 style={{ fontSize: "16px" }}>Audiences loved them</h2>
            <p>Crowd-pleasers the critics underrated.</p>
          </div>
          <div className="card" style={{ padding: 0 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th className="r">Year</th>
                  <th className="r">Critics</th>
                  <th className="r">Audience</th>
                  <th className="r">Gap</th>
                </tr>
              </thead>
              <tbody>
                {audienceFav.map((r) => (
                  <tr key={r.title}>
                    <td className="title-col">{r.title}</td>
                    <td className="r mono-val" style={{ color: "var(--muted)" }}>
                      {r.release_year}
                    </td>
                    <td className="r mono-val" style={{ color: "var(--muted)" }}>
                      {r.rt_score}%
                    </td>
                    <td className="r mono-val">{r.audience_score}</td>
                    <td className="r">
                      <span className="badge badge-delivered">+{r.gap}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <div className="section-head">
            <h2 style={{ fontSize: "16px" }}>Critics loved them</h2>
            <p>Critical darlings that left audiences lukewarm.</p>
          </div>
          <div className="card" style={{ padding: 0 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th className="r">Year</th>
                  <th className="r">Critics</th>
                  <th className="r">Audience</th>
                  <th className="r">Gap</th>
                </tr>
              </thead>
              <tbody>
                {criticsFav.map((r) => (
                  <tr key={r.title}>
                    <td className="title-col">{r.title}</td>
                    <td className="r mono-val" style={{ color: "var(--muted)" }}>
                      {r.release_year}
                    </td>
                    <td className="r mono-val">{r.rt_score}%</td>
                    <td className="r mono-val" style={{ color: "var(--muted)" }}>
                      {r.audience_score}
                    </td>
                    <td className="r">
                      <span className="badge badge-gem">+{r.gap}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

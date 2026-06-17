"use client";

import { useMemo } from "react";

interface Film {
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
}

export default function FilmOfDay({ films }: { films: Film[] }) {
  const film = useMemo(() => {
    if (!films.length) return null;
    const now = new Date();
    const start = new Date(now.getFullYear(), 0, 0);
    const dayOfYear = Math.floor((now.getTime() - start.getTime()) / 86400000);
    return films[dayOfYear % films.length];
  }, [films]);

  if (!film) return null;

  const today = new Date().toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const bars = [
    { label: "Composite",       val: film.composite_score },
    { label: "Rotten Tomatoes", val: film.rt_score },
    { label: "Audience (×10)", val: film.tmdb_rating * 10 },
  ].filter((b) => b.val != null);

  return (
    <div className="page-grid-2" style={{ alignItems: "stretch" }}>
      {/* Film card */}
      <div className="film-feature">
        <div className="film-date">{today}</div>
        <div className="film-title">{film.title}</div>
        <div className="film-meta">
          {film.release_year}&ensp;·&ensp;{film.primary_genre}
          {film.won_oscar && (
            <span className="badge badge-oscar" style={{ marginLeft: "10px" }}>
              {film.oscar_wins ? `${film.oscar_wins}× Oscar` : "Oscar Winner"}
            </span>
          )}
        </div>
        <div>
          {bars.map((b) => (
            <div key={b.label} className="score-bar-row">
              <span className="score-bar-label">{b.label}</span>
              <div className="score-bar-track">
                <div
                  className="score-bar-fill"
                  style={{ width: `${Math.min(b.val, 100)}%` }}
                />
              </div>
              <span className="score-bar-val">{Math.round(b.val)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Insight */}
      <div
        className="insight"
        style={{ height: "100%", boxSizing: "border-box" }}
      >
        <div className="insight-label">Why this film</div>
        <p className="insight-text">
          &ldquo;{film.title}&rdquo; ranks among the highest-rated films across all
          scoring sources in the dataset.
        </p>
        <p className="insight-sub">
          {film.roi_ratio != null && (
            <>
              Returned{" "}
              <strong style={{ color: "var(--accent)" }}>
                {film.roi_ratio.toFixed(1)}×
              </strong>{" "}
              its budget at the box office.{" "}
            </>
          )}
          {film.won_oscar && (
            <>
              Won{" "}
              {film.oscar_wins ? (
                <>
                  {film.oscar_wins}{" "}
                  {film.oscar_wins === 1 ? "Oscar" : "Oscars"}.
                </>
              ) : (
                "an Oscar."
              )}
            </>
          )}
        </p>

        <div style={{ marginTop: "auto", paddingTop: "20px" }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "10px",
            }}
          >
            {[
              { label: "Composite", val: `${Math.round(film.composite_score)}` },
              { label: "RT Score",  val: `${Math.round(film.rt_score)}%` },
              { label: "Audience",  val: `${Math.round(film.tmdb_rating * 10)}` },
              {
                label: "ROI",
                val: film.roi_ratio != null ? `${film.roi_ratio.toFixed(1)}×` : "—",
              },
            ].map((s) => (
              <div
                key={s.label}
                style={{
                  background: "rgba(0,0,0,0.2)",
                  borderRadius: "8px",
                  padding: "10px 12px",
                }}
              >
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "18px",
                    fontWeight: 700,
                    color: "var(--text)",
                    marginBottom: "3px",
                  }}
                >
                  {s.val}
                </div>
                <div
                  style={{
                    fontSize: "10px",
                    color: "var(--muted)",
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                  }}
                >
                  {s.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

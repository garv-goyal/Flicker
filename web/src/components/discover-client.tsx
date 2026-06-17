"use client";

import { useCallback, useEffect, useState } from "react";

type Mood =
  | "prestige"
  | "blockbuster"
  | "feel-good"
  | "mind-bending"
  | "hidden-gem"
  | "dark-slow-burn";

interface Film {
  title: string;
  release_year: number;
  primary_genre: string;
  composite_score: number;
  rt_score: number | null;
  tmdb_rating: number | null;
  roi_ratio: number | null;
}

const MOODS: { id: Mood; label: string; desc: string; icon: string }[] = [
  {
    id: "prestige",
    label: "Prestige Drama",
    desc: "Award-winners, critical darlings",
    icon: "◆",
  },
  {
    id: "blockbuster",
    label: "Safe Blockbuster",
    desc: "Big budget, big returns",
    icon: "◈",
  },
  {
    id: "feel-good",
    label: "Feel-good",
    desc: "High audience scores, light tone",
    icon: "◉",
  },
  {
    id: "mind-bending",
    label: "Mind-bending",
    desc: "Sci-fi, thriller, and the uncanny",
    icon: "◌",
  },
  {
    id: "hidden-gem",
    label: "Hidden Gem",
    desc: "Low hype, outsized quality",
    icon: "◎",
  },
  {
    id: "dark-slow-burn",
    label: "Dark & Slow-burn",
    desc: "Drama, crime, atmosphere",
    icon: "◧",
  },
];

export default function DiscoverClient() {
  const [activeMood, setActiveMood] = useState<Mood | null>(null);
  const [films, setFilms] = useState<Film[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const fetchMood = useCallback(async (mood: Mood, attempt = 0) => {
    setLoading(true);
    setError(false);
    setFilms([]);
    try {
      const r = await fetch(`/api/discover?mood=${mood}`);
      if (!r.ok) throw new Error(`status ${r.status}`);
      const d = await r.json();
      setFilms(d.films ?? []);
    } catch {
      if (attempt < 1) {
        await fetchMood(mood, attempt + 1);
        return;
      }
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeMood) fetchMood(activeMood);
  }, [activeMood, fetchMood]);

  return (
    <div>
      {/* Mood selector */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "10px",
          marginBottom: "32px",
        }}
      >
        {MOODS.map((m) => (
          <button
            key={m.id}
            className={`mood-tag ${activeMood === m.id ? "active" : ""}`}
            onClick={() =>
              setActiveMood((prev) => (prev === m.id ? null : m.id))
            }
          >
            <span style={{ fontSize: "14px", opacity: 0.7 }}>{m.icon}</span>
            <span>{m.label}</span>
            <span
              style={{
                fontSize: "11px",
                color: "var(--muted)",
                display: "none",
              }}
            >
              {m.desc}
            </span>
          </button>
        ))}
      </div>

      {/* Active mood description */}
      {activeMood && (
        <div style={{ marginBottom: "24px" }}>
          <p style={{ color: "var(--muted)", fontSize: "13px" }}>
            {MOODS.find((m) => m.id === activeMood)?.desc}
            {loading ? " — Loading…" : films.length ? ` — ${films.length} films` : ""}
          </p>
        </div>
      )}

      {/* Results grid */}
      {loading && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
            gap: "14px",
          }}
        >
          {Array.from({ length: 12 }).map((_, i) => (
            <div
              key={i}
              className="film-result-card"
              style={{ opacity: 0.4, height: "120px", animation: "pulse 1.5s ease-in-out infinite" }}
            />
          ))}
        </div>
      )}

      {!loading && films.length > 0 && (
        <div className="film-grid">
          {films.map((f) => (
            <div key={`${f.title}-${f.release_year}`} className="film-result-card">
              <div className="film-result-title">{f.title}</div>
              <div className="film-result-meta">
                {f.release_year}&ensp;·&ensp;{f.primary_genre}
              </div>
              <div
                style={{
                  display: "flex",
                  alignItems: "flex-end",
                  justifyContent: "space-between",
                }}
              >
                <div>
                  <div className="film-result-score">
                    {f.composite_score != null
                      ? Math.round(f.composite_score)
                      : "—"}
                  </div>
                  <div
                    style={{
                      fontSize: "10px",
                      color: "var(--muted)",
                      letterSpacing: "0.08em",
                      textTransform: "uppercase",
                    }}
                  >
                    Composite
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  {f.rt_score != null && (
                    <div
                      style={{
                        fontSize: "12px",
                        color: "var(--muted)",
                        fontFamily: "var(--font-mono)",
                      }}
                    >
                      RT {Math.round(f.rt_score)}%
                    </div>
                  )}
                  {f.roi_ratio != null && (
                    <div
                      style={{
                        fontSize: "12px",
                        color: "var(--accent)",
                        fontFamily: "var(--font-mono)",
                        fontWeight: 600,
                      }}
                    >
                      {f.roi_ratio.toFixed(1)}× ROI
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && error && (
        <div className="empty-state">
          Couldn&rsquo;t load films right now — try again in a moment.
        </div>
      )}

      {!loading && !error && activeMood && films.length === 0 && (
        <div className="empty-state">
          No films found for this vibe in the current dataset.
        </div>
      )}

      {!activeMood && (
        <div className="empty-state">
          Select a vibe above to discover films.
        </div>
      )}
    </div>
  );
}

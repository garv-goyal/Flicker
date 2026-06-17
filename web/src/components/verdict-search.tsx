"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface SearchResult {
  title: string;
  release_year: number;
}

interface VerdictFilm {
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
}

const OUTCOME_STYLES: Record<
  string,
  { cls: string; label: string }
> = {
  Delivered:    { cls: "badge-delivered",  label: "Delivered" },
  "Hidden gem": { cls: "badge-gem",        label: "Hidden Gem" },
  Overhyped:    { cls: "badge-overhyped",  label: "Overhyped" },
  Overlooked:   { cls: "badge-overlooked", label: "Overlooked" },
};

export default function VerdictSearch({ onClose }: { onClose: () => void }) {
  const [q, setQ] = useState("");
  const [suggestions, setSuggestions] = useState<SearchResult[]>([]);
  const [verdict, setVerdict] = useState<VerdictFilm | null>(null);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [onClose]);

  const search = useCallback(async (val: string) => {
    if (val.length < 2) { setSuggestions([]); return; }
    const r = await fetch(`/api/search?q=${encodeURIComponent(val)}`);
    const d = await r.json();
    setSuggestions(d.results ?? []);
  }, []);

  useEffect(() => {
    const t = setTimeout(() => search(q), 200);
    return () => clearTimeout(t);
  }, [q, search]);

  async function pickFilm(title: string) {
    setSuggestions([]);
    setQ(title);
    setLoading(true);
    try {
      const r = await fetch(`/api/verdict?title=${encodeURIComponent(title)}`);
      const d = await r.json();
      setVerdict(d.film ?? null);
    } finally {
      setLoading(false);
    }
  }

  const score = (v: number | null, mul = 1) =>
    v == null ? "—" : `${Math.round(v * mul)}`;

  const outcomeMeta =
    verdict?.outcome_label ? OUTCOME_STYLES[verdict.outcome_label] : null;

  return (
    <div className="search-overlay" onClick={onClose}>
      <div className="search-box" onClick={(e) => e.stopPropagation()}>
        <div className="search-input-wrap">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--muted)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
          <input
            ref={inputRef}
            className="search-input"
            placeholder="Search any film for its verdict…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          {q && (
            <button
              onClick={() => { setQ(""); setVerdict(null); setSuggestions([]); }}
              style={{ color: "var(--muted)", background: "none", border: "none", cursor: "pointer", padding: 0 }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 6 6 18M6 6l12 12" />
              </svg>
            </button>
          )}
          <button
            onClick={onClose}
            style={{ padding: "4px 10px", fontSize: "12px", color: "var(--muted)", background: "var(--surface-2)", border: "1px solid var(--border)", borderRadius: "5px", cursor: "pointer", flexShrink: 0 }}
          >
            ESC
          </button>
        </div>

        {suggestions.length > 0 && (
          <div className="card" style={{ padding: "6px", marginBottom: "10px" }}>
            {suggestions.map((s) => (
              <button
                key={`${s.title}-${s.release_year}`}
                onClick={() => pickFilm(s.title)}
                style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  width: "100%", padding: "10px 12px", background: "none", border: "none",
                  borderRadius: "6px", cursor: "pointer", textAlign: "left",
                  color: "var(--text)", fontSize: "14px",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-2)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "none")}
              >
                <span style={{ fontWeight: 500 }}>{s.title}</span>
                <span style={{ color: "var(--muted)", fontSize: "12px", fontFamily: "var(--font-mono)" }}>
                  {s.release_year}
                </span>
              </button>
            ))}
          </div>
        )}

        {loading && (
          <div className="card" style={{ textAlign: "center", color: "var(--muted)", fontSize: "13px" }}>
            Loading verdict…
          </div>
        )}

        {verdict && !loading && (
          <div className="verdict-card">
            <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "16px", gap: "12px" }}>
              <div>
                <div style={{ fontSize: "22px", fontWeight: 700, fontFamily: "var(--font-display)", marginBottom: "4px" }}>
                  {verdict.title}
                </div>
                <div style={{ fontSize: "13px", color: "var(--muted)" }}>
                  {verdict.release_year} &ensp;·&ensp; {verdict.primary_genre}
                </div>
              </div>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "6px", flexShrink: 0 }}>
                {outcomeMeta && (
                  <span className={`badge ${outcomeMeta.cls}`}>
                    {outcomeMeta.label}
                  </span>
                )}
                {verdict.won_oscar && (
                  <span className="badge badge-oscar">
                    {verdict.oscar_wins ? `${verdict.oscar_wins}× Oscar` : "Oscar Winner"}
                  </span>
                )}
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px", marginBottom: "16px" }}>
              {[
                { label: "Composite", val: score(verdict.composite_score) },
                { label: "RT Score", val: score(verdict.rt_score) + (verdict.rt_score != null ? "%" : "") },
                { label: "Audience", val: score(verdict.tmdb_rating, 10) },
                { label: "ROI", val: verdict.roi_ratio != null ? `${verdict.roi_ratio.toFixed(1)}×` : "—" },
              ].map((item) => (
                <div
                  key={item.label}
                  style={{
                    background: "var(--surface-2)", borderRadius: "8px",
                    padding: "12px", textAlign: "center",
                  }}
                >
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: "20px", fontWeight: 700, color: "var(--text)", marginBottom: "4px" }}>
                    {item.val}
                  </div>
                  <div style={{ fontSize: "10px", color: "var(--muted)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                    {item.label}
                  </div>
                </div>
              ))}
            </div>

            {verdict.composite_score && (
              <div style={{ marginTop: "4px" }}>
                {[
                  { label: "Composite Score", val: verdict.composite_score },
                  { label: "Rotten Tomatoes", val: verdict.rt_score },
                  { label: "Audience (×10)", val: verdict.tmdb_rating != null ? verdict.tmdb_rating * 10 : null },
                ].map((bar) => bar.val != null && (
                  <div key={bar.label} className="score-bar-row">
                    <span className="score-bar-label">{bar.label}</span>
                    <div className="score-bar-track">
                      <div
                        className="score-bar-fill"
                        style={{ width: `${Math.min(bar.val, 100)}%` }}
                      />
                    </div>
                    <span className="score-bar-val">{Math.round(bar.val)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {!verdict && !loading && q.length >= 2 && suggestions.length === 0 && (
          <div className="card" style={{ textAlign: "center", color: "var(--muted)", fontSize: "13px" }}>
            No films found matching &ldquo;{q}&rdquo;
          </div>
        )}
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";

interface TickerFilm {
  title: string;
  popularity: number;
  status: string;
}

export default function Ticker() {
  const [films, setFilms] = useState<TickerFilm[]>([]);

  useEffect(() => {
    fetch("/api/ticker")
      .then((r) => r.json())
      .then((d) => setFilms(d.films ?? []))
      .catch(() => {});
  }, []);

  if (!films.length) return null;

  const items = [...films, ...films];

  return (
    <div
      className="ticker-wrap"
      style={{ marginTop: "60px" }}
    >
      <div
        style={{
          flexShrink: 0,
          padding: "0 16px",
          fontSize: "10px",
          fontWeight: 700,
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          color: "var(--accent)",
          whiteSpace: "nowrap",
          borderRight: "1px solid var(--border)",
          marginRight: "20px",
          height: "100%",
          display: "flex",
          alignItems: "center",
        }}
      >
        PULSE
      </div>
      <div className="ticker-track" style={{ flex: 1 }}>
        {items.map((f, i) => (
          <span
            key={i}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "10px",
              paddingRight: "48px",
              fontSize: "12px",
              color: "var(--muted)",
              fontFamily: "var(--font-mono)",
            }}
          >
            <span
              style={{
                width: "5px",
                height: "5px",
                borderRadius: "50%",
                background: "var(--accent)",
                display: "inline-block",
                opacity: 0.5,
                flexShrink: 0,
              }}
            />
            <span style={{ color: "var(--text)", fontWeight: 500 }}>
              {f.title}
            </span>
            <span style={{ color: "var(--accent)", fontWeight: 600 }}>
              {f.popularity.toFixed(0)}
            </span>
            <span
              style={{
                fontSize: "10px",
                padding: "1px 6px",
                borderRadius: "3px",
                background: "var(--surface-2)",
                color: "var(--muted)",
                letterSpacing: "0.05em",
              }}
            >
              {f.status}
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}

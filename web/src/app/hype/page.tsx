"use client";

import { useEffect, useState } from "react";
import HypeScatterClient from "@/components/charts/hype-scatter-client";

type ScatterPoint = { title: string; release_year: number; primary_genre: string; trailer_views: number; roi_ratio: number; composite_score: number; outcome_label: string };
type CountRow = { outcome_label: string; films: number; avg_roi: number; avg_views: number };
type HypeFilm = { title: string; release_year: number; trailer_views: number; roi_ratio: number };

export default function HypePage() {
  const [scatter, setScatter] = useState<ScatterPoint[]>([]);
  const [counts, setCounts] = useState<CountRow[]>([]);
  const [overhyped, setOverhyped] = useState<HypeFilm[]>([]);
  const [gems, setGems] = useState<HypeFilm[]>([]);

  useEffect(() => {
    fetch("/api/hype")
      .then((r) => r.json())
      .then((d) => {
        setScatter(d.scatter);
        setCounts(d.counts);
        setOverhyped(d.overhyped);
        setGems(d.gems);
      });
  }, []);

  const countMap = Object.fromEntries(counts.map((c) => [c.outcome_label, c.films]));

  return (
    <div className="page-wrap">
      <div className="hero">
        <div className="eyebrow">Hype · Reality · Returns</div>
        <h1>
          Did the <em>hype</em><br />
          deliver?
        </h1>
        <p>
          Trailer views against actual box-office ROI. High buzz that paid off,
          high buzz that didn&rsquo;t, and the quiet films that surprised everyone.
        </p>
      </div>

      <div className="kpi-grid">
        {[
          { label: "Delivered", val: countMap["Delivered"] ?? 0, cls: "badge-delivered" },
          { label: "Hidden gems", val: countMap["Hidden gem"] ?? 0, cls: "badge-gem" },
          { label: "Overhyped", val: countMap["Overhyped"] ?? 0, cls: "badge-overhyped" },
          { label: "Overlooked", val: countMap["Overlooked"] ?? 0, cls: "badge-overlooked" },
        ].map((k) => (
          <div className="kpi-card" key={k.label}>
            <div className="kpi-value">{k.val}</div>
            <div className="kpi-label">{k.label}</div>
          </div>
        ))}
      </div>

      <div className="divider" />

      <div className="section-head">
        <h2>Trailer buzz vs box-office return</h2>
        <p>
          Trailer views (log scale) against ROI. Top-right = delivered on the
          hype. Bottom-right = spent the marketing budget, lost the gamble.
        </p>
      </div>

      <div className="chart-card">
        <HypeScatterClient data={scatter} />
        <div className="chart-legend" style={{ marginTop: "16px" }}>
          {[
            { color: "#10B981", label: "Delivered — big buzz, strong return" },
            { color: "#00D4FF", label: "Hidden gem — quiet buzz, strong return" },
            { color: "#FF4560", label: "Overhyped — big buzz, weak return" },
            { color: "#64748B", label: "Overlooked — quiet buzz, weak return" },
          ].map((l) => (
            <span key={l.label} className="chart-legend-item">
              <span className="legend-dot" style={{ background: l.color }} />
              {l.label}
            </span>
          ))}
        </div>
      </div>

      <div className="divider" />

      <div className="page-grid-equal">
        <div>
          <div className="section-head">
            <h2>Overhyped</h2>
            <p>Huge trailer buzz, underwhelming returns.</p>
          </div>
          <div className="card" style={{ padding: 0 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th className="r">Year</th>
                  <th className="r">Views</th>
                  <th className="r">ROI</th>
                </tr>
              </thead>
              <tbody>
                {overhyped.map((f) => (
                  <tr key={f.title}>
                    <td className="title-col">{f.title}</td>
                    <td className="r mono-val" style={{ color: "var(--muted)" }}>
                      {f.release_year}
                    </td>
                    <td className="r mono-val" style={{ color: "var(--muted)" }}>
                      {f.trailer_views >= 1e6
                        ? `${(f.trailer_views / 1e6).toFixed(0)}M`
                        : f.trailer_views?.toLocaleString()}
                    </td>
                    <td className="r">
                      <span className="badge badge-overhyped">
                        {f.roi_ratio.toFixed(1)}×
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <div className="section-head">
            <h2>Hidden gems</h2>
            <p>Modest buzz, outsized returns.</p>
          </div>
          <div className="card" style={{ padding: 0 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th className="r">Year</th>
                  <th className="r">Views</th>
                  <th className="r">ROI</th>
                </tr>
              </thead>
              <tbody>
                {gems.map((f) => (
                  <tr key={f.title}>
                    <td className="title-col">{f.title}</td>
                    <td className="r mono-val" style={{ color: "var(--muted)" }}>
                      {f.release_year}
                    </td>
                    <td className="r mono-val" style={{ color: "var(--muted)" }}>
                      {f.trailer_views >= 1e6
                        ? `${(f.trailer_views / 1e6).toFixed(0)}M`
                        : f.trailer_views?.toLocaleString()}
                    </td>
                    <td className="r">
                      <span className="badge badge-gem">
                        {f.roi_ratio.toFixed(1)}×
                      </span>
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

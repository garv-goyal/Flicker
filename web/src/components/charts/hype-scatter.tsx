"use client";

import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface DataPoint {
  title: string;
  release_year: number;
  primary_genre: string;
  trailer_views: number;
  roi_ratio: number;
  composite_score: number;
  outcome_label: string;
}

const COLOR: Record<string, string> = {
  Delivered:    "#10B981",
  "Hidden gem": "#00D4FF",
  Overhyped:    "#FF4560",
  Overlooked:   "#64748B",
};

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload as DataPoint;
  return (
    <div className="card-sm" style={{ minWidth: "180px", fontSize: "12px" }}>
      <div style={{ fontWeight: 600, fontSize: "13px", marginBottom: "6px" }}>{d.title}</div>
      <div style={{ color: "var(--muted)", marginBottom: "2px" }}>{d.release_year} · {d.primary_genre}</div>
      <div style={{ color: "var(--muted)", marginBottom: "2px" }}>
        Trailer views: <span style={{ color: "var(--text)", fontFamily: "var(--font-mono)" }}>{d.trailer_views?.toLocaleString()}</span>
      </div>
      <div style={{ color: "var(--muted)" }}>
        ROI: <span style={{ color: "var(--accent)", fontFamily: "var(--font-mono)" }}>{d.roi_ratio?.toFixed(1)}×</span>
      </div>
    </div>
  );
};

export default function HypeScatterChart({ data }: { data: DataPoint[] }) {
  const outcomes = ["Delivered", "Hidden gem", "Overhyped", "Overlooked"];
  const groups = outcomes.map((label) => ({
    label,
    color: COLOR[label],
    data: data.filter((d) => d.outcome_label === label),
  }));

  return (
    <ResponsiveContainer width="100%" height={360}>
      <ScatterChart>
        <XAxis
          dataKey="trailer_views"
          type="number"
          scale="log"
          domain={["auto", "auto"]}
          tick={{ fill: "var(--muted)", fontSize: 11, fontFamily: "var(--font-mono)" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => v >= 1e9 ? `${(v/1e9).toFixed(1)}B` : v >= 1e6 ? `${(v/1e6).toFixed(0)}M` : `${(v/1e3).toFixed(0)}K`}
          name="Trailer views"
        />
        <YAxis
          dataKey="roi_ratio"
          type="number"
          scale="log"
          domain={["auto", "auto"]}
          tick={{ fill: "var(--muted)", fontSize: 11, fontFamily: "var(--font-mono)" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `${v}×`}
          width={36}
          name="ROI"
        />
        <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: "3 3", stroke: "var(--border-2)" }} />
        {groups.map((g) => (
          <Scatter
            key={g.label}
            name={g.label}
            data={g.data}
            fill={g.color}
            fillOpacity={0.75}
          />
        ))}
      </ScatterChart>
    </ResponsiveContainer>
  );
}

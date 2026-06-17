"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

interface DataPoint {
  release_decade: number;
  film_count: number;
  avg_roi: number;
  median_roi: number;
  profitable_pct: number;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload as DataPoint;
  return (
    <div className="card-sm" style={{ minWidth: "160px", fontSize: "12px" }}>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: "14px", fontWeight: 700, marginBottom: "8px" }}>
        {label}
      </div>
      <div style={{ color: "var(--muted)", marginBottom: "3px" }}>
        Median ROI: <span style={{ color: "var(--accent)", fontFamily: "var(--font-mono)" }}>{d.median_roi}×</span>
      </div>
      <div style={{ color: "var(--muted)", marginBottom: "3px" }}>
        Films: <span style={{ color: "var(--text)", fontFamily: "var(--font-mono)" }}>{d.film_count}</span>
      </div>
      <div style={{ color: "var(--muted)" }}>
        Profitable: <span style={{ color: "var(--text)", fontFamily: "var(--font-mono)" }}>{d.profitable_pct}%</span>
      </div>
    </div>
  );
};

export default function RoiDecadeChart({ data }: { data: DataPoint[] }) {
  const formatted = data.map((d) => ({
    ...d,
    decade: `${d.release_decade}s`,
  }));

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={formatted} barCategoryGap="30%">
        <XAxis
          dataKey="decade"
          tick={{ fill: "var(--muted)", fontSize: 12, fontFamily: "var(--font-mono)" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: "var(--muted)", fontSize: 11, fontFamily: "var(--font-mono)" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `${v}×`}
          width={36}
        />
        <Tooltip
          content={<CustomTooltip />}
          cursor={{ fill: "rgba(255,255,255,0.03)" }}
        />
        <Bar dataKey="median_roi" radius={[4, 4, 0, 0]}>
          {formatted.map((_, i) => (
            <Cell
              key={i}
              fill="var(--accent)"
              fillOpacity={0.7 + (i / formatted.length) * 0.3}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

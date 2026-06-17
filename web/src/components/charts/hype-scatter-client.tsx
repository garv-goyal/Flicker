"use client";

import HypeScatterChart from "./hype-scatter";

interface DataPoint {
  title: string;
  release_year: number;
  primary_genre: string;
  trailer_views: number;
  roi_ratio: number;
  composite_score: number;
  outcome_label: string;
}

export default function HypeScatterClient({ data }: { data: DataPoint[] }) {
  return <HypeScatterChart data={data} />;
}

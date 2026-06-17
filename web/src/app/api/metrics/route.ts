import { NextResponse } from "next/server";
import { headlineMetrics, roiSummary } from "@/lib/queries";

export const dynamic = "force-dynamic";
export const revalidate = 3600;
export const maxDuration = 60;

export async function GET() {
  try {
    const [metrics, roi] = await Promise.all([headlineMetrics(), roiSummary()]);
    return NextResponse.json({ metrics, roi });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}

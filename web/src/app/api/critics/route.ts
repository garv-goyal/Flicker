import { NextResponse } from "next/server";
import {
  criticalSummary,
  bestReviewed,
  audienceOverCritics,
  criticsOverAudience,
} from "@/lib/queries";

export const revalidate = 3600;
export const maxDuration = 60;

export async function GET() {
  try {
    const [summary, best, audienceFav, criticsFav] = await Promise.all([
      criticalSummary(),
      bestReviewed(12),
      audienceOverCritics(7),
      criticsOverAudience(7),
    ]);
    return NextResponse.json({ summary, best, audienceFav, criticsFav });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}

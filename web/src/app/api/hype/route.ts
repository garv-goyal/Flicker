import { NextResponse } from "next/server";
import { hypeScatter, hypeCounts, hypeExamples } from "@/lib/queries";

export const revalidate = 3600;

export async function GET() {
  try {
    const [scatter, counts, overhyped, gems] = await Promise.all([
      hypeScatter(),
      hypeCounts(),
      hypeExamples("Overhyped", 6),
      hypeExamples("Hidden gem", 6),
    ]);
    return NextResponse.json({ scatter, counts, overhyped, gems });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}

import { NextResponse } from "next/server";
import { genreLeaderboard } from "@/lib/queries";

export const revalidate = 3600;

export async function GET() {
  try {
    const genres = await genreLeaderboard(8);
    return NextResponse.json({ genres });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}

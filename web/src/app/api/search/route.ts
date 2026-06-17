import { NextRequest, NextResponse } from "next/server";
import { searchFilms } from "@/lib/queries";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams.get("q") ?? "";
  if (q.length < 2) return NextResponse.json({ results: [] });
  try {
    const results = await searchFilms(q);
    return NextResponse.json({ results });
  } catch (e) {
    return NextResponse.json({ results: [], error: String(e) });
  }
}

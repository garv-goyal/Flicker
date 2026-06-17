import { NextResponse } from "next/server";
import { tickerFilms } from "@/lib/queries";

export const revalidate = 300;
export const maxDuration = 60;

export async function GET() {
  try {
    const films = await tickerFilms();
    return NextResponse.json({ films });
  } catch (e) {
    return NextResponse.json({ films: [], error: String(e) });
  }
}

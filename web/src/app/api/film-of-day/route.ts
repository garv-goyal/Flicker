import { NextResponse } from "next/server";
import { filmOfTheDay } from "@/lib/queries";

export const revalidate = 3600;
export const maxDuration = 60;

export async function GET() {
  try {
    const films = await filmOfTheDay();
    if (!films.length) return NextResponse.json({ film: null });

    const dayOfYear = Math.floor(
      (Date.now() - new Date(new Date().getFullYear(), 0, 0).getTime()) /
        86400000
    );
    const film = films[dayOfYear % films.length];
    return NextResponse.json({ film });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}

import { NextRequest, NextResponse } from "next/server";
import { discoverByMood, type Mood } from "@/lib/queries";

export const maxDuration = 60;

const VALID_MOODS: Mood[] = [
  "prestige",
  "blockbuster",
  "feel-good",
  "mind-bending",
  "hidden-gem",
  "dark-slow-burn",
];

export async function GET(req: NextRequest) {
  const mood = req.nextUrl.searchParams.get("mood") as Mood;
  if (!VALID_MOODS.includes(mood)) {
    return NextResponse.json({ error: "Invalid mood" }, { status: 400 });
  }
  try {
    const films = await discoverByMood(mood, 24);
    return NextResponse.json({ films });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}

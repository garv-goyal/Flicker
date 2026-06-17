import { NextResponse } from "next/server";
import { roiByDecade, topRoiFilms } from "@/lib/queries";

export const dynamic = "force-dynamic";
export const revalidate = 3600;
export const maxDuration = 60;

export async function GET() {
  try {
    const [decade, top] = await Promise.all([roiByDecade(), topRoiFilms(10)]);
    return NextResponse.json({ decade, top });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}

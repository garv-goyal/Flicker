import { NextRequest, NextResponse } from "next/server";
import { filmVerdict } from "@/lib/queries";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const title = req.nextUrl.searchParams.get("title") ?? "";
  if (!title) return NextResponse.json({ film: null });
  try {
    const film = await filmVerdict(title);
    return NextResponse.json({ film });
  } catch (e) {
    return NextResponse.json({ film: null, error: String(e) });
  }
}

import { NextRequest, NextResponse } from "next/server";
import { execute, query } from "@/lib/db";

export const maxDuration = 60;

const DDL = `
  CREATE SCHEMA IF NOT EXISTS bronze;
  CREATE TABLE IF NOT EXISTS bronze.newsletter_subscribers (
    email         VARCHAR PRIMARY KEY,
    genre_pref    VARCHAR,
    subscribed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    active        BOOLEAN     NOT NULL DEFAULT true
  )
`;

function isValidEmail(s: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s);
}

export async function POST(req: NextRequest) {
  try {
    const { email, genre } = await req.json();
    if (!email || !isValidEmail(email)) {
      return NextResponse.json({ error: "Invalid email address." }, { status: 400 });
    }

    await execute(DDL);

    const existing = await query<{ active: boolean; genre_pref: string | null }>(
      `SELECT active, genre_pref FROM bronze.newsletter_subscribers WHERE email = '${email.replace(/'/g, "''")}'`
    );

    const genreVal = genre ? `'${String(genre).replace(/'/g, "''")}'` : "NULL";

    if (existing.length > 0) {
      const { active, genre_pref } = existing[0];
      if (active && genre_pref === (genre ?? null)) {
        return NextResponse.json({ result: "exists" });
      }
      await execute(
        `UPDATE bronze.newsletter_subscribers SET active=true, genre_pref=${genreVal} WHERE email='${email.replace(/'/g, "''")}'`
      );
      return NextResponse.json({ result: "updated" });
    }

    await execute(
      `INSERT INTO bronze.newsletter_subscribers (email, genre_pref) VALUES ('${email.replace(/'/g, "''")}', ${genreVal})`
    );
    return NextResponse.json({ result: "new" });
  } catch (err) {
    console.error("[newsletter/subscribe POST]", err);
    return NextResponse.json({ error: "Server error." }, { status: 500 });
  }
}

export async function DELETE(req: NextRequest) {
  try {
    const { email } = await req.json();
    if (!email || !isValidEmail(email)) {
      return NextResponse.json({ error: "Invalid email." }, { status: 400 });
    }
    await execute(
      `UPDATE bronze.newsletter_subscribers SET active=false WHERE email='${email.replace(/'/g, "''")}'`
    );
    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error("[newsletter/subscribe DELETE]", err);
    return NextResponse.json({ error: "Server error." }, { status: 500 });
  }
}

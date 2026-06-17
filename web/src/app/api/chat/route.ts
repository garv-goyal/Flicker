import { NextRequest, NextResponse } from "next/server";
import { GoogleGenAI } from "@google/genai";
import { query } from "@/lib/db";

export const maxDuration = 60;

const SCHEMA = `
Available DuckDB tables (Gold layer, always prefix schema):

gold.mart_film_lifecycle_current — films currently in theaters
  tmdb_id INT, title TEXT, status TEXT ('Now Playing'|'Holdover'|'Leaving Soon'),
  popularity DOUBLE, vote_count INT, vote_average DOUBLE,
  primary_genre TEXT, release_year INT, last_change_ts TIMESTAMP

gold.fact_title_performance — financial + critical metrics per film
  title_key TEXT, budget_usd DOUBLE, revenue_usd DOUBLE,
  roi_ratio DOUBLE, is_profitable BOOLEAN,
  tmdb_rating DOUBLE, tmdb_vote_count INT,
  rt_score DOUBLE, metacritic_score DOUBLE, imdb_rating DOUBLE,
  composite_score DOUBLE, trailer_views INT, trailer_engagement DOUBLE,
  won_oscar BOOLEAN, oscar_wins INT, total_award_wins INT, popularity_score DOUBLE

gold.dim_titles — title dimension (join key)
  title_key TEXT, tmdb_id INT, title TEXT,
  release_date DATE, release_year INT, release_decade INT,
  primary_genre TEXT, runtime_minutes INT,
  original_language TEXT, is_franchise BOOLEAN

gold.mart_hype_vs_revenue — trailer hype vs box-office
  title TEXT, release_year INT, primary_genre TEXT,
  budget_usd DOUBLE, revenue_usd DOUBLE, roi_ratio DOUBLE,
  trailer_views INT, composite_score DOUBLE,
  outcome_label TEXT ('Overhyped'|'Hidden gem'|'Delivered'|'Overlooked')

gold.mart_roi_by_decade — ROI per decade (pre-aggregated, no GROUP BY)
  release_decade INT, film_count INT, avg_roi DOUBLE, median_roi DOUBLE, profitable_pct DOUBLE

Join keys:
  dim_titles.title_key = fact_title_performance.title_key
  dim_titles.tmdb_id   = mart_film_lifecycle_current.tmdb_id
`;

const SYSTEM = `You are Flicker's data assistant. Users ask natural-language questions about film analytics.

${SCHEMA}

Rules:
1. Answer in 1–3 clear sentences. Bold film titles and key stats with **text**.
2. If data is needed, emit exactly one DuckDB SQL query in a \`\`\`sql fence.
   - Always prefix tables with schema (gold.dim_titles, not just dim_titles).
   - LIMIT to 10 rows unless the user asks for more.
   - Only SELECT queries — never DDL or DML.
3. Tables prefixed with mart_ are pre-aggregated — never add GROUP BY to them.
4. If the question needs no data, skip the SQL block.
5. Be concise and conversational.
6. Never mention SQL, queries, tables, schemas, or "the database" in your reply to
   the user — talk about films and data, not how it's stored or fetched.`;

function extractSql(text: string): string | null {
  const m = text.match(/```sql\s*([\s\S]*?)\s*```/i);
  return m ? m[1].trim() : null;
}

function money(v: unknown): string {
  const n = Number(v);
  if (!n) return "—";
  if (n >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `$${(n / 1e6).toFixed(0)}M`;
  return `$${n.toLocaleString()}`;
}

function fmtCell(col: string, val: unknown): string {
  if (val === null || val === undefined) return "—";
  const c = col.toLowerCase();
  if (c.includes("roi")) return `${Number(val).toFixed(1)}×`;
  if (c.includes("budget") || c.includes("revenue")) return money(val);
  if (c.includes("rt_score") || c.includes("critic")) return `${Number(val).toFixed(0)}%`;
  if (c.includes("pct") || c.includes("percent")) return `${Number(val).toFixed(1)}%`;
  if (typeof val === "boolean") return val ? "Yes" : "No";
  if (typeof val === "number") return val >= 1000 ? val.toLocaleString() : val % 1 === 0 ? String(val) : val.toFixed(1);
  return String(val);
}

interface ChatMessage {
  role: string;
  content: string;
}

export async function POST(req: NextRequest) {
  try {
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      return NextResponse.json({ error: "Assistant is not available right now." }, { status: 500 });
    }

    const { messages, question } = (await req.json()) as { messages: ChatMessage[]; question: string };

    const ai = new GoogleGenAI({ apiKey });

    const history = messages.map((m) => ({
      role: m.role === "user" ? "user" : "model",
      parts: [{ text: m.content }],
    }));

    const chat = ai.chats.create({
      model: "gemini-2.5-flash",
      history,
      config: {
        systemInstruction: SYSTEM,
        maxOutputTokens: 600,
        thinkingConfig: { thinkingBudget: 0 },
      },
    });

    const response = await chat.sendMessage({ message: question });
    const raw = response.text ?? "";

    const sql = extractSql(raw);
    const plain = raw.replace(/```sql[\s\S]*?```/gi, "").trim();

    let tableHtml = "";
    if (sql) {
      try {
        const rows = await query<Record<string, unknown>>(sql);
        if (rows.length > 0) {
          const cols = Object.keys(rows[0]);
          const header = cols.map((c) => `<th>${c.replace(/_/g, " ")}</th>`).join("");
          const body = rows
            .map(
              (row) =>
                `<tr>${cols.map((c) => `<td>${fmtCell(c, row[c])}</td>`).join("")}</tr>`
            )
            .join("");
          tableHtml = `<table><thead><tr>${header}</tr></thead><tbody>${body}</tbody></table><div class="chat-row-count">${rows.length} row${rows.length !== 1 ? "s" : ""}</div>`;
        } else {
          tableHtml = `<div class="chat-row-count">0 rows</div>`;
        }
      } catch (e) {
        console.error("[chat] query failed", e);
        tableHtml = `<div class="chat-error-note">Couldn&rsquo;t load that data right now.</div>`;
      }
    }

    return NextResponse.json({ plain, tableHtml });
  } catch (err) {
    console.error("[chat]", err);
    return NextResponse.json({ error: "Failed to get response." }, { status: 500 });
  }
}

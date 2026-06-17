import path from "path";
import { DuckDBInstance } from "@duckdb/node-api";

type DuckDBConn = Awaited<ReturnType<Awaited<ReturnType<typeof DuckDBInstance.create>>["connect"]>>;

let _instance: Awaited<ReturnType<typeof DuckDBInstance.create>> | null = null;
let _conn: DuckDBConn | null = null;

function deepConvert(value: unknown): unknown {
  if (typeof value === "bigint") return Number(value);
  if (Array.isArray(value)) return value.map(deepConvert);
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([k, v]) => [
        k,
        deepConvert(v),
      ])
    );
  }
  return value;
}

async function connect(): Promise<DuckDBConn> {
  const useMd = process.env.FLICKER_USE_MOTHERDUCK === "true";
  let dbPath: string;

  if (useMd) {
    const token = process.env.MOTHERDUCK_TOKEN;
    if (!token) throw new Error("MOTHERDUCK_TOKEN required");
    const db = process.env.MOTHERDUCK_DATABASE ?? "flicker";
    dbPath = `md:${db}?motherduck_token=${token}`;
  } else {
    const defaultPath = path.resolve(
      path.dirname(new URL(import.meta.url).pathname),
      "../../../flicker.duckdb"
    );
    dbPath = process.env.FLICKER_DB_PATH ?? defaultPath;
  }

  _instance = await DuckDBInstance.create(dbPath, {});
  return _instance.connect();
}

// MotherDuck cold connections occasionally fail/timeout on serverless cold
// starts — retry a few times with backoff before giving up.
async function getConn(forceNew = false): Promise<DuckDBConn> {
  if (_conn && !forceNew) return _conn;

  let lastErr: unknown;
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      _conn = await connect();
      return _conn;
    } catch (e) {
      lastErr = e;
      if (attempt < 2) await new Promise((r) => setTimeout(r, 300 * (attempt + 1)));
    }
  }
  throw lastErr;
}

// If a query fails on a cached connection (e.g. a dropped/stale connection),
// reconnect once and retry before surfacing the error.
async function withConn<T>(fn: (conn: DuckDBConn) => Promise<T>): Promise<T> {
  try {
    return await fn(await getConn());
  } catch {
    _conn = null;
    return fn(await getConn(true));
  }
}

export async function query<T = Record<string, unknown>>(
  sql: string
): Promise<T[]> {
  return withConn(async (conn) => {
    const stmt = await conn.prepare(sql);
    const result = await stmt.runAndReadAll();
    await result.readAll();
    const rows = result.getRowObjectsJS() as unknown[];
    return deepConvert(rows) as T[];
  });
}

export async function queryOne<T = Record<string, unknown>>(
  sql: string
): Promise<T | null> {
  const rows = await query<T>(sql);
  return rows[0] ?? null;
}

export async function execute(sql: string): Promise<void> {
  await withConn(async (conn) => {
    const stmt = await conn.prepare(sql);
    await stmt.run();
  });
}

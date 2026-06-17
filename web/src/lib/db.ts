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

async function getConn() {
  if (_conn) return _conn;

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
  _conn = await _instance.connect();
  return _conn;
}

export async function query<T = Record<string, unknown>>(
  sql: string
): Promise<T[]> {
  const conn = await getConn();
  const stmt = await conn.prepare(sql);
  const result = await stmt.runAndReadAll();
  await result.readAll();
  const rows = result.getRowObjectsJS() as unknown[];
  return deepConvert(rows) as T[];
}

export async function queryOne<T = Record<string, unknown>>(
  sql: string
): Promise<T | null> {
  const rows = await query<T>(sql);
  return rows[0] ?? null;
}

export async function execute(sql: string): Promise<void> {
  const conn = await getConn();
  const stmt = await conn.prepare(sql);
  await stmt.run();
}

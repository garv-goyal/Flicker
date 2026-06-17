import path from "path";
import { DuckDBInstance } from "@duckdb/node-api";

// Vercel's Lambda runtime doesn't set HOME, but DuckDB needs one to resolve
// its config/extension directory — anything reading process.env.HOME
// directly (e.g. the MotherDuck extension) needs this set too.
if (!process.env.HOME) process.env.HOME = "/tmp";

type DuckDBConn = Awaited<ReturnType<Awaited<ReturnType<typeof DuckDBInstance.create>>["connect"]>>;

let _connPromise: Promise<DuckDBConn> | null = null;
// Serializes all query execution onto the single shared connection — the
// native DuckDB binding isn't safe under concurrent calls on one connection,
// and concurrent first-connects on cold start crashed the Vercel function.
let _queue: Promise<unknown> = Promise.resolve();

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

  // Vercel's Lambda runtime doesn't set HOME, and DuckDB needs a writable
  // home directory for extension/config state — /tmp always exists there.
  const instance = await DuckDBInstance.create(dbPath, {
    home_directory: process.env.HOME || "/tmp",
  });
  return instance.connect();
}

async function connectWithRetry(): Promise<DuckDBConn> {
  let lastErr: unknown;
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      return await connect();
    } catch (e) {
      lastErr = e;
      if (attempt < 2) await new Promise((r) => setTimeout(r, 300 * (attempt + 1)));
    }
  }
  throw lastErr;
}

// Caches the in-flight connection *promise* (not just the resolved value) so
// concurrent callers on a cold start all await one connect attempt instead
// of each racing to open a separate connection.
function getConn(forceNew = false): Promise<DuckDBConn> {
  if (forceNew) _connPromise = null;
  if (!_connPromise) {
    _connPromise = connectWithRetry();
    _connPromise.catch(() => {
      _connPromise = null;
    });
  }
  return _connPromise;
}

async function withConn<T>(fn: (conn: DuckDBConn) => Promise<T>): Promise<T> {
  const run = _queue.then(async () => {
    try {
      return await fn(await getConn());
    } catch {
      return fn(await getConn(true));
    }
  });
  _queue = run.catch(() => {});
  return run as Promise<T>;
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

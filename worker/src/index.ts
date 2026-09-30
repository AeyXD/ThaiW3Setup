// Receives problem reports from ThaiW3Setup (no login for users) and stores them in R2.
// POST /report        plain-text report, returns {"id": "..."}
// GET  /              list of reports (admin, HTTP Basic auth with ADMIN_PASSWORD)
// GET  /r/<key>       one report as text (admin)

const MAX_BYTES = 256 * 1024;
const MAGIC = "ThaiW3Setup report";
const PREFIX = "reports/";
const LIST_LIMIT = 300;

export default {
  async fetch(request, env): Promise<Response> {
    const url = new URL(request.url);
    try {
      if (url.pathname === "/report") {
        return request.method === "POST" ? await receive(request, env) : text("method not allowed", 405);
      }
      if (request.method !== "GET") {
        return text("method not allowed", 405);
      }
      if (!(await authorized(request, env))) {
        return new Response("login required", {
          status: 401,
          headers: { "WWW-Authenticate": 'Basic realm="ThaiW3Setup reports", charset="UTF-8"' },
        });
      }
      if (url.pathname === "/") {
        return await listReports(env);
      }
      if (url.pathname.startsWith("/r/")) {
        return await showReport(env, decodeURIComponent(url.pathname.slice(3)));
      }
      return text("not found", 404);
    } catch (err) {
      console.error(JSON.stringify({ message: "unhandled", error: String(err), path: url.pathname }));
      return text("internal error", 500);
    }
  },
} satisfies ExportedHandler<Env>;

async function receive(request: Request, env: Env): Promise<Response> {
  const ip = request.headers.get("cf-connecting-ip") ?? "unknown";
  const { success } = await env.REPORT_LIMITER.limit({ key: ip });
  if (!success) {
    return json({ error: "too many reports, try again in a minute" }, 429);
  }
  const declared = Number(request.headers.get("content-length") ?? "0");
  if (declared > MAX_BYTES) {
    return json({ error: "report too large" }, 413);
  }
  const body = await readLimited(request, MAX_BYTES);
  if (body === null) {
    return json({ error: "report too large" }, 413);
  }
  const report = new TextDecoder().decode(body);
  if (!report.startsWith(MAGIC)) {
    return json({ error: "not a ThaiW3Setup report" }, 400);
  }

  const now = new Date();
  const id = crypto.randomUUID().slice(0, 8);
  const stamp = now.toISOString();
  const key = `${PREFIX}${stamp.slice(0, 10)}/${stamp.slice(11, 19).replaceAll(":", "")}-${id}.txt`;
  const country = typeof request.cf?.country === "string" ? request.cf.country : "";
  await env.REPORTS.put(key, report, {
    httpMetadata: { contentType: "text/plain; charset=utf-8" },
    customMetadata: {
      id,
      app: field(report, "app"),
      game: field(report, "game version"),
      country,
    },
  });
  console.log(JSON.stringify({ message: "report stored", key, bytes: body.byteLength }));
  return json({ id }, 201);
}

async function readLimited(request: Request, limit: number): Promise<Uint8Array | null> {
  if (!request.body) {
    return new Uint8Array();
  }
  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    size += value.byteLength;
    if (size > limit) {
      await reader.cancel();
      return null;
    }
    chunks.push(value);
  }
  const out = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
    out.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return out;
}

function field(report: string, name: string): string {
  const line = report.split("\n", 40).find((l) => l.toLowerCase().startsWith(`${name}:`));
  return line ? line.slice(name.length + 1).trim().slice(0, 100) : "";
}

async function authorized(request: Request, env: Env): Promise<boolean> {
  const expected = env.ADMIN_PASSWORD;
  const header = request.headers.get("authorization") ?? "";
  if (!expected || !header.startsWith("Basic ")) {
    return false;
  }
  let decoded: string;
  try {
    decoded = atob(header.slice(6));
  } catch {
    return false;
  }
  const password = decoded.slice(decoded.indexOf(":") + 1);
  const encoder = new TextEncoder();
  const [a, b] = await Promise.all([
    crypto.subtle.digest("SHA-256", encoder.encode(password)),
    crypto.subtle.digest("SHA-256", encoder.encode(expected)),
  ]);
  return crypto.subtle.timingSafeEqual(a, b);
}

async function listReports(env: Env): Promise<Response> {
  const objects: R2Object[] = [];
  let cursor: string | undefined;
  do {
    const page = await env.REPORTS.list({ prefix: PREFIX, cursor, include: ["customMetadata"] });
    objects.push(...page.objects);
    cursor = page.truncated ? page.cursor : undefined;
  } while (cursor && objects.length < 5000);
  objects.sort((x, y) => (x.key < y.key ? 1 : -1));

  const rows = objects.slice(0, LIST_LIMIT).map((o) => {
    const m = o.customMetadata ?? {};
    return `<tr><td>${esc(o.uploaded.toISOString().replace("T", " ").slice(0, 19))}</td>`
      + `<td><a href="/r/${encodeURIComponent(o.key)}">${esc(m.id ?? o.key)}</a></td>`
      + `<td>${esc(m.app ?? "")}</td><td>${esc(m.game ?? "")}</td><td>${esc(m.country ?? "")}</td>`
      + `<td>${(o.size / 1024).toFixed(1)} KB</td></tr>`;
  });
  const html = `<!doctype html><meta charset="utf-8"><title>ThaiW3Setup reports</title>
<style>body{font:14px system-ui,sans-serif;margin:24px}table{border-collapse:collapse}
td,th{border:1px solid #ccc;padding:4px 8px;text-align:left}th{background:#f3f3f3}</style>
<h1>ThaiW3Setup reports</h1><p>${objects.length} reports (newest ${Math.min(objects.length, LIST_LIMIT)} shown, times in UTC)</p>
<table><tr><th>received</th><th>id</th><th>app</th><th>game</th><th>country</th><th>size</th></tr>${rows.join("")}</table>`;
  return new Response(html, { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" } });
}

async function showReport(env: Env, key: string): Promise<Response> {
  if (!key.startsWith(PREFIX)) {
    return text("not found", 404);
  }
  const obj = await env.REPORTS.get(key);
  if (!obj) {
    return text("not found", 404);
  }
  return new Response(obj.body, {
    headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
  });
}

function esc(s: string): string {
  return s.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
}

function text(body: string, status = 200): Response {
  return new Response(body, { status, headers: { "content-type": "text/plain; charset=utf-8" } });
}

function json(body: unknown, status = 200): Response {
  return Response.json(body, { status });
}

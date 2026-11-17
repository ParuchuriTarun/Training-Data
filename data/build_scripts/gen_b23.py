"""Build data/staging/claude_node_server_23.txt. Every file is written to a temporary folder and RUN with Node (v24) and the
commands shown; the real output is pasted into the answer."""
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

F = "`" * 3
OUT = Path(r"C:\Projects\Mavo\Coding 1 2B\data\staging\claude_node_server_23.txt")
NODE = shutil.which("node")
EXAMPLES = []
CLEAN_ENV = ("PORT", "NODE_ENV", "DATABASE_URL", "LOG_LEVEL", "NODE_OPTIONS")


def run_session(files, runs):
    d = Path(tempfile.mkdtemp())
    for name, content in files.items():
        p = d / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8", newline="\n")
    blocks = []
    for args, env in runs:
        e = {k: v for k, v in os.environ.items() if k not in CLEAN_ENV}
        e.update(env or {})
        p = subprocess.run([NODE] + list(args), cwd=str(d), env=e, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, encoding="utf-8", timeout=90)
        lines = ["$ " + "".join(f"{k}={v} " for k, v in (env or {}).items()) + "node " + " ".join(args)]
        body = p.stdout.replace("\r", "")
        body = re.sub(r" \(\d+(\.\d+)?ms\)", "", body)
        body = "\n".join(l.rstrip() for l in body.split("\n") if "duration_ms" not in l).strip("\n")
        if body:
            lines.append(body)
        if p.returncode:
            lines.append(f"[exit code {p.returncode}]")
        blocks.append("\n".join(lines))
    shutil.rmtree(d, ignore_errors=True)
    return "\n\n".join(blocks)


def ex(question, intro, shown, runs, after, files=None):
    real = dict(files or {})
    parts = [intro.strip()]
    for name, lang, content in shown:
        assert F not in content
        real.setdefault(name, content.strip("\n") + "\n")
        parts.append(f"`{name}`:\n\n{F}{lang}\n{content.strip(chr(10))}\n{F}")
    result = run_session(real, runs)
    parts.append(f"Running it:\n\n{F}\n{result}\n{F}")
    parts.append(after.strip())
    EXAMPLES.append((question, "\n\n".join(parts)))
    print(f"---- example {len(EXAMPLES)} ----\n{result}\n")


DEMO_HEAD = r'''
import { createApp } from "./server.mjs";

const server = createApp();
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const base = `http://127.0.0.1:${server.address().port}`;
'''

# 1 ---------------------------------------------------------------------------------------------
ex("How do I build a small JSON API with Node's built-in http module, without Express? I want routes for GET and POST and proper 404 and 405 answers.",
   "The `node:http` module is enough for a small API. The pieces are: a `send` helper that writes JSON with the right headers, a table that maps a path to its methods, and a server function that looks up the path (404 if unknown) and then the method (405 if the path exists but not for that method, with an `Allow` header that lists what is allowed). To test it without a browser, start the server on port `0` (the system picks a free port) and call it with `fetch`.",
   [("server.mjs", "javascript", r'''
import http from "node:http";

function send(res, status, data, headers = {}) {
  const body = JSON.stringify(data);
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(body),
    ...headers,
  });
  res.end(body);
}

export function createApp() {
  const items = [{ id: 1, name: "tea" }];

  const routes = {
    "/items": {
      GET: (req, res) => send(res, 200, items),
      POST: async (req, res) => {
        const chunks = [];
        for await (const chunk of req) chunks.push(chunk);
        const { name } = JSON.parse(Buffer.concat(chunks).toString("utf8"));
        const item = { id: items.length + 1, name };
        items.push(item);
        send(res, 201, item, { Location: `/items/${item.id}` });
      },
    },
  };

  return http.createServer(async (req, res) => {
    const { pathname } = new URL(req.url, "http://localhost");
    const methods = routes[pathname];
    if (!methods) return send(res, 404, { error: "not found" });

    const handler = methods[req.method];
    if (!handler) {
      return send(res, 405, { error: "method not allowed" }, { Allow: Object.keys(methods).join(", ") });
    }
    try {
      await handler(req, res);
    } catch (err) {
      send(res, 500, { error: "server error" });
    }
  });
}
'''),
    ("demo.mjs", "javascript", DEMO_HEAD + r'''
async function show(label, path, options) {
  const res = await fetch(base + path, options);
  const extra = ["allow", "location"].filter((h) => res.headers.has(h)).map((h) => `  ${h}: ${res.headers.get(h)}`);
  console.log(`${label}: ${res.status} ${await res.text()}${extra.join("")}`);
}

await show("list  ", "/items");
await show("create", "/items", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ name: "coffee" }),
});
await show("list  ", "/items");
await show("unknown", "/nope");
await show("delete", "/items", { method: "DELETE" });
server.close();
''')],
   [(["demo.mjs"], None)],
   "`404` means the path does not exist and `405` means the path exists but not for this method. The second one needs the `Allow` header, as the HTTP rules say, and clients and debugging tools use it. `Content-Length` is computed with `Buffer.byteLength`, not `string.length`, because the two differ as soon as the JSON contains a non-ASCII character such as an accented letter. Reading the body with `for await (const chunk of req)` works because the request is a stream. One weakness is left on purpose: a body that is not valid JSON would make `JSON.parse` throw and the user would get `500`, which is wrong because it is the client's mistake. The next question is about that.")

# 2 ---------------------------------------------------------------------------------------------
ex("How do I read a JSON request body safely in a plain Node HTTP server? I want 400 for bad JSON, 413 for a body that is too large and 415 for the wrong content type.",
   "Put the checks in one function that throws an error that carries an HTTP status, and let a single `catch` in the server turn it into a response. Check the content type before reading anything, count the bytes while reading so that a huge upload is stopped early instead of filling memory, and turn the `JSON.parse` failure into a `400`. Anything else that goes wrong is a real server error and stays `500`, without leaking details to the client.",
   [("server.mjs", "javascript", r'''
import http from "node:http";

export class HttpError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

export async function readJson(req, limit = 1024) {
  const type = req.headers["content-type"] ?? "";
  if (!type.startsWith("application/json")) throw new HttpError(415, "send application/json");

  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > limit) throw new HttpError(413, "body too large");
    chunks.push(chunk);
  }
  try {
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    throw new HttpError(400, "body is not valid JSON");
  }
}

function send(res, status, data, headers = {}) {
  const body = JSON.stringify(data);
  res.writeHead(status, { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(body), ...headers });
  res.end(body);
}

export function createApp() {
  return http.createServer(async (req, res) => {
    try {
      const body = await readJson(req);
      if (body.boom) throw new Error("secret internal detail");
      send(res, 200, { received: body });
    } catch (err) {
      if (err instanceof HttpError) {
        // the client may still be sending: close the connection after answering
        return send(res, err.status, { error: err.message }, { Connection: "close" });
      }
      console.error("unexpected:", err.message); // goes to the server log only
      send(res, 500, { error: "server error" });
    }
  });
}
'''),
    ("demo.mjs", "javascript", DEMO_HEAD + r'''
async function post(label, body, type = "application/json") {
  const res = await fetch(base, { method: "POST", headers: { "Content-Type": type }, body });
  console.log(`${label}: ${res.status} ${await res.text()}`);
}

await post("valid        ", JSON.stringify({ name: "ann" }));
await post("wrong type   ", "name=ann", "text/plain");
await post("broken JSON  ", '{"name": ');
await post("too large    ", JSON.stringify({ text: "x".repeat(2000) }));
await post("server bug   ", JSON.stringify({ boom: true }));
server.close();
''')],
   [(["demo.mjs"], None)],
   "The order inside `readJson` matters. The type check comes first because it costs nothing, and the size check runs for every chunk, so a client that sends several gigabytes is stopped after the first kilobyte over the limit and the rest is never kept in memory. The `Connection: close` header tells the client that the connection will not be reused, which is the safe thing to do when you answered before the whole body was read. The last line of the output shows the rule for real bugs: the log line `unexpected: secret internal detail` is for you, and the client only sees `server error`. Note that the `catch {` without a variable (optional catch binding) is valid in current Node.")

# 3 ---------------------------------------------------------------------------------------------
ex("I wrote a small Node static file server. How do I stop path traversal, so that nobody can read files outside the public folder?",
   "Never join the URL path to a folder and read the result. First decode the path, then resolve it to an absolute path, and only then check that the result is still inside the public folder. A check on the raw text for `..` is not enough, and the example shows why: the `URL` class already removes plain `../` segments, but a request for `/..%2fsecret.txt` keeps the slash encoded until you call `decodeURIComponent`, and after decoding it is a real `../`. The server below has a `guard` option so that you can see both behaviours.",
   [("static.mjs", "javascript", r'''
import http from "node:http";
import { readFile } from "node:fs/promises";
import path from "node:path";

const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json",
};

export function createStatic(root, { guard = true } = {}) {
  const base = path.resolve(root);

  return http.createServer(async (req, res) => {
    let pathname;
    try {
      pathname = decodeURIComponent(new URL(req.url, "http://localhost").pathname);
    } catch {
      res.writeHead(400).end("bad path"); // for example a lone % in the URL
      return;
    }
    if (pathname.endsWith("/")) pathname += "index.html";

    const file = path.resolve(base, "." + pathname);
    if (guard && file !== base && !file.startsWith(base + path.sep)) {
      res.writeHead(403).end("forbidden");
      return;
    }
    try {
      const data = await readFile(file);
      res.writeHead(200, {
        "Content-Type": TYPES[path.extname(file)] ?? "application/octet-stream",
        "Content-Length": data.length,
      });
      res.end(data);
    } catch (err) {
      const missing = err.code === "ENOENT" || err.code === "EISDIR";
      res.writeHead(missing ? 404 : 500).end(missing ? "not found" : "server error");
    }
  });
}
'''),
    ("demo.mjs", "javascript", r'''
import http from "node:http";
import path from "node:path";
import { createStatic } from "./static.mjs";

const root = path.join(import.meta.dirname, "public");

// fetch() would tidy the URL for us, so use a raw request to send exactly this path
function get(port, requestPath) {
  return new Promise((resolve, reject) => {
    http.get({ host: "127.0.0.1", port, path: requestPath }, (res) => {
      let body = "";
      res.on("data", (chunk) => (body += chunk));
      res.on("end", () => resolve(`${res.statusCode} ${res.headers["content-type"] ?? "-"} | ${body.trim().slice(0, 30)}`));
    }).on("error", reject);
  });
}

for (const guard of [true, false]) {
  const server = createStatic(root, { guard });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const port = server.address().port;
  console.log(`--- guard: ${guard}`);
  for (const p of ["/", "/app.css", "/missing.js", "/../secret.txt", "/..%2fsecret.txt", "/%E0%A4%A"]) {
    console.log(p.padEnd(18), await get(port, p));
  }
  server.close();
}
'''),
    ("public/index.html", "html", "<h1>Hello</h1>"),
    ("public/app.css", "css", "body { margin: 0; }"),
    ("secret.txt", "text", "do not share this file")],
   [(["demo.mjs"], None)],
   "With the guard on, the traversal attempt gets `403` and the plain `/../secret.txt` is harmless because `URL` has already turned it into `/secret.txt`, which does not exist inside `public/`. With the guard off, the `%2f` version returns the secret file, which is what a real attacker would try. The check is `file.startsWith(base + path.sep)` and not just `startsWith(base)`: a sibling folder called `public-old` also starts with the text `.../public`, and only the trailing separator tells them apart. Two more habits: read the error code before deciding the status (a missing file is `404`, a permission problem or a directory read is something else), and send a `Content-Type` yourself, because browsers refuse to apply a stylesheet that is served with the wrong type when `X-Content-Type-Options: nosniff` is set.",
   )

# 4 ---------------------------------------------------------------------------------------------
ex("My frontend on localhost:5173 gets a CORS error when it calls my Node API. How do I add CORS headers myself, including the OPTIONS preflight?",
   "CORS is the browser asking the API for permission. For a simple GET the browser sends the request and checks the `Access-Control-Allow-Origin` answer header. For anything else (a JSON body, a custom header, `PUT`, `DELETE`) it first sends a **preflight**: an `OPTIONS` request with `Origin`, `Access-Control-Request-Method` and `Access-Control-Request-Headers`. The server must answer that with `204` and the `Allow` headers, before the browser sends the real request. Also: do not answer `*` for every site if you use cookies or tokens. Keep a list of allowed origins and echo back the one that matches, with `Vary: Origin` so that caches keep the answers apart.",
   [("server.mjs", "javascript", r'''
import http from "node:http";

const ALLOWED = new Set(["http://localhost:5173"]);

export function createApp() {
  return http.createServer((req, res) => {
    const origin = req.headers.origin;
    res.setHeader("Vary", "Origin");

    if (origin && ALLOWED.has(origin)) {
      res.setHeader("Access-Control-Allow-Origin", origin);
    }

    if (req.method === "OPTIONS") {
      if (origin && ALLOWED.has(origin)) {
        res.setHeader("Access-Control-Allow-Methods", "GET, POST, DELETE");
        res.setHeader("Access-Control-Allow-Headers", req.headers["access-control-request-headers"] ?? "Content-Type");
        res.setHeader("Access-Control-Max-Age", "600"); // the browser may cache this answer for 10 minutes
      }
      res.writeHead(204).end();
      return;
    }

    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true }));
  });
}
'''),
    ("demo.mjs", "javascript", r'''
import http from "node:http";
import { createApp } from "./server.mjs";

const server = createApp();
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const port = server.address().port;

function request(label, method, headers) {
  return new Promise((resolve, reject) => {
    http.request({ host: "127.0.0.1", port, method, path: "/items", headers }, (res) => {
      res.resume();
      res.on("end", () => {
        const shown = Object.entries(res.headers)
          .filter(([name]) => name.startsWith("access-control") || name === "vary")
          .map(([name, value]) => `${name}: ${value}`);
        console.log(`${label}: ${res.statusCode}`);
        for (const line of shown) console.log("    " + line);
        resolve();
      });
    }).on("error", reject).end();
  });
}

await request("preflight, allowed site", "OPTIONS", {
  Origin: "http://localhost:5173",
  "Access-Control-Request-Method": "POST",
  "Access-Control-Request-Headers": "content-type",
});
await request("GET, allowed site      ", "GET", { Origin: "http://localhost:5173" });
await request("GET, other site        ", "GET", { Origin: "http://evil.example" });
await request("GET, no Origin header  ", "GET", {});
server.close();
''')],
   [(["demo.mjs"], None)],
   "Read the output like the browser does. For the allowed site the answers carry `access-control-allow-origin`, so the browser lets the page read the response. For `http://evil.example` the server still answers `200`, but without that header, and that is exactly what makes the browser block the page from reading it. **CORS is enforced by the browser, not by the server**: it does not protect the API from `curl` or from other servers, so it is not a replacement for authentication. A request without an `Origin` header (curl, another server) is not a CORS request at all and passes through. The most common mistake is to add the headers only to the real response and forget that the `OPTIONS` request has to be answered too: then the browser reports a CORS error even though the real handler is correct.")

# 5 ---------------------------------------------------------------------------------------------
ex("How do I write tests in Node without installing Jest? I have a small function and an async function to test.",
   "Node has a test runner built in: `node:test` for the structure (`describe`, `it`) and `node:assert/strict` for the checks. There is nothing to install and no config file. `node --test` finds files that end in `.test.mjs` or `.test.js` (and files in a `test/` folder) and runs them. The `strict` version of assert makes `assert.equal` behave like `===`, which is the one you want.",
   [("slugify.mjs", "javascript", r'''
export function slugify(text) {
  return text
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")   // drop accents: é -> e
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export async function loadTitle(fetchTitle, id) {
  if (!Number.isInteger(id) || id < 1) throw new RangeError(`bad id: ${id}`);
  const title = await fetchTitle(id);
  return slugify(title);
}
'''),
    ("slugify.test.mjs", "javascript", r'''
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { loadTitle, slugify } from "./slugify.mjs";

describe("slugify", () => {
  it("lowercases and joins words with dashes", () => {
    assert.equal(slugify("Hello World"), "hello-world");
  });

  it("removes accents", () => {
    assert.equal(slugify("Crème brûlée"), "creme-brulee");
  });

  it("collapses punctuation and trims the ends", () => {
    assert.equal(slugify("  --Rust & Node: 2026!  "), "rust-node-2026");
  });

  it("returns an empty string when nothing is left", () => {
    assert.equal(slugify("???"), "");
  });
});

describe("loadTitle", () => {
  it("slugifies what the fetch function returns", async () => {
    const fake = async (id) => `Post number ${id}`;
    assert.equal(await loadTitle(fake, 7), "post-number-7");
  });

  it("rejects an invalid id before calling the fetch function", async () => {
    let called = false;
    const fake = async () => ((called = true), "x");
    await assert.rejects(loadTitle(fake, 0), { name: "RangeError", message: "bad id: 0" });
    assert.equal(called, false);
  });
});
''')],
   [(["--test", "--test-reporter=spec"], None)],
   "Two details to copy. The async test is simply an `async` function, and the runner waits for it. For the function that would call the network, the test passes a small fake `fetchTitle` instead of using a mocking library: because `loadTitle` receives the dependency as an argument, the test needs no special tools. `assert.rejects` takes the promise (do not `await` it before passing it in) and an object that is matched against the error. The `called` flag checks the order of events, that the bad id was refused before any work was done. Add `\"test\": \"node --test\"` to the `scripts` in `package.json` and `npm test` does the same.")

# 6 ---------------------------------------------------------------------------------------------
ex("How do I read a huge text file line by line in Node without loading it all into memory? What about Windows line endings and a last line without a newline?",
   "Use `readline` on top of a read stream and loop with `for await`. The file is read in chunks and you get one line at a time, so the memory use stays flat whether the file has a hundred lines or a hundred million. Set `crlfDelay: Infinity` so that `\\r\\n` counts as one line break, and remember that `readline` does not include the line break in the line it gives you.",
   [("lines.mjs", "javascript", r'''
import { createReadStream } from "node:fs";
import readline from "node:readline";

export async function summarize(path) {
  const rl = readline.createInterface({
    input: createReadStream(path, { encoding: "utf8" }),
    crlfDelay: Infinity, // treat \r\n as a single line break
  });

  let total = 0;
  let blank = 0;
  let longest = "";
  for await (const line of rl) {
    total += 1;
    if (line.trim() === "") blank += 1;
    if (line.length > longest.length) longest = line;
  }
  return { total, blank, longest };
}
'''),
    ("demo.mjs", "javascript", r'''
import { readFileSync, writeFileSync } from "node:fs";
import { summarize } from "./lines.mjs";

// Windows line endings, an empty line, and no newline at the end of the file
writeFileSync("sample.txt", "first line\r\n\r\nthe longest line of all\r\nlast line, no newline");
const result = await summarize("sample.txt");
console.log(result);

const naive = readFileSync("sample.txt", "utf8").split("\n");
console.log("split on \\n only:", JSON.stringify(naive[0]), "- the \\r stays in the text");

writeFileSync("empty.txt", "");
console.log("empty file:", await summarize("empty.txt"));

try {
  await summarize("missing.txt");
} catch (err) {
  console.log("missing file:", err.code);
}
''')],
   [(["demo.mjs"], None)],
   "The four lines are counted correctly: the empty line counts as one, and the last line without a newline is not lost. The naive way, `split(\"\\n\")` on a Windows file, leaves a `\\r` at the end of every line, which causes strange bugs later (comparisons that fail, a CSV column that never matches). A file that does not exist is reported inside the loop's promise, so a normal `try/catch` around the `await` catches it, and the error has a `code` that you can test. An empty file gives zero lines, not one.")

# 7 ---------------------------------------------------------------------------------------------
ex("How do I call an API with fetch in Node and handle errors properly? I need a timeout, and I heard fetch does not throw for a 500.",
   "Both are true. `fetch` only rejects when the request could not be made at all (no connection, bad URL, timeout). A `500` or `404` is a normal answer, so you have to look at `response.ok` yourself and throw. For the timeout, pass `AbortSignal.timeout(ms)` as `signal`: the call is cancelled after that time and rejects with an error named `TimeoutError`. Wrapping this once in a small function means every caller gets the same, readable errors.",
   [("client.mjs", "javascript", r'''
export async function fetchJson(url, { timeoutMs = 3000 } = {}) {
  let response;
  try {
    response = await fetch(url, { signal: AbortSignal.timeout(timeoutMs) });
  } catch (err) {
    if (err.name === "TimeoutError") throw new Error(`timed out after ${timeoutMs} ms: ${url}`);
    throw new Error(`could not reach ${url} (${err.cause?.code ?? err.message})`);
  }
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} from ${url}`);
  }
  return response.json();
}
'''),
    ("demo.mjs", "javascript", r'''
import http from "node:http";
import { fetchJson } from "./client.mjs";

const server = http.createServer((req, res) => {
  if (req.url === "/ok") {
    res.writeHead(200, { "Content-Type": "application/json" }).end('{"hello":"world"}');
  } else if (req.url === "/fail") {
    res.writeHead(500).end("oops");
  } else if (req.url === "/slow") {
    setTimeout(() => res.writeHead(200).end("{}"), 600);
  } else {
    res.writeHead(404).end();
  }
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const base = `http://127.0.0.1:${server.address().port}`;

const dead = http.createServer();
await new Promise((resolve) => dead.listen(0, "127.0.0.1", resolve));
const deadPort = dead.address().port;
dead.close(); // nothing listens on this port any more

async function attempt(label, url, options) {
  try {
    console.log(label, "->", await fetchJson(url, options));
  } catch (err) {
    console.log(label, "-> error:", err.message.replace(String(deadPort), "PORT").replace(base, "BASE"));
  }
}

await attempt("ok     ", base + "/ok");
await attempt("500    ", base + "/fail");
await attempt("404    ", base + "/missing");
await attempt("slow   ", base + "/slow", { timeoutMs: 100 });
await attempt("refused", `http://127.0.0.1:${deadPort}/`);
server.closeAllConnections();
server.close();
''')],
   [(["demo.mjs"], None)],
   "Each failure has its own readable message, and none of them is a mystery like `fetch failed`. That generic message comes from the underlying network error, and the useful part (the `code`, such as `ECONNREFUSED`) is hidden in `err.cause`, which is why the wrapper reads `err.cause?.code`. `response.json()` can fail too (an answer that is not JSON), and that error is not wrapped here, so add a `try/catch` around it if you need a clearer message. For retries, add them around `fetchJson`, and only retry what can succeed later (a timeout, a `503`), never a `400` or `404`.")

# 8 ---------------------------------------------------------------------------------------------
ex("How should I read configuration from environment variables in Node? I want defaults, validation and a clear message if something is wrong.",
   "Read the environment in exactly one place, convert and check each value there, and collect **all** the problems before failing, so that the person who starts the program fixes everything in one go instead of one error at a time. Environment variables are always strings, so `PORT` needs converting, and `Number(\"abc\")` is `NaN`, which must be reported and not passed on. Node can also load a `.env` file by itself with `--env-file`, so no extra package is needed.",
   [("config.mjs", "javascript", r'''
export function loadConfig(env = process.env) {
  const problems = [];

  function integer(name, fallback, min, max) {
    const raw = env[name] ?? String(fallback);
    const value = Number(raw);
    if (raw.trim() === "" || !Number.isInteger(value) || value < min || value > max) {
      problems.push(`${name} must be a whole number from ${min} to ${max}, got "${raw}"`);
      return fallback;
    }
    return value;
  }

  function oneOf(name, fallback, allowed) {
    const value = env[name] ?? fallback;
    if (!allowed.includes(value)) {
      problems.push(`${name} must be one of ${allowed.join(", ")}, got "${value}"`);
    }
    return value;
  }

  const config = {
    port: integer("PORT", 3000, 1, 65535),
    mode: oneOf("NODE_ENV", "development", ["development", "test", "production"]),
    logLevel: oneOf("LOG_LEVEL", "info", ["debug", "info", "warn", "error"]),
    databaseUrl: env.DATABASE_URL,
  };
  if (!config.databaseUrl) problems.push("DATABASE_URL is required");

  if (problems.length > 0) {
    throw new Error("invalid configuration:\n  - " + problems.join("\n  - "));
  }
  return Object.freeze(config);
}
'''),
    ("main.mjs", "javascript", r'''
import { loadConfig } from "./config.mjs";

try {
  const config = loadConfig();
  // never print secrets: show only the part of the URL before the password
  console.log({ ...config, databaseUrl: config.databaseUrl.replace(/:\/\/.*@/, "://***@") });
} catch (err) {
  console.error(err.message);
  process.exitCode = 1;
}
'''),
    (".env", "text", "PORT=8080\nNODE_ENV=production\nDATABASE_URL=postgres://app:s3cret@db.internal/app")],
   [(["main.mjs"], None),
    (["main.mjs"], {"PORT": "abc", "NODE_ENV": "prod", "DATABASE_URL": "x"}),
    (["--env-file=.env", "main.mjs"], None),
    (["--env-file=.env", "main.mjs"], {"PORT": "9000"})],
   "The second run shows the point of collecting problems: two mistakes are reported together, with the value that was received. `process.exitCode = 1` marks the failure and lets Node finish normally (calling `process.exit(1)` can cut off output that is still being written). The last run shows the order of priority: a variable that is already set in the environment wins over the same name in the `.env` file, so `PORT=9000` beats `PORT=8080` and you can override the file from the command line or from your hosting platform. Keep `.env` out of git, because it holds secrets (add it to `.gitignore`), and commit a `.env.example` with the names and no values.")

# 9 ---------------------------------------------------------------------------------------------
ex("How do I shut down a Node HTTP server gracefully, so that requests that are already running can finish?",
   "Call `server.close()`: it stops accepting new connections and calls its callback when the existing ones are done. Two things are missing from that. Keep-alive connections that are idle stay open and would keep the server alive, so also call `server.closeIdleConnections()`. And a request that never finishes would wait forever, so set a deadline after which `server.closeAllConnections()` cuts whatever is left. In a real program you call this from a `SIGTERM` handler, which is the signal that Docker, systemd and most hosting platforms send first.",
   [("server.mjs", "javascript", r'''
import http from "node:http";

export function createApp() {
  return http.createServer((req, res) => {
    // a slow request: takes 300 ms to finish
    setTimeout(() => res.writeHead(200).end("finished the slow work"), 300);
  });
}

export function shutdown(server, { graceMs = 2000 } = {}) {
  return new Promise((resolve) => {
    server.close(() => resolve("closed cleanly"));
    server.closeIdleConnections();
    setTimeout(() => server.closeAllConnections(), graceMs).unref();
  });
}

// in a real program:
//   process.on("SIGTERM", async () => { console.log(await shutdown(server)); process.exit(0); });
'''),
    ("demo.mjs", "javascript", r'''
import { createApp, shutdown } from "./server.mjs";

const server = createApp();
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const base = `http://127.0.0.1:${server.address().port}`;

const inFlight = fetch(base).then((r) => r.text());   // starts a request that needs 300 ms
await new Promise((resolve) => setTimeout(resolve, 50)); // let it reach the server

const closing = shutdown(server);
console.log("shutdown started");

try {
  await fetch(base);
} catch (err) {
  console.log("new request:", err.cause?.code);
}
console.log("running request:", await inFlight);
console.log("server:", await closing);
''')],
   [(["demo.mjs"], None)],
   "The order of the output is the whole lesson: after `shutdown` has started, a new request is refused (`ECONNREFUSED`), the request that was already running still gets its answer, and only then does the server report that it closed cleanly. The `unref()` on the timer means the safety timer alone does not keep the process alive, so a clean shutdown ends immediately and does not wait for the two seconds. Choose the grace time to be a little shorter than the time your platform gives you before it sends `SIGKILL` (Docker waits 10 seconds by default), because after `SIGKILL` nothing you wrote runs any more.")

# ------------------------------------------------------------------------------ write
text = ""
for q, a in EXAMPLES:
    text += f"@@@ USER\n{q}\n@@@ ASSISTANT\n{a}\n@@@ END\n\n"
for q, a in EXAMPLES:
    assert len(q) + len(a) < 39000, (q, len(a))
OUT.write_text(text, encoding="utf-8", newline="\n")
print("wrote", OUT, len(EXAMPLES), "examples", len(text), "chars")

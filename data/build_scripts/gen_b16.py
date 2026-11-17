"""Build data/staging/claude_explain_concepts_16.txt.
Plain-English explanations of core developer concepts. Wherever an answer shows code or output,
the code is RUN here (Python, Node, rustc) and the real output / compiler message is pasted in."""
import subprocess
import sys
import tempfile
from pathlib import Path

F = "`" * 3
OUT = Path(r"C:\Projects\Mavo\Coding 1 2B\data\staging\claude_explain_concepts_16.txt")


def _run(cmd, d, timeout=60):
    p = subprocess.run(cmd, cwd=d, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True, encoding="utf-8", timeout=timeout)
    return p.returncode, p.stdout.replace("\r", "").rstrip("\n")


def run_py(code):
    d = Path(tempfile.mkdtemp())
    (d / "m.py").write_text(code.strip() + "\n", encoding="utf-8", newline="\n")
    rc, out = _run([sys.executable, "m.py"], d)
    if rc:
        print("PY FAILED\n", out[:1500]); sys.exit(1)
    return out


def run_node(code):
    d = Path(tempfile.mkdtemp())
    (d / "m.js").write_text(code.strip() + "\n", encoding="utf-8", newline="\n")
    rc, out = _run(["node", "m.js"], d)
    if rc:
        print("NODE FAILED\n", out[:1500]); sys.exit(1)
    return out


def run_rust(code):
    d = Path(tempfile.mkdtemp())
    (d / "m.rs").write_text(code.strip() + "\n", encoding="utf-8", newline="\n")
    rc, out = _run(["rustc", "--edition", "2021", "-A", "warnings", "-o", "m.exe", "m.rs"], d)
    if rc:
        print("RUSTC FAILED\n", out[:1500]); sys.exit(1)
    rc, out = _run([str(d / "m.exe")], d)
    return out


def rust_error(code):
    """Compile code that must FAIL and return the compiler message up to the final summary line."""
    d = Path(tempfile.mkdtemp())
    (d / "m.rs").write_text(code.strip() + "\n", encoding="utf-8", newline="\n")
    rc, out = _run(["rustc", "--edition", "2021", "-A", "warnings", "-o", "m.exe", "m.rs"], d)
    if rc == 0:
        print("EXPECTED A COMPILE ERROR BUT IT COMPILED"); sys.exit(1)
    keep = []
    for line in out.splitlines():
        if line.startswith("error: aborting") or line.startswith("For more information"):
            break
        keep.append(line)
    return "\n".join(keep).rstrip()


EXAMPLES = []


def text(question, answer):
    EXAMPLES.append((question, answer.strip()))


# 1 ---------------------------------------------------------------------------------------------
text("How does HTTPS work? Explain TLS in simple terms.",
     """
HTTPS is ordinary HTTP carried inside an encrypted channel called TLS. TLS gives you three things: **privacy** (nobody on the network can read the data), **integrity** (nobody can change it unnoticed) and **authentication** (you are really talking to the server that owns the domain).

What happens when your browser connects (TLS 1.3, simplified):
1. **Hello.** The browser says which TLS version and encryption algorithms it supports and sends a random number plus its half of a key exchange.
2. **Certificate.** The server answers with its half of the key exchange and its **certificate**: a file that links the domain name to a public key, signed by a Certificate Authority (CA).
3. **Verification.** The browser checks that the signature chains up to a CA that it already trusts, that the certificate is valid for exactly this domain name, and that it has not expired. The server also proves it owns the private key that belongs to the certificate.
4. **Shared secret.** Both sides combine the two key-exchange halves (an ephemeral Diffie-Hellman exchange) and arrive at the same secret key without ever sending it over the network.
5. **Encrypted traffic.** From now on everything, including the HTTP request line, headers, cookies and body, is encrypted with a fast symmetric algorithm such as AES-GCM or ChaCha20-Poly1305. Any change to the data is detected.

Why it is built this way: public-key cryptography solves the "how do we agree on a secret with a stranger" problem but is slow, so it is used only for the handshake. Symmetric encryption is fast, so it carries the actual data. Because the keys are ephemeral, recording the traffic today and stealing the server's key later does not decrypt it (**forward secrecy**).

What HTTPS does **not** do:
- It does not hide which server you connect to. The IP address is visible, and so is the domain name in most cases (it is sent in the handshake as SNI, unless Encrypted Client Hello is used, and in DNS queries unless you use DNS over HTTPS).
- It does not make a site trustworthy. A phishing site can have a perfectly valid certificate for its own domain.
- It does not protect the data once it reaches the server.

Common certificate errors and what they mean: *expired* (the certificate was not renewed), *name mismatch* (the certificate is for a different domain), *untrusted issuer* or *self-signed* (no trusted CA vouches for it). For your own sites, free certificates from Let's Encrypt are issued and renewed automatically by tools such as Certbot or by hosts like Caddy.""")

# 2 ---------------------------------------------------------------------------------------------
text("What happens when I type a URL into the browser and press Enter?",
     """
Here is the whole journey, in order. Each step can be a source of delay, which is why this is a favourite interview question.

1. **Parse the URL.** The browser splits `https://example.com/products?id=5` into scheme (`https`), host (`example.com`), path and query. If you typed words instead of a URL, it opens a search.
2. **Check local caches.** It may already have the page (HTTP cache), or know that the site must use HTTPS (HSTS list).
3. **DNS lookup.** It needs an IP address for `example.com`. The browser and the operating system each have a cache. If both miss, a DNS resolver (usually your ISP's or a public one) asks the root servers, then the `.com` servers, then the domain's own name servers, and caches the answer for the time given in its TTL.
4. **Open a connection.** TCP needs a handshake (one round trip). HTTP/3 uses QUIC over UDP, which combines connection setup with encryption.
5. **TLS handshake.** For HTTPS the browser and server agree on keys and the browser checks the certificate (one more round trip in TLS 1.3).
6. **Send the HTTP request.** For example `GET /products?id=5` with headers such as `Host`, `Accept` and your cookies.
7. **The server works.** A load balancer picks one server, the web application runs, probably asks a database or cache, and builds a response. It returns a status code, headers and a body, usually HTML.
8. **The browser parses the HTML** while it is still arriving. It builds the **DOM** tree. Each `<link rel="stylesheet">`, `<script>` and `<img>` it finds triggers another request (steps 3 to 7 again, but often on the same connection).
9. **Render.** CSS becomes the CSSOM. DOM and CSSOM combine into a render tree. Then **layout** (where does everything go), **paint** (draw pixels) and **composite** (put layers together on the GPU) follow.
10. **JavaScript runs.** A plain `<script>` blocks the parser until it has been downloaded and executed. `defer` (run after parsing, in order) and `async` (run as soon as it arrives) avoid that. Scripts can change the DOM and fetch more data, which causes more layout and paint.

Where to optimise: fewer and smaller requests, caching headers, a CDN (shorter distance to the server), compressed text (gzip or Brotli), `defer` for scripts, and small critical CSS so that the first paint comes early. Open the **Network** tab of the browser's developer tools to see these phases (DNS, connect, TLS, waiting, download) for every request.""")

# 3 ---------------------------------------------------------------------------------------------
text("What is the difference between REST, GraphQL and gRPC, and when should I use each?",
     """
All three let one program call another over a network. They differ in how you describe what you want.

**REST** models your data as **resources** with URLs and uses the HTTP verbs: `GET /users/42`, `POST /users`, `DELETE /users/42`. The server decides the shape of each response.
- Strengths: simple, works with any HTTP client, easy to debug with `curl`, and HTTP caching (CDNs, browser cache, ETags) works for free.
- Weaknesses: *over-fetching* (you get 30 fields when you need 3) and *under-fetching* (a screen needs three requests to different URLs). Versioning (`/v2/...`) can become messy.

**GraphQL** has one endpoint. The client sends a **query** that lists exactly the fields it wants, even across related objects, and gets back JSON in that shape.
- Strengths: one round trip for a whole screen, no wasted data, a typed schema that documents itself, and a good fit when many different clients (web, mobile, partners) need different slices of the same data.
- Weaknesses: caching is harder because everything is a `POST` to one URL. The server must guard against expensive queries (depth and cost limits), and it must avoid the *N+1 problem* (one database query per item in a list; the usual fix is batching with a DataLoader). File upload and error handling need extra conventions.

**gRPC** uses a `.proto` file to define services and messages. Code for client and server is generated, and messages travel as compact binary Protocol Buffers over HTTP/2.
- Strengths: fast and small, strongly typed contracts, built-in streaming in both directions, and generated clients in many languages. A good fit for communication between your own backend services.
- Weaknesses: not human-readable on the wire, browsers cannot call it directly (you need gRPC-Web or a gateway), and tooling is heavier than `curl`.

A practical rule:
- Public API or a simple CRUD app: **REST** with a good OpenAPI description.
- A product with several front ends and deeply connected data: consider **GraphQL**.
- Internal service-to-service calls where latency and contracts matter: **gRPC**.
- Do not choose by fashion. A small team with one front end is usually fastest with plain REST and a few well designed endpoints.""")

# 4 ---------------------------------------------------------------------------------------------
_slow_fast = r'''
def has_duplicates_slow(items):
    comparisons = 0
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            comparisons += 1
            if items[i] == items[j]:
                return True, comparisons
    return False, comparisons


def has_duplicates_fast(items):
    seen = set()
    steps = 0
    for x in items:
        steps += 1
        if x in seen:
            return True, steps
        seen.add(x)
    return False, steps


print("n      slow (comparisons)   fast (set steps)")
for n in (10, 100, 1000, 2000):
    data = list(range(n))  # worst case: no duplicates at all
    slow = has_duplicates_slow(data)[1]
    fast = has_duplicates_fast(data)[1]
    print(f"{n:<6} {slow:<20} {fast}")
'''
_out = run_py(_slow_fast)
text("What is Big-O notation? Explain it with a real example I can run.",
     f"""
Big-O describes how the **work** of an algorithm (time or memory) **grows when the input grows**. It ignores constant factors and small details, because they matter less than the shape of the growth curve when `n` gets large. Written `O(n)`, it says "roughly proportional to n in the worst case".

The classes you will meet most often, from best to worst:
- `O(1)` constant: looking up an array index or a hash map key (on average).
- `O(log n)`: binary search in a sorted array. Doubling the input adds one step.
- `O(n)` linear: scanning a list once.
- `O(n log n)`: good sorting algorithms (merge sort, the sort built into your language).
- `O(n²)` quadratic: two nested loops over the same data. Doubling the input makes it four times slower.
- `O(2ⁿ)` exponential: trying every subset. Only usable for tiny inputs.

Example: "does this list contain a duplicate?" Compare every pair (nested loops) or remember what you have seen in a set. The program counts the real operations in the worst case (no duplicates):

{F}python
{_slow_fast.strip()}
{F}

Output:

{F}
{_out}
{F}

Reading the numbers: the slow version does `n(n-1)/2` comparisons. When `n` doubles from 1000 to 2000 the count goes from 499,500 to 1,999,000, about four times more, which is the signature of `O(n²)`. The set version does one step per item (`O(n)`), and doubling `n` doubles the work. The price is memory: the set stores up to `n` items, so it is `O(n)` extra space. That trade of space for time is very common.

Practical advice:
- Big-O matters for large `n`. For 10 items the "slow" way is fine and often simpler.
- It describes growth, not speed. An `O(n)` algorithm with a huge constant can lose to an `O(n log n)` one on small inputs.
- Hidden costs count: `x in some_list` is `O(n)`, `x in some_set` is `O(1)` on average, and string concatenation in a loop can be `O(n²)` in some languages.
- Measure before you optimise. A profiler tells you which part is really slow.""")

# 5 ---------------------------------------------------------------------------------------------
text("SQL or NoSQL: how do I choose a database for my project?",
     """
Start from the shape of your data and the questions you will ask, not from the label.

**Relational databases (PostgreSQL, MySQL, SQLite)** store data in tables with a fixed schema and relations between them.
- You get **joins**, **constraints** (foreign keys, unique, not null) and **ACID transactions**. A transfer that subtracts from one account and adds to another either happens completely or not at all.
- You can ask new questions later with SQL without having planned them. That flexibility is the main reason they remain the default.

**NoSQL** is a group of very different tools:
- **Document stores** (MongoDB, Firestore) keep JSON-like documents. They fit data that is read and written as one whole piece, such as a product page with nested options, and they allow different fields per document.
- **Key-value stores** (Redis, DynamoDB in simple use) give very fast lookups by key. They are great for caches, sessions and counters.
- **Wide-column and time-series stores** (Cassandra, ClickHouse, TimescaleDB) handle huge write volumes of data that arrive in time order.
- **Graph databases** (Neo4j) make "friends of friends" and route queries natural.

How to decide:
1. Is the data **related** (users, orders, products, payments) and do you need consistency? Use a relational database.
2. Do you only look things up by one key, or need a cache, a queue or a leaderboard? Use a key-value store such as Redis, next to your main database.
3. Is it mostly flexible, self-contained documents? A document store is reasonable, but PostgreSQL's `JSONB` columns also cover this need well.
4. Do you have a measured need for write throughput or size beyond one server, with access patterns that you know in advance? A distributed NoSQL store may be right.

Common mistakes:
- Choosing NoSQL "for scale" before there is any scale. A single PostgreSQL server handles a very large number of requests and terabytes of data.
- Storing related data in a document store and then repeating (denormalising) it everywhere. When a user's name changes you have to update it in many places.
- Skipping transactions and constraints and then writing that checking logic by hand in the application.

For most new web or mobile back ends the safe default is **PostgreSQL** (or SQLite for a small app or a single-machine tool), plus Redis if you need caching. Change that only when you can point to a concrete requirement.""")

# 6 ---------------------------------------------------------------------------------------------
text("What is the difference between a process and a thread, and between concurrency and parallelism?",
     """
**Process vs thread**
- A **process** is a running program with its own private memory, file handles and identity. Processes are isolated: if one crashes, the others continue, and they have to communicate through pipes, sockets or shared-memory areas.
- A **thread** is a path of execution **inside** a process. All threads of a process share the same memory. That makes communication cheap, and it also means two threads can change the same data at the same time.
- Starting a process is heavier than starting a thread, but a process gives you stronger isolation.

**Concurrency vs parallelism**
- **Concurrency** is about *structure*: dealing with many tasks in overlapping time periods, for example a server handling 1,000 connections. It can run on a single core by switching between tasks.
- **Parallelism** is about *execution*: doing several things at the same instant on several cores.
- A cook who starts the soup, then chops vegetables while it simmers, is concurrent. Two cooks working at the same time are parallel.

**Which tool for which problem**
- **I/O-bound** work (waiting for the network, a disk or a database) benefits from concurrency. `async/await` with an event loop handles thousands of waiting tasks on one thread. Node.js works this way.
- **CPU-bound** work (compressing video, training a model, hashing) needs real parallelism: several threads or processes on several cores. In the standard CPython interpreter the Global Interpreter Lock lets only one thread run Python bytecode at a time, so CPU-bound Python code uses `multiprocessing` or native libraries. In Node.js use worker threads. In Rust, Go, Java and C++ threads run in parallel.

**The dangers of shared memory**
- A **race condition** happens when the result depends on the unlucky timing of two threads. For example, two threads both read a counter as 5 and both write 6, so one increment is lost.
- A **mutex** (lock) protects a piece of data so that only one thread at a time can use it. Locks that are held too long slow the program, and two threads that wait for each other's locks cause a **deadlock**.
- Prefer designs that avoid sharing: pass messages through channels or queues, or use immutable data. Rust goes further and makes a data race a compile-time error through its ownership rules.

Rule of thumb: first measure whether your program is waiting or computing. If it is waiting, use async I/O. If it is computing on many independent items, use a pool of workers.""")

# 7 ---------------------------------------------------------------------------------------------
_own_fail1 = r'''
fn main() {
    let a = String::from("hello");
    let b = a;
    println!("{} {}", a, b);
}
'''
_own_fail2 = r'''
fn main() {
    let mut v = vec![1, 2, 3];
    let first = &v[0];
    v.push(4);
    println!("{}", first);
}
'''
_own_ok = r'''
fn print_len(s: &String) -> usize {
    s.len() // borrows: the caller keeps ownership
}

fn consume(s: String) -> usize {
    s.len() // takes ownership: the String is freed when this function ends
}

fn main() {
    let a = String::from("hello");
    let b = a.clone(); // an explicit, visible copy
    println!("{} {}", a, b);

    let n = print_len(&a); // borrow
    println!("{} has {} bytes", a, n);

    let m = consume(a); // move: `a` can no longer be used
    println!("consumed, length {}", m);

    let mut v = vec![1, 2, 3];
    let first = &v[0]; // shared borrow
    println!("first = {}", first);
    v.push(4); // fine: the borrow ended after its last use above
    println!("{:?}", v);
}
'''
_e1 = rust_error(_own_fail1)
_e2 = rust_error(_own_fail2)
_o = run_rust(_own_ok)
text("Explain Rust ownership and borrowing in plain English.",
     f"""
Rust has no garbage collector and no manual `free`. Instead the compiler follows three rules about **ownership**:
1. Every value has exactly one **owner** (a variable).
2. When the owner goes out of scope, the value is dropped (its memory is freed).
3. Ownership can be **moved** to another variable or function, and then the old variable can no longer be used.

Think of a physical book. If you give it to a friend, you no longer have it. If you only let someone read it while it stays in your hands, you **lend** it. That lending is called **borrowing**.

**Moves.** Assigning a `String` to another variable moves it:

{F}rust,compile_fail
{_own_fail1.strip()}
{F}

The compiler refuses to build this:

{F}
{_e1}
{F}

Moving is cheap (only a pointer, a length and a capacity are copied) and it prevents the classic bug where two owners free the same memory. Simple types like `i32` and `bool` implement `Copy` and are copied instead of moved.

**Borrowing.** A reference `&T` lets code use a value without owning it. The rules:
- Any number of shared references `&T`, **or** exactly one mutable reference `&mut T`, at a time, never both.
- A reference can never outlive the value it points to.

These rules make data races and dangling pointers impossible in safe Rust. Here the compiler stops a bug that is easy to write in C++, holding a pointer into a vector and then growing the vector, which may move its memory:

{F}rust,compile_fail
{_own_fail2.strip()}
{F}

{F}
{_e2}
{F}

The fixes: copy or clone when you really need two owners, borrow when you only need to look, and finish using a reference before you change the value. This program does all three and compiles:

{F}rust
{_own_ok.strip()}
{F}

Output:

{F}
{_o}
{F}

Practical advice:
- Function parameters: use `&T` to read, `&mut T` to change, and plain `T` when the function should consume or store the value.
- Prefer `&str` over `&String` and `&[T]` over `&Vec<T>` in parameters. They accept more kinds of arguments.
- When the borrow checker complains, read the message from top to bottom: it names the value, where it was moved or borrowed, and often suggests the fix (like `.clone()` above).
- `.clone()` is a legitimate tool, but if you have to put it everywhere, rethink who should own the data.""")

# 8 ---------------------------------------------------------------------------------------------
_cors = r'''
const http = require('node:http');

const ALLOWED = new Set(['https://app.example.com']);

const server = http.createServer((req, res) => {
  const origin = req.headers.origin;
  if (origin && ALLOWED.has(origin)) {
    res.setHeader('Access-Control-Allow-Origin', origin); // echo one allowed origin, never "*" with credentials
    res.setHeader('Access-Control-Allow-Credentials', 'true');
    res.setHeader('Vary', 'Origin');
  }
  if (req.method === 'OPTIONS') { // the preflight request
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
    res.setHeader('Access-Control-Max-Age', '600');
    res.writeHead(204).end();
    return;
  }
  res.setHeader('Content-Type', 'application/json');
  res.end(JSON.stringify({ ok: true }));
});

server.listen(0, async () => {
  const base = `http://127.0.0.1:${server.address().port}`;
  const show = async (label, init) => {
    const res = await fetch(base, init);
    const cors = [...res.headers]
      .filter(([k]) => k.startsWith('access-control') || k === 'vary')
      .map(([k, v]) => `    ${k}: ${v}`);
    console.log(`${label} -> ${res.status}`);
    console.log(cors.length ? cors.join('\n') : '    (no CORS headers)');
  };
  await show('request from allowed origin', { headers: { Origin: 'https://app.example.com' } });
  await show('request from other origin  ', { headers: { Origin: 'https://evil.example.net' } });
  await show('preflight for PUT          ', {
    method: 'OPTIONS',
    headers: { Origin: 'https://app.example.com', 'Access-Control-Request-Method': 'PUT' },
  });
  server.close();
});
'''
_cors_out = run_node(_cors)
text("What is CORS and how do I fix the 'blocked by CORS policy' error?",
     f"""
**Background: the same-origin policy.** A browser lets a page read responses only from its own **origin**, the combination of scheme, host and port. `https://app.example.com` and `https://api.example.com` are different origins, and so are `http://localhost:3000` and `http://localhost:8000`. This stops a random website from silently reading your data from another site where you are logged in.

**CORS (Cross-Origin Resource Sharing)** is the way a server says "this other origin may read my responses". It is done with response headers, and the **browser** enforces it. The request is usually still sent and the server still answers; the browser just refuses to give the response to your JavaScript and prints the error.

Two kinds of requests:
- **Simple requests** (for example a `GET`, or a `POST` of a plain form) are sent directly. The browser then checks `Access-Control-Allow-Origin` in the response.
- Anything else, such as `PUT`/`DELETE`, a custom header like `Authorization`, or `Content-Type: application/json`, triggers a **preflight**: first the browser sends an `OPTIONS` request that asks "may I send this?" and only if the answer allows it, it sends the real request.

Here is a small server that handles both, and a script that calls it. The calls set the `Origin` header by hand, because this runs in Node and not in a browser:

{F}js
{_cors.strip()}
{F}

Output:

{F}
{_cors_out}
{F}

How to read it:
- For the allowed origin the server echoes that origin in `Access-Control-Allow-Origin`, so the browser lets the page read the response. For the other origin there are no CORS headers, so a browser would block it (the server itself still answered `200`).
- The preflight answer says which methods and headers are allowed (`Access-Control-Allow-Methods`, `Access-Control-Allow-Headers`) and for how many seconds the browser may remember it (`Access-Control-Max-Age`).
- `Vary: Origin` tells caches that the response differs per origin. Without it a cache may hand the header for one origin to another.

**How to fix the error:**
1. The fix is **on the server** (or a proxy in front of it). Nothing you do in the front-end code can grant yourself permission. Add the headers above, or use your framework's CORS middleware (such as the `cors` package for Express, `CORSMiddleware` in FastAPI, or `tower-http` in Rust).
2. If you send cookies or `Authorization` with `credentials: 'include'`, the server must answer with `Access-Control-Allow-Credentials: true` and a **specific** origin. The wildcard `*` is not allowed in that case.
3. Make sure the preflight (`OPTIONS`) gets a successful response too, and that authentication middleware does not reject it with `401`.
4. During development, the simplest option is often a dev-server proxy (Vite's `server.proxy`, for example), which makes the browser see one origin.

Common misunderstandings:
- `fetch(url, {{ mode: 'no-cors' }})` does not fix anything. It gives you an **opaque** response that your code cannot read.
- CORS is not server security. `curl` and other servers ignore it. It protects the user's browser, so you still need real authentication and authorization on the server.
- Browser extensions that turn CORS off help only for your own testing.""")

# 9 ---------------------------------------------------------------------------------------------
_jwt = r'''
const crypto = require('node:crypto');

const b64url = (data) => Buffer.from(data).toString('base64url');
const fromB64url = (s) => Buffer.from(s, 'base64url').toString('utf8');
const hmac = (data, secret) => crypto.createHmac('sha256', secret).update(data).digest();

function sign(payload, secret) {
  const header = { alg: 'HS256', typ: 'JWT' };
  const body = `${b64url(JSON.stringify(header))}.${b64url(JSON.stringify(payload))}`;
  return `${body}.${b64url(hmac(body, secret))}`;
}

function verify(token, secret) {
  const [h, p, s] = token.split('.');
  const expected = hmac(`${h}.${p}`, secret);
  const given = Buffer.from(s ?? '', 'base64url');
  if (given.length !== expected.length || !crypto.timingSafeEqual(given, expected)) {
    throw new Error('invalid signature');
  }
  const payload = JSON.parse(fromB64url(p));
  if (payload.exp !== undefined && payload.exp < Date.now() / 1000) throw new Error('token expired');
  return payload;
}

const secret = 'demo-secret-do-not-use-in-production';
const token = sign({ sub: 'user-42', role: 'member', exp: 4102444800 }, secret); // expires in the year 2100
const [h, p] = token.split('.');

console.log('parts   :', token.split('.').length);
console.log('header  :', fromB64url(h));
console.log('payload :', fromB64url(p), '<- readable by anyone, it is NOT encrypted');
console.log('verify  :', verify(token, secret));

const forged = [h, b64url(JSON.stringify({ sub: 'user-42', role: 'admin', exp: 4102444800 })), token.split('.')[2]].join('.');
for (const [label, t, key] of [
  ['forged payload ', forged, secret],
  ['wrong secret   ', token, 'another-secret'],
  ['expired token  ', sign({ sub: 'user-42', exp: 1 }, secret), secret],
]) {
  try { verify(t, key); console.log(label, 'accepted (bad!)'); }
  catch (e) { console.log(label, 'rejected:', e.message); }
}
'''
_jwt_out = run_node(_jwt)
text("JWT or session cookies: which should I use for authentication?",
     f"""
Both answer "who is making this request?". They differ in **where the truth lives**.

**Server-side session.** After login the server creates a random, unguessable session ID, stores the session data (user id, roles, expiry) in a database or in Redis, and sends the ID to the browser in a cookie. On each request it looks the ID up.
- Easy to **revoke**: delete the session and the user is logged out immediately (useful for "log out everywhere" and for stolen devices).
- The cookie holds no data, so there is nothing to leak or forge.
- Cost: a lookup per request, and with several servers they must share the session store.

**JWT (JSON Web Token).** The server gives the client a signed token that contains the claims itself (`sub`, `role`, `exp`). Any server that knows the signing key can check it without a database lookup. The demo below signs a token with HMAC-SHA256 and checks it:

{F}js
{_jwt.strip()}
{F}

Output:

{F}
{_jwt_out}
{F}

What the output shows:
- A JWT is three Base64URL parts separated by dots: header, payload, signature. The payload can be **read by anyone**. It is signed, not encrypted, so never put secrets in it.
- The signature covers header and payload. Changing the role to `admin` without the key makes the signature invalid. A wrong key and an expired `exp` are also rejected.
- The check uses `timingSafeEqual`, so an attacker cannot learn the signature byte by byte from response times.

**The trade-offs of JWT:**
- Stateless, which suits many servers and calls between services, and tokens can be passed to other APIs.
- Hard to revoke before they expire. Solutions are short lifetimes (5 to 15 minutes) combined with a **refresh token** that is stored on the server and can be revoked, or a denylist, which brings back server-side state.
- Common mistakes: accepting `alg: none` or letting the token choose the algorithm (always fix the allowed algorithm on the server), very long expiry, putting sensitive data in the payload, and storing the token in `localStorage`, where any XSS bug can steal it.

**Recommendation:**
- A normal website or app with its own back end: use **server-side sessions** in a cookie with `HttpOnly` (JavaScript cannot read it), `Secure` (HTTPS only) and `SameSite=Lax` or `Strict` (against CSRF). It is simpler and safer.
- APIs consumed by several clients or services, single sign-on, or third-party access: use **short-lived JWT access tokens** (this is what OAuth 2.0 and OpenID Connect use), with a library that has been audited. Do not write your own verification for production.
- Whatever you choose, hash passwords with a slow algorithm (Argon2id, scrypt or bcrypt), and consider passkeys or an identity provider instead of building login yourself.""")

# 10 --------------------------------------------------------------------------------------------
_idx = r'''
import sqlite3

con = sqlite3.connect(":memory:")
con.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT, country TEXT)")
con.executemany(
    "INSERT INTO users (email, country) VALUES (?, ?)",
    [(f"user{i}@example.com", "IN" if i % 3 == 0 else "US") for i in range(20000)],
)


def plan(sql, *params):
    rows = con.execute("EXPLAIN QUERY PLAN " + sql, params).fetchall()
    return " | ".join(row[3] for row in rows)


lookup = "SELECT * FROM users WHERE email = ?"
print("1) no index          :", plan(lookup, "user777@example.com"))

con.execute("CREATE INDEX idx_users_email ON users(email)")
print("2) with index        :", plan(lookup, "user777@example.com"))
print("3) lower(email) = ?  :", plan("SELECT * FROM users WHERE lower(email) = ?", "user777@example.com"))
print("4) email LIKE '%777@':", plan("SELECT * FROM users WHERE email LIKE ?", "%777@example.com"))
print("5) ORDER BY email    :", plan("SELECT * FROM users ORDER BY email LIMIT 5"))

con.execute("CREATE INDEX idx_users_country ON users(country)")
print("6) country = 'IN'    :", plan("SELECT * FROM users WHERE country = ?", "IN"))
print("   rows with country IN:", con.execute("SELECT COUNT(*) FROM users WHERE country = 'IN'").fetchone()[0], "of 20000")
'''
_idx_out = run_py(_idx)
text("What is a database index, when does it help, and when does it hurt?",
     f"""
An **index** is a separate, sorted data structure (usually a **B-tree**) that points to the rows of a table. It works like the index of a book: instead of reading every page to find a word, you look the word up in the sorted list and jump to the page. Without an index the database must do a **full table scan** and read every row.

The demo below uses SQLite and asks the database for its query plan with `EXPLAIN QUERY PLAN`. Always do this in your real database (`EXPLAIN ANALYZE` in PostgreSQL) instead of guessing.

{F}python
{_idx.strip()}
{F}

Output:

{F}
{_idx_out}
{F}

Reading the plans:
- `SCAN` means every row is read. `SEARCH ... USING INDEX` means the database jumped straight to the matching rows through the B-tree. Lookups on 20,000 rows are fast either way, but on 20 million rows a scan is the difference between milliseconds and seconds.
- Line 5 is a `SCAN ... USING INDEX`: the database walks the index from the smallest to the largest email, so the rows come out already sorted and no separate sorting step appears in the plan.
- An index on a column is also used for range conditions (`>`, `<`, `BETWEEN`), for `ORDER BY` (the data is already sorted, so no separate sort step is needed) and for uniqueness checks.
- Wrapping the column in a function, as in `lower(email) = ?`, **hides it from the index**, so the plan goes back to a scan. The fix is to store the data normalised, or create an index on the expression (supported by PostgreSQL and SQLite).
- A `LIKE` pattern that starts with a wildcard (`'%777@...'`) cannot use an ordinary index, because the sort order helps only when you know the beginning of the value.

**The costs of indexes:**
- Every `INSERT`, `UPDATE` and `DELETE` must also update every index on the table, so write-heavy tables should not have indexes that nobody uses.
- Indexes take disk space and memory.
- Indexes on columns with only a few distinct values (a boolean, or a country column where most rows share a value) help little, because the query returns a large part of the table anyway. In line 6 SQLite still uses the `country` index, but 6,667 of the 20,000 rows match, so the database must visit a third of the table in index order and the saving is small, while every write pays for maintaining that index. A good planner with up-to-date statistics may prefer a plain scan in such a case, and then it is right to do so.

**Practical rules:**
1. Index the columns that appear in `WHERE`, `JOIN ... ON` and `ORDER BY` of queries that are slow or frequent. Foreign key columns are the classic forgotten ones.
2. In a **composite** index `(a, b)` the order matters. It serves queries on `a` and on `a AND b`, but not on `b` alone (the leftmost-prefix rule). Put the column you compare with `=` first.
3. Measure: look at the plan before and after, and drop indexes that no query uses.
4. Primary keys and `UNIQUE` constraints already create an index. Do not add a second one.""")

# 11 --------------------------------------------------------------------------------------------
text("What is Docker? Explain the difference between an image and a container.",
     """
Docker packages an application together with everything it needs to run (runtime, libraries, system tools, configuration) so that it behaves the same on your laptop, on a colleague's machine and on a server. "It works on my machine" becomes "it works in the image".

**Image.** A read-only template. It is built in **layers**: each instruction in a `Dockerfile` adds a layer, and unchanged layers are cached and shared between images. An image is like a class or an installer: it describes what exists, but nothing is running.

**Container.** A **running instance** of an image: the image's layers plus a thin writable layer on top, started as an isolated process. Many containers can start from one image, like many objects from one class. When a container is deleted, what it wrote to its own writable layer is deleted with it.

**Container vs virtual machine.** A VM includes a complete guest operating system with its own kernel. A container shares the **kernel of the host** and is isolated with Linux features (namespaces for what a process can see, cgroups for how much CPU and memory it may use). That is why containers start in about a second and use far less memory. The price is weaker isolation than a VM, and a Linux container needs a Linux kernel (Docker Desktop on Windows and macOS runs a small Linux VM for this).

A typical `Dockerfile` for a Node.js app:

```dockerfile
FROM node:22-slim
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev
COPY . .
EXPOSE 3000
CMD ["node", "server.js"]
```

The order is deliberate: the dependency files are copied and installed **before** the rest of the source. As long as `package.json` does not change, Docker reuses the cached `npm ci` layer, and rebuilds after a code change take seconds instead of minutes.

Commands you will use daily:
- `docker build -t myapp .` builds an image from the Dockerfile in the current folder.
- `docker run -p 8080:3000 myapp` starts a container and maps host port 8080 to container port 3000. Add `-d` to run it in the background and `--rm` to delete it when it stops.
- `docker ps` lists running containers (`-a` shows stopped ones too), `docker logs <name>` shows output, `docker exec -it <name> sh` opens a shell inside it, and `docker stop <name>` stops it.
- `docker compose up` starts several containers (for example your app, a database and Redis) from one `compose.yaml` file.

Things beginners trip over:
- **Data disappears with the container.** Keep databases and uploads in a **volume** (`-v mydata:/var/lib/postgresql/data`) or in a bind mount.
- `localhost` inside a container means the container itself, not your computer. Containers in one Compose project reach each other by service name.
- Do not bake secrets into images (anyone who can pull the image can read them). Pass them at run time with environment variables or your platform's secret store.
- Add a `.dockerignore` (for `node_modules`, `.git`, `.env`) so that the build context stays small and clean.
- Run the process as a non-root user where possible, and use small official base images (`-slim`, `alpine`) to reduce size and attack surface.""")

# 12 --------------------------------------------------------------------------------------------
text("How should I debug a bug in my code systematically instead of guessing?",
     """
Guessing and changing code at random feels productive but often adds new bugs. A repeatable method is faster.

1. **Reproduce it reliably.** If you cannot trigger the bug on demand, you cannot know whether a fix worked. Write down the exact steps and input. For a flaky bug, find what varies: timing, data, environment, order of operations.
2. **Read the error message and stack trace completely.** Read what kind of error it is, where it happened, and which of **your** files appear in the trace. In Python the most recent call is at the **bottom** of the traceback, and in JavaScript and Java it is at the **top**. Search for the exact message (without your own names and paths) if you do not know it.
3. **Shrink the problem.** Remove code and input until the smallest example that still fails is left. Often the bug becomes obvious while you shrink, and if not, the small example is what you show to others, or put in a bug report.
4. **Form a hypothesis and test it with one experiment.** Say it in a sentence: "I think `user` is `None` because the lookup returns nothing when the id has a trailing space." Then check it by printing the value, using a debugger, or writing a failing test. Change **one thing at a time**, otherwise you do not know what mattered.
5. **Check your assumptions, not your intentions.** Print the actual values and types at the point where it goes wrong. Many bugs live in something you were *sure* about: a variable that is not what you think, a function that returns earlier than you thought, a config file that was not loaded, or an old build that is still running.
6. **Bisect.** Cut the search space in half. Put a check in the middle of the code path: is the data still correct here? Then continue in the half that contains the problem. With version control, `git bisect` does the same with commits and finds the change that introduced a regression in about log2(n) steps.
7. **Use the right tool.** Print or log statements are quick and work everywhere. A **debugger** (breakpoints, step through, inspect variables, watch expressions) is better when you need to see many values or follow complicated control flow. Browser dev tools, `pdb` or `breakpoint()` in Python, `dbg!` in Rust, and your IDE all provide them.
8. **Explain it out loud.** Describing the problem step by step to a colleague, or to a rubber duck, forces you to state assumptions, and the mismatch often shows up mid-sentence.
9. **Take a break if you are stuck.** A short walk, or sleeping on it, regularly solves what an hour of staring did not.
10. **Fix the cause, then lock it in.** Do not patch the symptom (for example by catching the exception and ignoring it). Write a test that fails before the fix and passes after, so the bug cannot quietly come back, and look for the same mistake in similar places.

When asking someone else for help, include: what you expected, what happened instead, the exact error text, the smallest code that reproduces it, and what you already tried. That alone makes most questions answerable in one reply.""")


def block(q, a):
    return f"@@@ USER\n{q}\n@@@ ASSISTANT\n{a}\n@@@ END\n\n"


OUT.write_text("".join(block(q, a) for q, a in EXAMPLES), encoding="utf-8")
print("wrote", OUT, len(EXAMPLES), "examples", OUT.stat().st_size, "bytes")

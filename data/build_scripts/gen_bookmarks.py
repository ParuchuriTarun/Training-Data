"""Builds claude_longhorizon_bookmarks_11.txt from the tested project files in v1/ and v2/."""
import ast
from pathlib import Path

HERE = Path(__file__).resolve().parent
F = "`" * 3


def read(version, name):
    return (HERE / version / name).read_text(encoding="utf-8").rstrip() + "\n"


def methods(version, name, cls, wanted):
    """Source of the wanted methods of a class (with their original indentation)."""
    src = read(version, name)
    tree = ast.parse(src)
    lines = src.splitlines()
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == cls:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name in wanted:
                    start = (item.decorator_list[0].lineno if item.decorator_list else item.lineno) - 1
                    out.append((wanted.index(item.name), "\n".join(lines[start:item.end_lineno])))
    return "\n\n".join(text for _, text in sorted(out))


def code(lang, text):
    return f"{F}{lang}\n{text.rstrip()}\n{F}"


t = []

# ---------------------------------------------------------------- turn 1
t.append("""@@@ USER
I want to build a small bookmarks service with a JSON HTTP API, using only the Python standard library. I want to add a bookmark (url, title, tags), list bookmarks (optionally filtered by tag), and delete one. Plan the steps and do only step 1.
@@@ ASSISTANT
Plan:

1. **Storage** (`store.py`) with SQLite, plus unit tests. No HTTP yet, so the rules of the data are fixed and tested first.
2. **HTTP server** (`server.py`) with `http.server`: routes, JSON, status codes.
3. **API tests** (`test_api.py`) that start the server and call it.
4. **Hardening**: pagination, an API key for writes, and a list of what is still missing.

Step 1 is below. Put both files in one folder.

**store.py**

""" + code("python", read("v1", "store.py")) + """

**test_store.py**

""" + code("python", read("v1", "test_store.py")) + """

Run it from that folder:

""" + code("", "python -m unittest test_store -v") + """

Expected end of the output:

""" + code("", "Ran 5 tests in 0.011s\n\nOK") + """

Decisions in this step, so you can change them on purpose later:
- `url` is `UNIQUE` in the database. The program checks nothing itself: the database refuses the second insert, and `add` turns that error into `DuplicateError`. This is also safe when two requests arrive at the same moment.
- Tags live in their own table with `ON DELETE CASCADE`, so deleting a bookmark removes its tags. SQLite needs `PRAGMA foreign_keys = ON` for that, which is easy to forget.
- `clean_tags` makes tags lower case, removes duplicates and sorts them, so `Python` and ` python ` are the same tag.
- `with self._lock, self._db:` takes a lock (the server will use several threads) and makes the block one transaction. If the tag insert fails, the bookmark insert is rolled back too.
- All SQL uses `?` placeholders. Never build SQL by joining strings with user input.
- `list` asks the database one extra question per bookmark to get its tags. That is fine for now; step 4 comes back to it.

Tell me when the 5 tests pass and I will write step 2, the HTTP server.
""")

# ---------------------------------------------------------------- turn 2
t.append("""@@@ USER
All 5 pass. Step 2: the HTTP server.
@@@ ASSISTANT
Step 2 adds `server.py`. It does not change `store.py`.

**server.py**

""" + code("python", read("v1", "server.py")) + """

Start it and try it (on Windows use `curl.exe`; put the JSON into a file such as `new.json` and use `-d @new.json` to avoid quoting problems):

""" + code("", """python server.py

curl -s -w " -> HTTP %{http_code}\\n" -X POST http://127.0.0.1:8000/bookmarks -d "{\\"url\\": \\"https://doc.rust-lang.org/book/\\", \\"title\\": \\"The Rust Book\\", \\"tags\\": [\\"Rust\\", \\"learning\\"]}"
curl -s -w " -> HTTP %{http_code}\\n" "http://127.0.0.1:8000/bookmarks?tag=rust"
curl -s -w " -> HTTP %{http_code}\\n" -X DELETE http://127.0.0.1:8000/bookmarks/1""") + """

Real responses from this code (the time differs on your machine):

""" + code("", """POST /bookmarks
  {"id": 1, "url": "https://doc.rust-lang.org/book/", "title": "The Rust Book", "tags": ["learning", "rust"], "created_at": "2026-11-13T00:22:21+00:00"} -> HTTP 201
POST /bookmarks   (same url again)
  {"error": "this url is already saved"} -> HTTP 409
POST /bookmarks   (url "ftp://old.example")
  {"error": "url must start with http:// or https://"} -> HTTP 400
GET /bookmarks?tag=rust
  {"items": [{"id": 1, "url": "https://doc.rust-lang.org/book/", "title": "The Rust Book", "tags": ["learning", "rust"], "created_at": "2026-11-13T00:22:21+00:00"}]} -> HTTP 200
DELETE /bookmarks/1
   -> HTTP 204
DELETE /bookmarks/1   (again)
  {"error": "no such bookmark"} -> HTTP 404""") + """

Why it is written this way:
- Every status code has one meaning: `201` created, `204` deleted (and no body), `400` the request is wrong, `404` unknown path or id, `409` the url already exists.
- `make_handler(store)` returns a handler class that **closes over** the store. `http.server` creates a new handler object for every request, so the store cannot be passed in through `__init__`. A closure is the smallest way to give it the store.
- The list answers with an **object** (`{"items": [...]}`), not a bare array. Later we can add `total` and `limit` without breaking the clients.
- `_read_json` has three guards: a size limit (10,000 bytes), valid JSON, and "must be an object". Every one of them gives a clear 400 instead of a crash.
- `ThreadingHTTPServer` handles requests in separate threads, which is why the store uses a lock.
- Messages for the user say what is wrong; the code never sends a Python traceback to the client.
- `log_message` is silenced to keep the console clean. In a real service you would log method, path, status and time.

Next is step 3: automatic tests for the API. Tell me when the manual calls work.
""")

# ---------------------------------------------------------------- turn 3
t.append("""@@@ USER
Works with curl, the responses look the same as yours. Step 3: automated tests for the API.
@@@ ASSISTANT
The tests start the real server inside the test process on a free port and call it over HTTP. That tests routing, JSON handling and status codes together.

**test_api.py**

""" + code("python", read("v1", "test_api.py")) + """

Run both test files:

""" + code("", "python -m unittest -v") + """

Expected end of the output:

""" + code("", "Ran 9 tests in 0.6s\n\nOK") + """

Points to know about these tests:
- `port=0` asks the operating system for a free port, so the tests never fail because port 8000 is busy. `server.server_address[1]` tells us which one it chose.
- `serve_forever` runs in a **daemon thread**, so the test process can still exit if something goes wrong. `shutdown()` stops the loop, and `server_close()` frees the port.
- `urllib` raises `HTTPError` for every 4xx and 5xx answer. The `call` helper catches it and returns `(status, body)` in both cases, so a test can simply compare the status.
- `test_bad_requests_give_400` covers four different ways to send a bad body: a bad URL, broken JSON, JSON that is not an object, and a body that is too large.
- Every test uses its own URLs. The server and its in-memory database are shared by all tests in this class, so tests must not depend on each other's data.

Step 4 is the last one: pagination, an API key for writes, and a list of what is still missing. Say when you are ready.
""")

# ---------------------------------------------------------------- turn 4
store_changes = methods("v2", "store.py", "BookmarkStore", ["_where", "count", "list"])
test_changes = methods(
    "v2", "test_api.py", "ApiTests",
    ["setUp", "tearDown", "call", "add", "test_writes_need_the_key_but_reads_do_not", "test_pagination", "test_bad_paging_values_give_400"],
)
t.append("""@@@ USER
All 9 pass. Now two things: pagination for the list, and protect the writes with an API key. And tell me what is still missing before this can be used for real.
@@@ ASSISTANT
Design first:
- **Pagination**: `GET /bookmarks?limit=20&offset=0`. `limit` is between 1 and 100 (default 20), `offset` is 0 or more. A wrong value gives `400` with a clear message instead of being quietly corrected. The answer gets `total`, `limit` and `offset`. Because the list was already an object, old clients keep working.
- **API key**: only `POST` and `DELETE` need it, in the header `X-API-Key`. The key comes from the environment variable `BOOKMARKS_KEY`, never from the source code. If it is not set, the server prints a warning and stays open (fine for local use).
- The key is compared with `hmac.compare_digest`, which takes the same time whether the first or the last character is wrong. A normal `==` leaks that information.

**store.py**: replace `list` and add `_where` and `count` (the rest of the file stays the same):

""" + code("python", store_changes) + """

**server.py**: the whole file, because several places change (new imports, `int_param`, `_authorized`, the `GET` branch, and `make_server`):

""" + code("python", read("v2", "server.py")) + """

**test_api.py**: the whole file. The server is now created for every test (so each test starts with an empty database), the helper sends the key, and there are three new tests (`test_writes_need_the_key_but_reads_do_not`, `test_pagination`, `test_bad_paging_values_give_400`):

""" + code("python", read("v2", "test_api.py")) + """

In `test_store.py` add one test for `count`, `limit` and `offset`:

""" + code("python", methods("v2", "test_store.py", "StoreTests", ["test_limit_offset_and_count"])) + """

Run everything:

""" + code("", "python -m unittest -v") + """

Result of the complete project:

""" + code("", "Ran 13 tests in 3.6s\n\nOK") + """

(The tests take a few seconds because `shutdown()` waits for the server loop to notice, once per test.)

Real responses, with the key set to `secret`:

""" + code("", """POST /bookmarks   (no key)
  {"error": "missing or wrong API key"} -> HTTP 401
GET /bookmarks?limit=2&offset=1   (three bookmarks saved)
  {"items": [{"id": 2, "url": "https://site2.example", "title": "Site 2", "tags": ["demo"], "created_at": "2026-11-13T00:22:22+00:00"}, {"id": 1, "url": "https://site1.example", "title": "Site 1", "tags": ["demo"], "created_at": "2026-11-13T00:22:22+00:00"}], "total": 3, "limit": 2, "offset": 1} -> HTTP 200
GET /bookmarks?limit=500
  {"error": "limit must be between 1 and 100"} -> HTTP 400""") + """

Run it with a key:

""" + code("", """set BOOKMARKS_KEY=a-long-random-value        (cmd.exe)
$env:BOOKMARKS_KEY = "a-long-random-value"   (PowerShell)
python server.py""") + """

**What is still missing before real use** (in the order I would do it):
1. **HTTPS.** An API key over plain HTTP can be read by anyone on the network. Put the service behind a reverse proxy (Caddy, nginx) that handles TLS, and keep this server on `127.0.0.1`.
2. **Real logging** of method, path, status and duration (`logging` module), and a catch-all that turns an unexpected exception into a `500` with a short message while the traceback goes to the log. Right now an unexpected error closes the connection without an answer.
3. **Deep pages are slow.** `OFFSET 100000` makes SQLite walk past 100,000 rows. If the list grows large, switch to *keyset* pagination: `WHERE id < ? ORDER BY id DESC LIMIT ?` with the last id of the previous page.
4. **One query per bookmark** to load its tags. With the limit at 100 this is at most 101 small queries, which is acceptable; a single `GROUP_CONCAT` query would remove it.
5. **Backups** of `bookmarks.db` (copy the file while no write is running, or use SQLite's `.backup` command).
6. **One shared key** means no users and no way to revoke one person. If more than one person needs access, store hashed keys or use a proper login.
7. **Browser clients.** A web page on another domain can only call this API if the server sends CORS headers. Add them deliberately, for that one origin only.
8. **Running it as a service** (Windows Service, systemd, or a container) so it starts again after a restart.
9. **Rate limiting** at the proxy, so one client cannot fill the database.

None of these is needed for local use. Items 1, 2 and 5 are the ones I would not skip before putting it on a server.
@@@ END
""")

out = HERE.parent / "claude_longhorizon_bookmarks_11.txt"
out.write_text("\n".join(t), encoding="utf-8")
print("written", out, sum(len(x) for x in t), "chars")

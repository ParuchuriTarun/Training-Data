"""Runs the real servers and prints what curl would show (status after the body)."""
import json
import sys
import threading
import urllib.error
import urllib.request

version = sys.argv[1]
sys.path.insert(0, f"C:/Projects/Mavo/Coding 1 2B/data/staging/proj/{version}")
from server import make_server  # noqa: E402
from store import BookmarkStore  # noqa: E402

key = "secret" if version == "v2" else None
server = make_server(BookmarkStore(), port=0, **({"api_key": key} if key else {}))
base = f"http://127.0.0.1:{server.server_address[1]}"
threading.Thread(target=server.serve_forever, daemon=True).start()


def call(method, path, body=None, with_key=True):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method)
    if key and with_key:
        req.add_header("X-API-Key", key)
    try:
        with urllib.request.urlopen(req) as r:
            text, code = r.read().decode(), r.status
    except urllib.error.HTTPError as e:
        text, code = e.read().decode(), e.code
    print(f"{method} {path}\n  {text} -> HTTP {code}")


if version == "v1":
    call("POST", "/bookmarks", {"url": "https://doc.rust-lang.org/book/", "title": "The Rust Book", "tags": ["Rust", "learning"]})
    call("POST", "/bookmarks", {"url": "https://docs.python.org/3/", "title": "Python docs", "tags": ["python"]})
    call("POST", "/bookmarks", {"url": "https://doc.rust-lang.org/book/", "title": "again"})
    call("POST", "/bookmarks", {"url": "ftp://old.example", "title": "x"})
    call("GET", "/bookmarks?tag=rust")
    call("DELETE", "/bookmarks/2")
    call("DELETE", "/bookmarks/2")
else:
    call("POST", "/bookmarks", {"url": "https://x.example", "title": "X"}, with_key=False)
    for n in range(1, 4):
        call("POST", "/bookmarks", {"url": f"https://site{n}.example", "title": f"Site {n}", "tags": ["demo"]})
    call("GET", "/bookmarks?limit=2&offset=1")
    call("GET", "/bookmarks?limit=500")
server.shutdown()

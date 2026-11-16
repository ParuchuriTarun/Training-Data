"""Turn open-source documentation (MIT / Apache-2.0 / CC0 only) into Mavo training examples.

Usage:   python data/oss_convert.py <source-key> [<source-key> ...]
Output:  open_sources/_out/oss_<key>.txt   (check it, then copy into data/external/)

Every source folder lives in open_sources/ and keeps its own LICENSE file. The list of sources,
their licenses and the exact commits is in data/OPEN_SOURCE_LICENSES.md.
"""
import hashlib
import re
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "open_sources"
OUT = SRC / "_out"

TARGET = 7000      # characters per example (about 1,700 tokens: fits the 2048-token window)
MINIMUM = 600      # smaller pieces are merged into the previous piece or dropped


# --------------------------------------------------------------------------- mdbook includes
INC = re.compile(r"\{\{#(rustdoc_include|include|playground)\s+([^}]+?)\s*\}\}")
ANCHOR_LINE = re.compile(r"^\s*(//|#|--|/\*|<!--)?\s*ANCHOR(_END)?:\s*\S+.*$")


def read_included(base_dir, spec):
    spec = spec.split()[0]
    parts = spec.split(":")
    path = (base_dir / parts[0])
    try:
        lines = path.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
    except Exception:
        return None
    args = parts[1:]
    if not args:
        sel = lines
    elif len(args) == 1 and not args[0].isdigit():
        name = re.escape(args[0])
        sel, on = [], False
        for ln in lines:
            if re.search(rf"ANCHOR:\s*{name}\b", ln):
                on = True
                continue
            if re.search(rf"ANCHOR_END:\s*{name}\b", ln):
                on = False
                continue
            if on:
                sel.append(ln)
        sel = textwrap.dedent("\n".join(sel)).split("\n")
    else:
        a = args[0] if len(args) > 0 else ""
        b = args[1] if len(args) > 1 else ""
        start = int(a) - 1 if a.isdigit() else 0
        end = int(b) if b.isdigit() else (len(lines) if len(args) > 1 or not a.isdigit() else int(a))
        sel = lines[start:end]
    sel = [ln for ln in sel if not ANCHOR_LINE.match(ln)]
    return "\n".join(sel).strip("\n")


def expand_includes(text, base_dir, depth=0):
    def repl(m):
        body = read_included(base_dir, m.group(2))
        if body is None:
            return ""
        if depth < 4 and "{{#" in body:      # included markdown files may include more files
            inner = (base_dir / m.group(2).split()[0].split(":")[0]).parent
            body = expand_includes(body, inner, depth + 1)
        return body
    return INC.sub(repl, text)


# --------------------------------------------------------------------------- cleaning
FENCE = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")
LISTING = re.compile(r"<Listing\b([^>]*)>")
ATTR = re.compile(r"([\w-]+)=\"([^\"]*)\"")


def clean_prose(s):
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)

    def listing(m):
        attrs = dict(ATTR.findall(m.group(1)))
        bits = []
        if "number" in attrs:
            cap = attrs.get("caption", "")
            bits.append(f"Listing {attrs['number']}" + (f": {cap}" if cap else ""))
        if "file-name" in attrs:
            bits.append(f"Filename: {attrs['file-name']}")
        return "\n".join(bits)

    s = LISTING.sub(listing, s)
    s = s.replace("</Listing>", "")
    s = re.sub(r"<span[^>]*>(.*?)</span>", r"\1", s, flags=re.S)
    s = re.sub(r"<img[^>]*>", "", s)
    s = re.sub(r"<a\b[^>]*>\s*</a>", "", s)
    s = re.sub(r"<a\b[^>]*>(.*?)</a>", r"\1", s, flags=re.S)
    s = re.sub(r"\[!\[[^\]]*\]\]\[[^\]]*\]", "", s)                 # [![badge]][link]
    s = re.sub(r"!\[[^\]]*\](\[[^\]]*\]|\([^)]*\))", "", s)         # images
    s = re.sub(r"\[\]\[[^\]]*\]", "", s)
    s = re.sub(r"^\[(?!\^)[^\]\n]+\]:\s+\S+.*$", "", s, flags=re.M)  # link reference lines
    s = re.sub(r"(?<![\w`])\[([^\]]{1,150})\]\[[^\]\n]*\]", lambda m: m.group(1).replace("\n", " "), s)   # [text][ref] -> text
    s = re.sub(r"(?<![\w`])\[([^\]]{1,150})\]\([^)\n]*\)", lambda m: m.group(1).replace("\n", " "), s)   # [text](url) -> text
    s = re.sub(r"\{\{[^}\n]*\}\}", "", s)
    s = re.sub(r"^r\[[\w.\-]+\]\s*$", "", s, flags=re.M)             # rust reference rule ids
    return s


def process(text):
    """Remove hidden lines from rust code, clean prose outside code. Returns cleaned text."""
    out, prose = [], []
    in_fence, fence_char, lang = False, "", ""

    def flush():
        if prose:
            out.append(clean_prose("\n".join(prose)))
            prose.clear()

    for line in text.split("\n"):
        m = FENCE.match(line)
        if m and not in_fence:
            flush()
            in_fence, fence_char, lang = True, m.group(2)[0], m.group(3).strip()
            out.append(line)
            continue
        if m and in_fence and m.group(2)[0] == fence_char and not m.group(3).strip():
            in_fence = False
            out.append(line)
            continue
        if in_fence:
            if lang.startswith("rust"):
                t = line.strip()
                if t == "#" or line.lstrip().startswith("# "):
                    continue
                if line.lstrip().startswith("##"):
                    line = line.replace("##", "#", 1)
            out.append(line)
        else:
            prose.append(line)
    flush()
    s = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", s).strip("\n")


def normalize_fences(text):
    """```rust,editable / ```rust,ignore ... -> ```rust (done after the compile check)."""
    return re.sub(r"^(\s*```)rust[^\n`]*$", r"\1rust", text, flags=re.M)


# --------------------------------------------------------------------------- splitting
HEAD = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def blocks_of(text):
    """Split text into [(level, title, body_text)] at headings (outside code fences)."""
    blocks, cur_level, cur_title, cur = [], 0, "", []
    in_fence, fence_char = False, ""
    for line in text.split("\n"):
        m = FENCE.match(line)
        if m:
            if not in_fence:
                in_fence, fence_char = True, m.group(2)[0]
            elif m.group(2)[0] == fence_char and not m.group(3).strip():
                in_fence = False
        h = None if in_fence else HEAD.match(line)
        if h:
            if cur or cur_title:
                blocks.append((cur_level, cur_title, "\n".join(cur)))
            cur_level, cur_title, cur = len(h.group(1)), h.group(2).strip(), [line]
        else:
            cur.append(line)
    blocks.append((cur_level, cur_title, "\n".join(cur)))
    return [b for b in blocks if b[2].strip()]


def split_paragraphs(text):
    """Cut a long text at blank lines that are outside code fences."""
    pieces, cur, in_fence = [], [], False
    for line in text.split("\n"):
        if FENCE.match(line):
            in_fence = not in_fence
        cur.append(line)
        if not in_fence and line.strip() == "" and sum(len(x) + 1 for x in cur) >= TARGET * 0.6:
            pieces.append("\n".join(cur).strip("\n"))
            cur = []
    if "".join(cur).strip():
        pieces.append("\n".join(cur).strip("\n"))
    return pieces


def chunks_from(text, file_title):
    """Return [(topic, chunk_text)] for one markdown file."""
    blocks = blocks_of(text)
    chunks, cur, cur_title, first = [], [], None, True

    def close():
        nonlocal cur, cur_title, first
        body = "\n".join(cur).strip("\n")
        if body.strip():
            topic = file_title if first else f"{file_title}: {cur_title}" if cur_title else f"{file_title} (continued)"
            chunks.append([topic, body])
        cur, cur_title, first = [], None, False

    for level, title, body in blocks:
        if cur and len("\n".join(cur)) + len(body) > TARGET and (level <= 3 or len("\n".join(cur)) > TARGET * 0.5):
            close()
        if not cur:
            cur_title = title or None
        cur.append(body)
    close()

    out = []
    for topic, body in chunks:
        if len(body) > TARGET * 1.6:
            parts = split_paragraphs(body)
            for i, part in enumerate(parts):
                out.append([topic if i == 0 else f"{topic} (part {i + 1})", part])
        else:
            out.append([topic, body])
    # merge tiny pieces into the previous one
    merged = []
    for topic, body in out:
        if merged and len(body) < MINIMUM and len(merged[-1][1]) + len(body) < TARGET * 1.4:
            merged[-1][1] += "\n\n" + body
        else:
            merged.append([topic, body])
    return [(t, b) for t, b in merged if len(b) >= MINIMUM]


def file_title_of(text, path):
    for level, title, _ in blocks_of(text):
        if title:
            return re.sub(r"[*_`]", "", title).strip()
    return path.stem.replace("_", " ").replace("-", " ")


# --------------------------------------------------------------------------- questions
QUESTIONS = {
    "rust_book": [
        "Explain {t} in Rust.",
        "I am learning Rust. Can you teach me about {t}?",
        "What should I know about {t} in Rust? Please include examples.",
        "Rust question: {t}. How does it work?",
        "Walk me through {t} in Rust.",
        "Help me understand {t} in Rust.",
    ],
    "rust_by_example": [
        "Show me {t} in Rust with working examples.",
        "How do I use {t} in Rust? Give me examples I can run.",
        "Teach me {t} in Rust by example.",
        "Rust: {t}. Explain it and show code.",
    ],
    "rust_api_guidelines": [
        "What are the Rust API design guidelines about {t}?",
        "I am designing a Rust library. What should I know about {t}?",
        "Explain this Rust API guideline: {t}.",
    ],
    "rust_async_book": [
        "Explain {t} in asynchronous Rust.",
        "How does {t} work in async Rust?",
        "Teach me about {t} in async Rust, with code.",
    ],
    "rust_cookbook": [
        "Show me a Rust recipe: {t}.",
        "How do I do this in Rust: {t}?",
        "Give me a working Rust example for: {t}.",
    ],
}

SOURCES = {
    "rust_book": ("rust-lang__book/src", {"SUMMARY.md", "README.md"}),
    "rust_by_example": ("rust-lang__rust-by-example/src", {"SUMMARY.md", "README.md"}),
    "rust_api_guidelines": ("rust-lang__api-guidelines/src", {"SUMMARY.md", "README.md"}),
    "rust_async_book": ("rust-lang__async-book/src", {"SUMMARY.md", "README.md"}),
    "rust_cookbook": ("rust-lang-nursery__rust-cookbook/src", {"SUMMARY.md", "README.md", "about.md", "index.md"}),
}


def safe(text):
    """Make sure nothing in the text can be mistaken for a data marker."""
    return re.sub(r"^@@@", "@ @@", text, flags=re.M)


def write_examples(path, examples):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for q, a in examples:
            f.write(f"@@@ USER\n{safe(q)}\n@@@ ASSISTANT\n{safe(a)}\n@@@ END\n\n")


def convert_md(key):
    rel, skip = SOURCES[key]
    base = SRC / rel
    templates = QUESTIONS[key]
    examples, seen = [], set()
    for p in sorted(base.rglob("*.md")):
        if p.name in skip:
            continue
        text = p.read_text(encoding="utf-8").replace("\r\n", "\n")
        if re.search(r"\{\{#include [^}]*\.md", text):
            continue                       # an overview page that only repeats other pages
        text = expand_includes(text, p.parent)
        text = process(text)
        if len(text) < MINIMUM:
            continue
        title = file_title_of(text, p)
        for topic, body in chunks_from(text, title):
            # drop the heading that repeats the question
            lines = body.split("\n")
            if lines and HEAD.match(lines[0]):
                lines = lines[1:]
            body = "\n".join(lines).strip("\n")
            if len(body) < MINIMUM:
                continue
            idx = int(hashlib.sha1(topic.encode()).hexdigest()[:6], 16) % len(templates)
            q = templates[idx].format(t=topic)
            if q in seen:
                continue
            seen.add(q)
            examples.append((q, body))
    return examples


if __name__ == "__main__":
    for key in sys.argv[1:]:
        if key in SOURCES:
            ex = convert_md(key)
        else:
            raise SystemExit(f"unknown source: {key}")
        target = OUT / f"oss_{key}.txt"
        write_examples(target, ex)
        total = sum(len(q) + len(a) for q, a in ex)
        print(f"{key}: {len(ex)} examples, {total:,} characters -> {target}")

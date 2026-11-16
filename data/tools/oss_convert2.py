"""Second set of converters for open-source repositories (MIT / Apache-2.0 only).

Usage:   python data/oss_convert2.py <key> [<key> ...]
Keys:    rustlings  algo_python  algo_rust  js_questions  clean_code_js  bash_bible
Output:  open_sources/_out/final/oss_<key>.txt

IMPORTANT: this script only READS text. It never runs, imports or compiles code from the downloaded
repositories. These projects test their own code in their own CI (doctests, cargo test, shellcheck);
that is the only verification these examples have. The only check done here is that Python files
are valid Python syntax (ast.parse, which does not run anything).
"""
import ast
import difflib
import hashlib
import re
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import oss_convert as oc  # noqa: E402
from oss_convert import SRC, OUT, write_examples  # noqa: E402

FINAL = OUT / "final"


def pick(templates, key):
    return templates[int(hashlib.sha1(key.encode()).hexdigest()[:6], 16) % len(templates)]


def read(p):
    return p.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


# --------------------------------------------------------------------------- rustlings
def conv_rustlings():
    base = SRC / "rust-lang__rustlings"
    info = tomllib.loads(read(base / "rustlings-macros" / "info.toml"))
    templates = [
        "I am doing a Rust exercise about {t}. It does not compile or its tests fail. How do I fix it?\n\n```rust\n{c}\n```",
        "Fix this Rust program. The topic is {t}.\n\n```rust\n{c}\n```",
        "This Rust code about {t} has errors that I cannot solve. Please repair it and explain the fix.\n\n```rust\n{c}\n```",
    ]
    out = []
    for ex in info["exercises"]:
        name, dirn, hint = ex["name"], ex["dir"], ex.get("hint", "").strip()
        ep = base / "exercises" / dirn / f"{name}.rs"
        sp = base / "solutions" / dirn / f"{name}.rs"
        if not (ep.exists() and sp.exists()):
            continue
        code, sol = read(ep).strip(), read(sp).strip()
        if len(code) > 4500 or len(sol) > 5500 or code == sol:
            continue
        topic = re.sub(r"^\d+_", "", dirn).replace("_", " ")
        sm = difflib.SequenceMatcher(None, code.split("\n"), sol.split("\n"), autojunk=False)
        changes = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            a = " ".join(x.strip() for x in code.split("\n")[i1:i2]).strip()
            b = " ".join(x.strip() for x in sol.split("\n")[j1:j2]).strip()
            if tag == "replace" and a and b and len(a) < 120 and len(b) < 160:
                changes.append(f"- `{a}` became `{b}`.")
            elif tag == "insert" and 0 < len(b) < 160:
                changes.append(f"- Added `{b}`.")
            elif tag == "delete" and 0 < len(a) < 120 and not a.startswith("//"):
                changes.append(f"- Removed `{a}`.")
        parts = []
        if hint:
            parts.append(hint)
        parts.append("Here is a working version:\n\n```rust\n" + sol + "\n```")
        if changes[:8]:
            parts.append("Changes made:\n" + "\n".join(changes[:8]))
        out.append((pick(templates, name).format(t=topic, c=code), "\n\n".join(parts)))
    return out


# --------------------------------------------------------------------------- python algorithms
SKIP_DIRS = {"machine_learning", "neural_network", "computer_vision", "web_programming", "scripts", "docs",
             "project_euler", "audio_filters", "digital_image_processing", "fuzzy_logic", "quantum", "physics",
             "financial", "electronics", "conversions", "blockchain", "knapsack", "scheduling"}
STDLIB = set(sys.stdlib_module_names)


def py_imports_ok(src):
    for m in re.finditer(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", src, re.M):
        mod = (m.group(1) or m.group(2)).split(".")[0]
        if mod not in STDLIB and mod != "__future__":
            return False
    return True


def conv_algo_python():
    base = SRC / "TheAlgorithms__Python"
    per, out = {}, []
    templates = [
        "Write a Python implementation of {t}. Add a docstring and doctests.",
        "How do I implement {t} in Python? Show complete code with examples that run as doctests.",
        "Implement {t} ({c}) in Python, with type hints where they help.",
        "Show me a clean Python version of {t} with tests inside the docstrings.",
    ]
    for p in sorted(base.rglob("*.py")):
        rel = p.relative_to(base)
        if rel.parts[0] in SKIP_DIRS or p.name.startswith("__") or len(rel.parts) < 2:
            continue
        src = read(p)
        if not (500 <= len(src) <= 6500) or "input(" in src or ">>>" not in src or not py_imports_ok(src):
            continue
        try:
            ast.parse(src)                       # syntax check only; nothing is executed
        except SyntaxError:
            continue
        k = rel.parts[0]
        if per.get(k, 0) >= 12:                  # no single topic folder dominates
            continue
        per[k] = per.get(k, 0) + 1
        title, cat = rel.stem.replace("_", " "), rel.parts[0].replace("_", " ")
        q = pick(templates, str(rel)).format(t=title, c=cat)
        m = re.match(r'\s*(?:#[^\n]*\n)*\s*(?:"""|\'\'\')(.*?)(?:"""|\'\'\')', src, re.S)
        if m:
            first = m.group(1).strip().split("\n\n")[0].strip()
            if 20 < len(first) < 500 and ">>>" not in first:
                q += f"\n\nDescription: {first}"
        a = (f"```python\n{src.strip()}\n```\n\n"
             f"The examples in the docstrings are doctests. Run them with `python -m doctest -v {rel.name}`.")
        out.append((q, a))
    return out


# --------------------------------------------------------------------------- rust algorithms
def conv_algo_rust():
    base = SRC / "TheAlgorithms__Rust" / "src"
    per, out = {}, []
    templates = [
        "Implement {t} in Rust ({c}) and include unit tests.",
        "Write {t} in Rust. Add tests that show it works.",
        "How do I code {t} in Rust? Please show the complete file with its tests.",
    ]
    for p in sorted(base.rglob("*.rs")):
        rel = p.relative_to(base)
        if p.name in ("mod.rs", "lib.rs", "main.rs") or len(rel.parts) < 2:
            continue
        src = read(p)
        if not (500 <= len(src) <= 7000) or "#[test]" not in src:
            continue
        if re.search(r"use crate::|extern crate|use (rand|num|nalgebra|serde)\b", src):
            continue
        k = rel.parts[0]
        if per.get(k, 0) >= 10:
            continue
        per[k] = per.get(k, 0) + 1
        title, cat = rel.stem.replace("_", " "), rel.parts[0].replace("_", " ")
        a = (f"```rust\n{src.strip()}\n```\n\n"
             f"Run the tests with `rustc --test {rel.name}` and then run the program it builds, "
             "or with `cargo test` inside a Cargo project.")
        out.append((pick(templates, str(rel)).format(t=title, c=cat), a))
    return out


# --------------------------------------------------------------------------- javascript questions
def conv_js_questions():
    text = read(SRC / "lydiahallie__javascript-questions" / "README.md")
    parts = re.split(r"^###### \d+\.\s*", text, flags=re.M)[1:]
    out = []
    for part in parts:
        title, _, rest = part.partition("\n")
        m = re.search(r"<details><summary><b>Answer</b></summary>\s*<p>\s*#### Answer:\s*(.*?)\n(.*?)</p>\s*</details>",
                      rest, re.S)
        if not m:
            continue
        body = re.sub(r"\n---\s*$", "", rest[:m.start()].strip()).strip()
        letter, expl = m.group(1).strip(), oc.process(m.group(2).strip())
        if len(expl) < 40 or not body:
            continue
        out.append((f"JavaScript quiz: {title.strip()}\n\n{body}", f"Answer: {letter}\n\n{expl}"))
    return out


# --------------------------------------------------------------------------- clean code javascript
def conv_clean_code_js():
    old = oc.TARGET
    oc.TARGET = 3500
    try:
        text = oc.process(read(SRC / "ryanmcdermott__clean-code-javascript" / "README.md"))
        chunks = oc.chunks_from(text, "Clean code in JavaScript")
    finally:
        oc.TARGET = old
    templates = ["What does good clean-code practice say about {t}? Show JavaScript examples.",
                 "Explain this JavaScript clean-code rule with a bad and a good example: {t}.",
                 "How do I write cleaner JavaScript? Topic: {t}."]
    out = []
    for topic, body in chunks:
        lines = body.split("\n")
        if lines and oc.HEAD.match(lines[0]):
            lines = lines[1:]
        body = "\n".join(lines).strip()
        t = re.sub(r"[*]", "", topic.replace("Clean code in JavaScript: ", "").replace("Clean code in JavaScript", "general rules"))
        if len(body) >= 500:
            out.append((pick(templates, topic).format(t=t), body))
    return out


# --------------------------------------------------------------------------- pure bash bible
def conv_bash_bible():
    text = oc.process(read(SRC / "dylanaraps__pure-bash-bible" / "README.md"))
    out = []
    for level, title, body in oc.blocks_of(text):
        if level != 2 or len(body) < 250 or len(body) > 6500:
            continue
        body = "\n".join(body.split("\n")[1:]).strip()
        if not re.search(r"^```(sh|bash|shell)\n", body, re.M):
            continue
        title = re.sub(r"[*_`]", "", title).strip().rstrip(".")
        out.append((f"In Bash, how do I do this without calling external programs: {title}?", body))
    return out


# --------------------------------------------------------------------------- generic documentation pages
def clean_mdx(text):
    """Remove front matter, imports and component tags from .mdx pages. Returns (title, text)."""
    title = ""
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if m:
        t = re.search(r"^title:\s*(.+)$", m.group(1), re.M)
        title = t.group(1).strip().strip("'\"") if t else ""
        text = text[m.end():]
    out, in_fence = [], False
    for line in text.split("\n"):
        if oc.FENCE.match(line):
            in_fence = not in_fence
            if in_fence:                                    # ```rust title="x" ins={2} -> ```rust
                line = re.sub(r"^(\s*`{3,}\w*)\b.*$", r"\1", line)
            out.append(line)
            continue
        if not in_fence and re.match(r"^(import|export)\s", line):
            continue
        out.append(line)
    text = "\n".join(out)
    text = re.sub(r"^:::(note|tip|caution|danger|warning)(?:\[([^\]]*)\])?\s*$",
                  lambda m: f"**{(m.group(2) or m.group(1)).capitalize()}:**", text, flags=re.M)
    text = re.sub(r"^:::\s*$", "", text, flags=re.M)
    text = re.sub(r'<TabItem\s+label="([^"]*)"[^>]*>', r"**\1**", text)
    text = re.sub(r"</?[A-Z]\w*\b[^<>]*?/?>", "", text, flags=re.S)
    return title, text


def conv_docs(base, pattern, templates, skip_parts=(), skip_names=(), mdx=False, drop_topic=None, target=None):
    old = oc.TARGET
    if target:
        oc.TARGET = target
    out, seen = [], set()
    try:
        for p in sorted(base.rglob(pattern)):
            rel_parts = set(p.relative_to(base).parts)
            if rel_parts & set(skip_parts) or p.name in skip_names:
                continue
            text = read(p)
            title = ""
            if mdx:
                title, text = clean_mdx(text)
            text = re.sub(r"(?im)^.*\b(pre|post)-?lecture quiz\b.*$", "", text)
            text = re.sub(r"(?im)^>?\s*sketchnote by.*$", "", text)
            text = oc.process(text)
            if len(text) < oc.MINIMUM:
                continue
            file_title = title or oc.file_title_of(text, p)
            for topic, body in oc.chunks_from(text, file_title):
                if drop_topic and re.search(drop_topic, topic, re.I):
                    continue
                lines = body.split("\n")
                if lines and oc.HEAD.match(lines[0]):
                    lines = lines[1:]
                body = "\n".join(lines).strip()
                if len(body) < oc.MINIMUM:
                    continue
                q = pick(templates, topic).format(t=re.sub(r"[*]", "", topic))
                if q not in seen:
                    seen.add(q)
                    out.append((q, body))
    finally:
        oc.TARGET = old
    return out


def conv_webdev_beginners():
    base = SRC / "microsoft__Web-Dev-For-Beginners"
    templates = ["Teach me {t} as a beginner web developer.",
                 "I am learning web development. Explain {t} with examples.",
                 "Walk me through {t} step by step, the way a web development course would.",
                 "Web development lesson: {t}. What do I need to know?"]
    return conv_docs(base, "README.md", templates,
                     skip_parts={"translations", "solution", "start", "node_modules", "quiz-app", "docs",
                                 "sketchnotes", "images", "teaching-files", "pdf", "lesson-template"},
                     drop_topic=r"quiz|assignment|credits|disclaimer|self[- ]study|educators")


def conv_tauri_docs():
    base = SRC / "tauri-apps__tauri-docs" / "src" / "content" / "docs"
    templates = ["Explain {t} in Tauri.",
                 "I am building a desktop or mobile app with Tauri and Rust. How does {t} work?",
                 "Tauri: {t}. Please explain it with examples."]
    return conv_docs(base, "*.md*", templates, skip_parts={"_fragments"}, mdx=True)


def conv_airbnb_js():
    base = SRC / "airbnb__javascript"
    templates = ["What does the Airbnb JavaScript style guide say about {t}? Show good and bad examples.",
                 "Explain this JavaScript style rule with a bad and a good example: {t}.",
                 "How should I write {t} in modern JavaScript?"]
    return conv_docs(base, "README.md", templates, skip_parts={"packages", "linters", "css-in-javascript", "react"},
                     target=3500)


CONVERTERS = {"rustlings": conv_rustlings, "algo_python": conv_algo_python, "algo_rust": conv_algo_rust,
              "js_questions": conv_js_questions, "clean_code_js": conv_clean_code_js, "bash_bible": conv_bash_bible,
              "webdev_beginners": conv_webdev_beginners, "tauri_docs": conv_tauri_docs, "airbnb_js": conv_airbnb_js}

if __name__ == "__main__":
    FINAL.mkdir(parents=True, exist_ok=True)
    for key in sys.argv[1:]:
        ex = CONVERTERS[key]()
        seen, uniq = set(), []
        for q, a in ex:
            if q not in seen:
                seen.add(q)
                uniq.append((q, a))
        write_examples(FINAL / f"oss_{key}.txt", uniq)
        print(f"{key}: {len(uniq)} examples, {sum(len(q) + len(a) for q, a in uniq):,} characters")

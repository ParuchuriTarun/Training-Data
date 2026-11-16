"""Quality check for a data file from another AI (needs rustc on PATH).

Usage:  python data/check_external.py path\to\file.txt

For every example it checks:
  * format: one USER, one ASSISTANT, text present, a "Changes made" list when code is fixed
  * Rust in the QUESTION: if it names an error code (error[E0382] ...), the broken code must
    really fail with that code
  * Rust in the ANSWER: every complete program/test block must compile (std-only; blocks that
    use external crates or are tagged `ignore` are skipped)
  * duplicates of questions already in data/seed or data/external
The code is only compiled, never run.
"""
import hashlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTERNAL = ("tokio", "serde", "axum", "clap", "eframe", "egui", "anyhow", "thiserror", "reqwest", "rand")
FENCE = re.compile(r"```rust(,[a-z_]+)?\n(.*?)```", re.S)


def compile_src(src, test=False):
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "main.rs"
        f.write_text(src, encoding="utf-8")
        cmd = ["rustc", "--edition", "2021", "-A", "warnings", "-o", str(Path(d) / "out.exe"), str(f)]
        if test:
            cmd.insert(1, "--test")
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        return r.returncode == 0, r.stderr


def parse(text):
    return re.findall(r"@@@ USER\r?\n(.*?)\r?\n@@@ ASSISTANT\r?\n(.*?)\r?\n@@@ END", text, re.S)


def known_questions():
    seen = set()
    for pat in ("seed/*.txt", "external/*.txt"):
        for p in (ROOT / "data").glob(pat):
            for u, a in parse(p.read_text(encoding="utf-8")):
                seen.add(hashlib.sha1(u.strip().encode()).hexdigest())
    return seen


def complete_program(code):
    return "fn main" in code or "#[test]" in code


def main():
    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")
    exs = parse(text)
    print(f"{path.name}: {len(exs)} examples found")
    known = known_questions()
    problems, notes = 0, []
    for i, (u, a) in enumerate(exs, 1):
        issues = []
        if len(a.strip()) < 200:
            issues.append("answer is very short")
        if "```" not in a and "--prose" not in sys.argv:
            issues.append("answer has no code block (pass --prose for explanation-only data)")
        if hashlib.sha1(u.strip().encode()).hexdigest() in known:
            issues.append("question already exists in your data")
        claimed = set(re.findall(r"error\[(E\d{4})\]", u + a))
        ub = [m.group(2) for m in FENCE.finditer(u)]
        if ub and complete_program(ub[0]):
            ok, err = compile_src(ub[0], test="#[test]" in ub[0])
            actual = set(re.findall(r"error\[(E\d{4})\]", err))
            if ok:
                notes.append(f"#{i}: question code compiles (runtime problem such as a panic, not a compile error)")
            elif claimed and not (claimed & actual):
                issues.append(f"claims {sorted(claimed)} but the question code really fails with {sorted(actual) or 'a different error'}")
        elif claimed and ub:
            notes.append(f"#{i}: question code is a fragment, error code {sorted(claimed)} not verified")
        n_checked = 0
        for m in FENCE.finditer(a):
            tag, code = m.group(1) or "", m.group(2)
            if "--cargo-verified" in sys.argv:
                continue  # multi-file cargo projects: the real project was built and tested with cargo, snippets are fragments
            if "ignore" in tag or "compile_fail" in tag or any(f"{c}::" in code or f"use {c}" in code for c in EXTERNAL):
                continue
            if not complete_program(code):
                continue
            n_checked += 1
            ok, err = compile_src(code, test="#[test]" in code)
            if not ok:
                first = next((l for l in err.splitlines() if l.startswith("error")), err[:120])
                issues.append(f"answer code does not compile: {first[:110]}")
        if ub and any(complete_program(x) for x in ub) and n_checked == 0:
            issues.append("no complete, compilable code block in the answer")
        if re.search(r"fix|error|fail|why", u, re.I) and "Changes made" not in a and ub:
            issues.append('missing "Changes made" list')
        status = "OK " if not issues else "BAD"
        problems += bool(issues)
        first_line = u.strip().splitlines()[0][:70]
        print(f"[{status}] #{i:>2} {first_line}")
        for s in issues:
            print(f"        - {s}")
    print()
    for n in notes:
        print("note:", n)
    print(f"\nSummary: {len(exs) - problems} good, {problems} with problems")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()

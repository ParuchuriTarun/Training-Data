"""Verify the Rust examples with the real compiler (needs rustc on PATH).

1. Every entry in data/generators/gen_rust_errors.py: the broken code must fail with the stated
   error code, and the fixed code must compile.
2. Every ```rust block in data/seed/*.txt and data/external/*.txt that only uses the standard
   library (no external crates, no `ignore` tag) must compile (tests are checked with --test).

Run:  python data/verify_rust.py
"""
import importlib.util
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTERNAL_CRATES = ("tokio", "serde", "axum", "clap", "eframe", "egui", "anyhow", "thiserror", "reqwest", "rand")


def compile_src(src, test=False):
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "main.rs"
        f.write_text(src, encoding="utf-8")
        cmd = ["rustc", "--edition", "2021", "-A", "warnings", "-o", str(Path(d) / "out.exe"), str(f)]
        if test:
            cmd.insert(1, "--test")
        r = subprocess.run(cmd, capture_output=True, text=True)
        return r.returncode == 0, r.stderr


def main():
    bad_total = 0
    spec = importlib.util.spec_from_file_location("g", ROOT / "data" / "generators" / "gen_rust_errors.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for e in mod.ENTRIES:
        ok_bad, err = compile_src(e["bad"])
        ok_fix, err2 = compile_src(e["fixed"])
        has_code = f"error[{e['code']}]" in err
        status = "OK " if (not ok_bad and has_code and ok_fix) else "BAD"
        if status == "BAD":
            bad_total += 1
        print(f"[{status}] {e['code']}: bad fails={not ok_bad} code_matches={has_code} fixed_compiles={ok_fix}")
        if status == "BAD":
            print("   ", (err if not has_code or ok_bad else err2)[:400].replace("\n", "\n    "))

    texts = []
    for pat in ("seed/*.txt", "external/*.txt"):
        texts += list((ROOT / "data").glob(pat))
    checked = 0
    for p in texts:
        full = p.read_text(encoding="utf-8")
        # only check the ASSISTANT answers (user questions may contain deliberately broken code)
        content = "\n".join(re.findall(r"@@@ ASSISTANT\n(.*?)@@@ END", full, re.S))
        for m in re.finditer(r"```rust(,[a-z_]+)?\n(.*?)```", content, re.S):
            tag, code = m.group(1) or "", m.group(2)
            if "ignore" in tag or any(f"{c}::" in code or f"use {c}" in code for c in EXTERNAL_CRATES):
                continue
            if "fn main" not in code and "#[cfg(test)]" not in code:
                continue
            ok, err = compile_src(code, test="#[test]" in code)
            checked += 1
            if not ok:
                bad_total += 1
                print(f"[BAD] {p.name}: block starting {code.strip().splitlines()[0][:60]!r}")
                print("   ", err[:500].replace("\n", "\n    "))
    print(f"\nChecked {len(mod.ENTRIES)} error entries and {checked} code blocks. Problems: {bad_total}")
    sys.exit(1 if bad_total else 0)


if __name__ == "__main__":
    main()

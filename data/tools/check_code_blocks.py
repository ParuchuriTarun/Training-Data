"""Syntax-check the code blocks inside example files (never runs the code).

Usage:  python data/check_code_blocks.py <file-or-folder> [--json out.json]

Checks, when the tool exists on this computer:
  python / py        -> ast.parse
  json               -> json.loads
  js / javascript    -> node --check (as an ES module)
  ts / typescript    -> node --check (Node's built-in TypeScript type stripping)
  bash / sh          -> bash -n
  powershell / ps1   -> PowerShell parser
  rust               -> rustc, only for complete programs (fn main / tests), std-only
Blocks that are obviously fragments (diffs, a line with only '...', jsx/tsx, sql, css, html, yaml) are skipped.
A failure is a SIGNAL for review: short fragments can fail for harmless reasons.
"""
import ast
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from mavo.data import parse_txt  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

FENCE = re.compile(r"^```([\w+#-]*)[^\n]*\n(.*?)^```", re.S | re.M)
NODE, BASH = shutil.which("node"), shutil.which("bash")
RUSTC = shutil.which("rustc")
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")
EXT_CRATES = ("tokio", "serde", "axum", "clap", "eframe", "egui", "anyhow", "thiserror", "reqwest", "rand")


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60, **kw)


def is_fragment(code):
    lines = [l for l in code.splitlines() if l.strip()]
    if not lines:
        return True
    if any(l.strip() in ("...", "// ...", "# ...", "/* ... */") for l in lines):
        return True
    if sum(l.startswith(("+", "-", "@@")) for l in lines) > len(lines) // 2 and len(lines) > 2:
        return True  # diff
    return False


def check_block(lang, code):
    """Return None if ok/skipped, or a short error string."""
    lang = lang.lower()
    if is_fragment(code):
        return None
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        if lang in ("python", "py"):
            try:
                ast.parse(code)
            except SyntaxError as e:
                return f"python syntax error line {e.lineno}: {e.msg}"
        elif lang == "json":
            try:
                json.loads(code)
            except Exception as e:
                return f"json error: {str(e)[:80]}"
        elif lang in ("js", "javascript", "mjs") and NODE:
            f = d / "x.mjs"
            f.write_text(code, encoding="utf-8")
            r = run([NODE, "--check", str(f)])
            if r.returncode and "Unexpected token '<'" not in r.stderr:  # '<' = JSX inside a js block: fine
                return "js syntax: " + next((l for l in r.stderr.splitlines() if "Error" in l), r.stderr[:100]).strip()[:110]
        elif lang in ("ts", "typescript") and NODE:
            f = d / "x.ts"
            f.write_text(code, encoding="utf-8")
            r = run([NODE, "--disable-warning=ExperimentalWarning", str(Path(__file__).with_name("check_ts.mjs")), str(f)])
            if r.returncode:
                return "ts syntax: " + (r.stderr.strip().splitlines() or ["error"])[-1][:110]
        elif lang in ("bash", "sh", "shell") and BASH:
            r = run([BASH, "-n"], input=code.replace("\r\n", "\n") + "\n")
            if r.returncode:
                return "bash syntax: " + (r.stderr.strip().splitlines() or ["error"])[-1][:110]
        elif lang in ("powershell", "ps1", "pwsh") and POWERSHELL:
            f = d / "x.ps1"
            f.write_text(code, encoding="utf-8")
            script = ("$e=$null;$t=$null;[void][System.Management.Automation.Language.Parser]::ParseFile('%s',[ref]$t,[ref]$e);"
                      "if($e){$e[0].Message;exit 1}" % str(f))
            r = run([POWERSHELL, "-NoProfile", "-Command", script])
            if r.returncode:
                return "powershell syntax: " + r.stdout.strip()[:110]
        elif lang == "rust" and RUSTC:
            if ("fn main" not in code and "#[test]" not in code) or any(f"{c}::" in code or f"use {c}" in code for c in EXT_CRATES):
                return None
            f = d / "main.rs"
            f.write_text(code, encoding="utf-8")
            cmd = [RUSTC, "--edition", "2021", "-A", "warnings", "-o", str(d / "o.exe"), str(f)]
            if "#[test]" in code:
                cmd.insert(1, "--test")
            r = run(cmd)
            if r.returncode:
                return "rust: " + next((l for l in r.stderr.splitlines() if l.startswith("error")), "compile error")[:110]
    return None


def main():
    target = Path(sys.argv[1])
    files = sorted(p for p in ([target] if target.is_file() else target.rglob("*.txt")) if "_scratch" not in p.parts)
    out, n_checked, n_bad = [], 0, 0
    print(f"tools: node={bool(NODE)} bash={bool(BASH)} rustc={bool(RUSTC)} powershell={bool(POWERSHELL)}")
    for p in files:
        for i, (u, a) in enumerate(parse_txt(p.read_text(encoding="utf-8", errors="replace")), 1):
            for m in FENCE.finditer(a):
                lang, code = m.group(1), m.group(2)
                err = check_block(lang, code)
                if lang.lower() in ("python", "py", "json", "js", "javascript", "mjs", "ts", "typescript", "bash", "sh", "shell",
                                    "powershell", "ps1", "rust") and not is_fragment(code):
                    n_checked += 1
                if err:
                    n_bad += 1
                    first = next((l for l in code.splitlines() if l.strip()), "")[:70]
                    out.append({"file": str(p.relative_to(target) if target.is_dir() else p.name), "n": i, "lang": lang,
                                "error": err, "first_line": first})
    for o in out:
        print(f"[{o['lang']:>10}] {o['file']} #{o['n']}: {o['error']}   | {o['first_line']}")
    print(f"\nChecked {n_checked} code blocks, {n_bad} with a syntax problem (review each; fragments can fail harmlessly)")
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()

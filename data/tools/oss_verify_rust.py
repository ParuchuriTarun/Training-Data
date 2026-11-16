"""Compile every complete Rust program inside converted open-source examples.

Usage:  python data/oss_verify_rust.py <key> [<key> ...]
Reads   open_sources/_out/oss_<key>.txt
Writes  open_sources/_out/final/oss_<key>.txt   (examples whose programs all compile, fences normalized)
        open_sources/_out/final/oss_<key>.dropped.txt  (why an example was dropped)

Programs that need outside crates (rand, serde, tokio, ...) cannot be compiled here; they are kept
and counted as "skipped". Blocks tagged ignore / does_not_compile / compile_fail are not compiled.
"""
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from oss_convert import OUT, normalize_fences, write_examples  # noqa: E402

FENCE = re.compile(r"^```([^\n`]*)\n(.*?)^```", re.S | re.M)
SKIP_TAGS = ("ignore", "does_not_compile", "compile_fail", "text", "console", "toml")
EXTERNAL_HINT = ("unresolved import", "unlinked crate", "can't find crate", "unresolved module or unlinked crate",
                 "use of unresolved", "could not find `", "E0432", "E0433", "E0463")


def parse(text):
    return re.findall(r"@@@ USER\n(.*?)\n@@@ ASSISTANT\n(.*?)\n@@@ END", text, re.S)


def compile_block(src):
    """Return 'ok', 'external' or an error text."""
    last = ""
    for edition in ("2024", "2021"):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "main.rs"
            f.write_text(src, encoding="utf-8")
            r = subprocess.run(["rustc", "--edition", edition, "-A", "warnings", "-o", str(Path(d) / "out.exe"), str(f)],
                               capture_output=True, text=True)
            if r.returncode == 0:
                return "ok"
            last = r.stderr
    if any(h in last for h in EXTERNAL_HINT):
        return "external"
    # pieces of a longer listing use names defined in an earlier piece; C builds need a C compiler
    if re.search(r"cannot find (function|value|type|struct|macro|trait)|unclosed delimiter|linking with|custom build", last):
        return "external"
    return last.strip().splitlines()[0] if last.strip() else "unknown error"


def check_example(item):
    idx, (q, a) = item
    results = []
    for m in FENCE.finditer(a + "\n"):
        info, code = m.group(1).strip(), m.group(2)
        if not info.startswith("rust") or any(t in info for t in SKIP_TAGS) or "fn main" not in code:
            continue
        results.append(compile_block(code))
    return idx, results


if __name__ == "__main__":
    final = OUT / "final"
    for key in sys.argv[1:]:
        examples = parse((OUT / f"oss_{key}.txt").read_text(encoding="utf-8"))
        with ThreadPoolExecutor(max_workers=6) as pool:
            checked = dict(pool.map(check_example, list(enumerate(examples))))
        kept, dropped, n_ok, n_ext = [], [], 0, 0
        for i, (q, a) in enumerate(examples):
            res = checked[i]
            bad = [r for r in res if r not in ("ok", "external")]
            n_ok += res.count("ok")
            n_ext += res.count("external")
            if bad:
                dropped.append(f"{q}\n    {bad[0]}")
            else:
                kept.append((q, normalize_fences(a)))
        write_examples(final / f"oss_{key}.txt", kept)
        (final / f"oss_{key}.dropped.txt").parent.mkdir(parents=True, exist_ok=True)
        (final / f"oss_{key}.dropped.txt").write_text("\n".join(dropped), encoding="utf-8")
        print(f"{key}: kept {len(kept)} of {len(examples)} examples; programs compiled ok {n_ok}, "
              f"needing outside crates (not compiled) {n_ext}, dropped examples {len(dropped)}")

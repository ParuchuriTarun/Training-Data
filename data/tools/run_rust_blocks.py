"""Compile AND RUN the complete Rust programs in a data file's answers, and print what they output.
Used to confirm that any 'Expected output' written in an answer is true.

Usage:  python data/run_rust_blocks.py <file.txt> [example numbers...]
Programs read stdin from an empty input and are stopped after 20 seconds.
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

FENCE = "`" * 3


def main():
    path = Path(sys.argv[1])
    wanted = {int(x) for x in sys.argv[2:]}
    text = path.read_text(encoding="utf-8")
    ex = re.findall(r"@@@ USER\r?\n(.*?)\r?\n@@@ ASSISTANT\r?\n(.*?)\r?\n@@@ END", text, re.S)
    pattern = re.compile(FENCE + r"rust\n(.*?)" + FENCE, re.S)
    for n, (_, ans) in enumerate(ex, 1):
        if wanted and n not in wanted:
            continue
        for code in pattern.findall(ans):
            if "fn main" not in code:
                continue
            d = Path(tempfile.mkdtemp())
            (d / "m.rs").write_text(code, encoding="utf-8")
            if "#[test]" in code:  # also build and run the unit tests of this block
                t = subprocess.run(["rustc", "--edition", "2021", "--test", "-A", "warnings", "-o", str(d / "t.exe"), str(d / "m.rs")],
                                   capture_output=True, text=True)
                if t.returncode:
                    print(f"--- example {n}: TEST COMPILE FAIL\n{t.stderr[:400]}")
                else:
                    tr = subprocess.run([str(d / "t.exe")], capture_output=True, text=True, timeout=60)
                    print(f"--- example {n} tests (exit {tr.returncode})\n{tr.stdout[-400:]}")
            r = subprocess.run(["rustc", "--edition", "2021", "-A", "warnings", "-o", str(d / "m.exe"), str(d / "m.rs")],
                               capture_output=True, text=True)
            if r.returncode:
                print(f"--- example {n}: COMPILE FAIL\n{r.stderr[:400]}")
                continue
            try:
                p = subprocess.run([str(d / "m.exe")], capture_output=True, text=True, timeout=20, input="")
                print(f"--- example {n}\n{p.stdout[:700]}{p.stderr[:200]}")
            except subprocess.TimeoutExpired:
                print(f"--- example {n}: TIMEOUT")


if __name__ == "__main__":
    main()

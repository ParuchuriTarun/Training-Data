"""Run the complete ```python blocks in a data file's answers and print their output, so any
'Output:' written in an answer can be compared with what Python really prints.

Usage:  python data/run_py_blocks.py <file.txt> [example numbers...]
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

FENCE = "`" * 3


def main():
    text = Path(sys.argv[1]).read_text(encoding="utf-8")
    wanted = {int(x) for x in sys.argv[2:]}
    ex = re.findall(r"@@@ USER\r?\n(.*?)\r?\n@@@ ASSISTANT\r?\n(.*?)\r?\n@@@ END", text, re.S)
    pat = re.compile(FENCE + r"python\n(.*?)" + FENCE, re.S)
    for n, (_, ans) in enumerate(ex, 1):
        if wanted and n not in wanted:
            continue
        for code in pat.findall(ans):
            f = Path(tempfile.mkdtemp()) / "t.py"
            f.write_text(code, encoding="utf-8")
            r = subprocess.run([sys.executable, "-I", str(f)], capture_output=True, text=True, timeout=30, input="")
            print(f"--- example {n} (exit {r.returncode})\n{r.stdout[:600]}{r.stderr[-300:]}")


if __name__ == "__main__":
    main()

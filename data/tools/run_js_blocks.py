"""Run the ```js blocks of the chosen examples with Node and print their output, so any 'Output:' in an
answer can be compared with what Node really prints. Only pick examples that do not use the browser (DOM).

Usage:  python data/run_js_blocks.py <file.txt> <example numbers...>
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
    pat = re.compile(FENCE + r"js\n(.*?)" + FENCE, re.S)
    for n, (_, ans) in enumerate(ex, 1):
        if n not in wanted:
            continue
        for code in pat.findall(ans):
            f = Path(tempfile.mkdtemp()) / "t.js"
            f.write_text(code, encoding="utf-8")
            r = subprocess.run(["node", str(f)], capture_output=True, text=True, timeout=30)
            print(f"--- example {n} (exit {r.returncode})\n{r.stdout[:900]}{r.stderr[-300:]}")


if __name__ == "__main__":
    main()

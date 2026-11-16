import re
import subprocess
import tempfile
from pathlib import Path

t = (Path(__file__).resolve().parent.parent / "claude_longhorizon_markdown_12.txt").read_text(encoding="utf-8")
F = "`" * 3
blocks = re.findall(F + r"rust(,[a-z_]+)?\n(.*?)" + F, t, re.S)
print(len(blocks), "rust blocks")
for i, (_, b) in enumerate(blocks):
    d = Path(tempfile.mkdtemp())
    f = d / "b.rs"
    f.write_text(b, encoding="utf-8")
    r = subprocess.run(["rustc", "--edition", "2021", "--crate-type", "lib", str(f), "-o", str(d / "b.rlib"), "-A", "warnings"], capture_output=True, text=True)
    first = next((l for l in r.stderr.splitlines() if l.startswith("error")), "ok" if r.returncode == 0 else "?")
    print(i, len(b), b.strip().splitlines()[0][:50], "->", first[:90])

import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAMPLE = """# Release notes

The tool is *fast*, and `md --page` makes a **full page**.
See [the docs](https://example.com/docs) or [bad](javascript:alert(1)).

- converts headings
- converts lists

```rust
fn main() { println!("<hi>"); }
```
"""
BUG = "Total: 5 * 3 * 2 = 30\n"
NEW = "> Quote *here*\n\n1. first\n2. second\n"

d = Path(tempfile.mkdtemp(prefix="mdd_"))
for v in ("v3", "v4"):
    exe = d / f"md_{v}.exe"
    c = subprocess.run(["rustc", "--edition", "2021", str(HERE / f"md_{v}.rs"), "-o", str(exe), "-A", "dead_code"], capture_output=True, text=True)
    print("#####", v, "compile", c.returncode, c.stderr[:500])
    def run(args, text):
        r = subprocess.run([str(exe)] + args, input=text, capture_output=True, text=True, encoding="utf-8")
        return r.stdout, r.stderr, r.returncode
    if v == "v3":
        print("--- sample"); print(run([], SAMPLE)[0])
        print("--- sample --page"); print(run(["--page"], SAMPLE)[0])
        print("--- bug:"); print(run([], BUG)[0])
        print("--- missing file:", run(["nope.md"], "")[1:], )
        print("--- bad option:", run(["--zzz"], "")[1:])
    else:
        print("--- bug fixed:"); print(run([], BUG)[0])
        print("--- new blocks:"); print(run([], NEW)[0])

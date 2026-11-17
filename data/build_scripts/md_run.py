"""Assemble each version of md.rs, compile it with its tests and run them."""
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from md_pieces import VERSIONS, assemble  # noqa: E402

wanted = sys.argv[1:] or list(VERSIONS)
for name in wanted:
    d = Path(tempfile.mkdtemp(prefix="md_"))
    src = d / "md.rs"
    src.write_text(assemble(VERSIONS[name]), encoding="utf-8")
    (HERE / f"md_{name}.rs").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    exe = d / "md_test.exe"
    c = subprocess.run(["rustc", "--edition", "2021", "--test", str(src), "-o", str(exe), "-A", "dead_code"],
                       capture_output=True, text=True)
    print(f"##### {name}: compile exit {c.returncode}")
    if c.returncode:
        print(c.stderr[:3000])
        continue
    r = subprocess.run([str(exe)], capture_output=True, text=True, timeout=120)
    print("\n".join(l for l in r.stdout.splitlines() if l.strip())[-1800:])
    print(r.stderr[-500:])

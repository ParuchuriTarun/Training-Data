"""Print, for each clone in open_sources/, the licence files found and their first meaningful lines."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "open_sources"
for d in sorted(p for p in ROOT.iterdir() if p.is_dir() and not p.name.startswith("_")):
    print("=" * 70)
    print(d.name)
    files = [f for f in d.iterdir() if f.is_file() and f.name.upper().startswith(("LICENSE", "LICENCE", "COPYING"))]
    if not files:
        print("  (no top-level licence file)")
    for f in sorted(files):
        lines = [l.strip() for l in f.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
        print(f"  {f.name}: {' | '.join(lines[:3])[:160]}")
        for l in lines:
            if l.lower().startswith("copyright"):
                print("     ", l[:140])
                break

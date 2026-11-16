"""Audit a folder of example files (the same @@@ USER / @@@ ASSISTANT / @@@ END format).

Usage:  python data/audit_training_data.py <folder> [--json report.json]

For every example it measures simple, objective quality signals and flags problems:
  parse    markers that the real loader (mavo.data.parse_txt) does not turn into an example
  short    very short answer
  fence    unbalanced ``` code fences (usually a truncated answer)
  cut      answer ends in the middle of a sentence or code
  filler   chatty filler ("Sure!", "Great question", "As an AI ...")
  todo     placeholders such as TODO, lorem ipsum, "// ...", "your code here"
  mojibake broken characters (encoding damage)
  dup      same question (or same answer) seen earlier in this folder or in data/seed|external
"""
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from mavo.data import parse_txt  # noqa: E402

FILLER = re.compile(r"^(sure|certainly|of course|absolutely|great question|good question|happy to help)\b|"
                    r"\bas an ai\b|\bi'?m (just )?an ai\b|\blanguage model\b|\bi hope this helps\b|\blet me know if you\b",
                    re.I | re.M)
TODO = re.compile(r"\bTODO\b|lorem ipsum|your code here|//\s*\.\.\.|#\s*\.\.\.|/\*\s*\.\.\.\s*\*/|\bfoo\s*bar\s*baz\b|<insert|\[insert", re.I)
MOJI = re.compile("Ã.|â€|ï¿½|�")
FENCE_LANG = re.compile(r"^```(\w[\w+#-]*)?", re.M)


def key(s):
    return hashlib.sha1(re.sub(r"\s+", " ", s.strip().lower()).encode()).hexdigest()


def existing_keys():
    qs, ans = set(), set()
    for pat in ("seed/*.txt", "external/*.txt"):
        for p in (ROOT / "data").glob(pat):
            for u, a in parse_txt(p.read_text(encoding="utf-8")):
                qs.add(key(u))
                ans.add(key(a))
    return qs, ans


def ends_cut(a):
    t = a.rstrip()
    if not t:
        return True
    if t.count("```") % 2:
        return True
    last = t.splitlines()[-1].strip()
    if last.startswith("```"):
        return False
    return not re.search(r"[.!?:)\]}`\"'*>]$|\d$", last) and not re.match(r"^(\d+[.)]|[-*]|#)", last) and len(last) > 25


def main():
    folder = Path(sys.argv[1])
    out_json = None
    if "--json" in sys.argv:
        out_json = Path(sys.argv[sys.argv.index("--json") + 1])
    ex_q, ex_a = existing_keys()
    seen_q, seen_a = {}, {}
    report, per_file = [], []
    files = sorted(p for p in folder.rglob("*.txt") if "_scratch" not in p.parts)
    for p in files:
        text = p.read_text(encoding="utf-8", errors="replace")
        n_markers = len(re.findall(r"(?m)^@@@ USER\s*$", text))
        exs = parse_txt(text)
        flags_count = Counter()
        lens = []
        for i, (u, a) in enumerate(exs, 1):
            flags = []
            if len(a) < 120:
                flags.append("short")
            if a.count("```") % 2 or u.count("```") % 2:
                flags.append("fence")
            elif ends_cut(a):
                flags.append("cut")
            if FILLER.search(a):
                flags.append("filler")
            if TODO.search(a):
                flags.append("todo")
            if MOJI.search(u + a):
                flags.append("mojibake")
            ku, ka = key(u), key(a)
            where = seen_q.get(ku) or seen_a.get(ka)
            if where:
                flags.append("dup:in-folder")
            elif ku in ex_q or ka in ex_a:
                flags.append("dup:existing")
            seen_q.setdefault(ku, f"{p.name}#{i}")
            seen_a.setdefault(ka, f"{p.name}#{i}")
            for f in flags:
                flags_count[f.split(":")[0]] += 1
            lens.append(len(a))
            report.append({"file": str(p.relative_to(folder)), "n": i, "flags": flags,
                           "user_len": len(u), "asst_len": len(a), "user": u[:90].replace("\n", " ")})
        per_file.append((p.relative_to(folder), n_markers, len(exs), sorted(lens)[len(lens) // 2] if lens else 0,
                         dict(flags_count)))
    print(f"{'file':34} {'markers':>7} {'parsed':>6} {'med.ans':>7}  flags")
    for f, m, n, med, fc in per_file:
        miss = "  <-- loader dropped " + str(m - n) if m != n else ""
        print(f"{str(f):34} {m:>7} {n:>6} {med:>7}  {fc}{miss}")
    tot = len(report)
    bad = sum(1 for r in report if r["flags"])
    print(f"\nTotal parsed examples: {tot}; with at least one flag: {bad}; clean: {tot - bad}")
    if out_json:
        out_json.write_text(json.dumps(report, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()

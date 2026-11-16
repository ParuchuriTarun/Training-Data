"""Sanity check for data/external/*.txt after adding open-source files.

Reports: exact duplicate questions, near-duplicate answers (same first 300 chars),
unbalanced code fences, mojibake, and lists the examples flagged so they can be removed.
"""
import hashlib
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "data" / "external"
PAT = re.compile(r"@@@ USER\n(.*?)\n@@@ ASSISTANT\n(.*?)\n@@@ END", re.S)
MOJI = re.compile("(Ã[ -¿]|â€|�)")

by_q = defaultdict(list)
by_a = defaultdict(list)
bad = []
total = 0
for f in sorted(EXT.glob("*.txt")):
    t = f.read_text(encoding="utf-8", errors="replace")
    for i, (u, a) in enumerate(PAT.findall(t)):
        total += 1
        qk = re.sub(r"\W+", " ", u.lower()).strip()
        by_q[qk].append((f.name, i))
        by_a[hashlib.sha1(a[:300].encode("utf-8")).hexdigest()].append((f.name, i))
        if a.count("```") % 2:
            bad.append((f.name, i, "unbalanced fence", u[:70]))
        if MOJI.search(a):
            bad.append((f.name, i, "mojibake", u[:70]))

dq = {k: v for k, v in by_q.items() if len(v) > 1}
da = {k: v for k, v in by_a.items() if len(v) > 1}
print(f"examples: {total}")
print(f"duplicate questions: {len(dq)} groups, {sum(len(v) - 1 for v in dq.values())} extra")
for k, v in list(dq.items())[:15]:
    print("  Q:", k[:70], v[:4])
print(f"duplicate answer openings: {len(da)} groups, {sum(len(v) - 1 for v in da.values())} extra")
for k, v in list(da.items())[:15]:
    print("  A:", v[:4])
print(f"flagged examples: {len(bad)}")
for b in bad[:40]:
    print("  ", b)

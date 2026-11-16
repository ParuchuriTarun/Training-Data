"""Curate C:\\Projects\\Mavo\\Coding 1 2B\\training_data  ->  data/external/td_<category>.txt

Originals are never touched. Steps:
  1. read every .txt in the six category folders (ignores _scratch and non-.txt files)
  2. fix glued markers, split into examples (multi-turn kept as several USER/ASSISTANT pairs)
  3. merge consecutive context-dependent examples into one conversation (GROUPS below)
  4. quality filters (too short, unbalanced code fences, cut-off, filler, mojibake, placeholders)
  5. remove duplicates / near-duplicate rewrites (keeps the longest, most complete version)
  6. write accepted examples + a report (data/external/_curation_report.txt is NOT read by the loader)

Usage:  python data/curate_training_data.py [--dry]
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "training_data"
OUT = ROOT / "data" / "external"
CATEGORIES = ["appdev", "english", "fundamentals", "longhorizon", "seed", "webdev"]

# 1-based example numbers inside a file that continue one conversation.
GROUPS = {
    "seed/batch_0001.txt": [[4, 5, 6]],
    "longhorizon/batch_0002.txt": [[1, 2, 3, 4, 5], [6, 7, 8, 9], [10, 11, 12, 13], [14, 15, 16, 17, 18]],
    "longhorizon/batch_0003.txt": [[1, 2, 3], [4, 5], [6, 7, 8, 9], [10, 11, 12], [13, 14, 15]],
}

MARK = re.compile(r"(?<=\S)[ \t]*@@@ (USER|ASSISTANT|END)(?=[ \t]*(?:\r?\n|$))")
FILLER = ["as an ai language model", "lorem ipsum", "i hope this helps", "[insert ", "[insert]", "your code here",
          "todo: implement", "// todo", "# todo", "<placeholder>", "..." + "...", "(omitted for brevity)",
          "rest of the code", "and so on..."]
MOJIBAKE = ["\u00e2\u20ac", "\u00c3\u00a9", "\u00c3\u00a2", "\ufffd"]


def parse_blocks(text):
    """-> list of turn-lists; a turn is (user, assistant). Blocks without a complete first pair are skipped."""
    text = MARK.sub(r"\n@@@ \1", text.replace("\r\n", "\n"))
    blocks, turns, user, mode, buf = [], [], None, None, []
    for line in text.split("\n"):
        s = line.strip()
        if s in ("@@@ USER", "@@@ ASSISTANT", "@@@ END"):
            body = "\n".join(buf).strip()
            if mode == "USER":
                user = body
            elif mode == "ASSISTANT" and user is not None:
                turns.append((user, body))
                user = None
            if s == "@@@ END":
                if turns and all(u and a for u, a in turns):
                    blocks.append(turns)
                turns, user, mode = [], None, None
            else:
                mode = s.split()[1]
            buf = []
        elif mode:
            buf.append(line)
    return blocks


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def shingles(s, n=5):
    w = norm(s).split()
    return {" ".join(w[i:i + n]) for i in range(max(1, len(w) - n + 1))}


def problems(turns):
    bad = []
    for i, (u, a) in enumerate(turns):
        if len(a) < 120:
            bad.append(f"turn{i + 1}: answer too short ({len(a)} chars)")
        if len(u) < 8:
            bad.append(f"turn{i + 1}: question too short")
        if a.count("```") % 2:
            bad.append(f"turn{i + 1}: unbalanced code fence")
        low = a.lower()
        for f in FILLER:
            if f in low:
                bad.append(f"turn{i + 1}: filler/placeholder '{f}'")
        for m in MOJIBAKE:
            if m in a or m in u:
                bad.append(f"turn{i + 1}: mojibake")
                break
    last = turns[-1][1].rstrip()
    lastline = last.split("\n")[-1].strip()
    if last and last[-1].isalnum() and len(lastline) > 80 and not lastline.startswith(("|", "-", "*", "#")):
        bad.append("looks cut off (ends mid-sentence)")
    return bad


def main():
    dry = "--dry" in sys.argv
    kept = defaultdict(list)           # category -> [(turns, origin)]
    rejected = []
    total_in = 0
    for cat in CATEGORIES:
        for f in sorted((SRC / cat).glob("*.txt")):
            rel = f"{cat}/{f.name}"
            blocks = parse_blocks(f.read_text(encoding="utf-8", errors="replace"))
            total_in += len(blocks)
            used = set()
            for grp in GROUPS.get(rel, []):
                if max(grp) > len(blocks):
                    print(f"WARNING {rel}: group {grp} exceeds {len(blocks)} examples")
                    continue
                turns = [t for n in grp for t in blocks[n - 1]]
                used.update(grp)
                kept[cat].append((turns, f"{rel} #{grp[0]}-{grp[-1]}"))
            for n, b in enumerate(blocks, 1):
                if n not in used:
                    kept[cat].append((b, f"{rel} #{n}"))

    # quality filters
    ok = []
    for cat in CATEGORIES:
        for turns, origin in kept[cat]:
            bad = problems(turns)
            if bad:
                rejected.append((origin, "; ".join(bad)))
            else:
                ok.append((cat, turns, origin))

    # duplicates: same question, or heavily overlapping answers -> keep the longest
    ok.sort(key=lambda x: -sum(len(a) for _, a in x[1]))
    final, keys, shingle_sets = [], set(), []
    for cat, turns, origin in ok:
        q = norm(turns[0][0])[:300]
        sh = shingles(" ".join(a for _, a in turns))
        dup = None
        if q in keys:
            dup = "same question"
        else:
            for s2, o2 in shingle_sets:
                inter = len(sh & s2)
                if inter / max(1, min(len(sh), len(s2))) > 0.6:
                    dup = f"near-duplicate of {o2}"
                    break
        if dup:
            rejected.append((origin, dup))
            continue
        keys.add(q)
        shingle_sets.append((sh, origin))
        final.append((cat, turns, origin))

    final.sort(key=lambda x: (CATEGORIES.index(x[0]), x[2]))
    per_cat = defaultdict(list)
    for cat, turns, origin in final:
        per_cat[cat].append(turns)

    lines = [f"examples read: {total_in}", f"accepted: {len(final)}", f"rejected: {len(rejected)}", ""]
    for cat in CATEGORIES:
        multi = sum(1 for t in per_cat[cat] if len(t) > 1)
        lines.append(f"  {cat:13s} {len(per_cat[cat]):4d} examples ({multi} multi-turn)")
    lines += ["", "REJECTED:"] + [f"  {o}: {why}" for o, why in sorted(rejected)]
    report = "\n".join(lines)
    print(report)
    if dry:
        return

    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("td_*.txt"):
        old.unlink()
    for cat, exs in per_cat.items():
        parts = []
        for turns in exs:
            for u, a in turns:
                parts.append(f"@@@ USER\n{u}\n@@@ ASSISTANT\n{a}")
            parts.append("@@@ END\n")
        (OUT / f"td_{cat}.txt").write_text("\n".join(parts), encoding="utf-8", newline="\n")
    (ROOT / "data" / "curation_report.txt").write_text(report, encoding="utf-8")
    print(f"\nwritten to {OUT}")


if __name__ == "__main__":
    main()

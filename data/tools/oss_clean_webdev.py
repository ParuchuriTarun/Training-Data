"""Post-process oss_webdev_beginners.txt: strip emoji, drop first-person 'persona' examples.

Text-only. The Web-Dev-For-Beginners lessons (MIT) contain some chatty first-person
passages ("when I started...") that would teach the model to invent personal experience.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FP = ROOT / "open_sources" / "_out" / "final" / "oss_webdev_beginners.txt"

EMO = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐️‍]")
PERSONA = re.compile(
    r"(when I started|I'll be honest|I'm going to be honest|my favorite|I remember when|"
    r"THIS is where|honestly,|I've seen|in my experience)", re.I)

text = FP.read_text(encoding="utf-8")
ex = re.findall(r"@@@ USER\n(.*?)\n@@@ ASSISTANT\n(.*?)\n@@@ END", text, re.S)
kept, dropped = [], 0
for u, a in ex:
    if len(PERSONA.findall(a)) >= 2:
        dropped += 1
        continue
    if a.count("```") % 2 or re.search("(Ã[ -¿]|â€|�)", a):
        dropped += 1
        continue
    a = EMO.sub("", a)
    a = re.sub(r"[ \t]+\n", "\n", a)
    kept.append((u, a.strip()))

out = "".join(f"@@@ USER\n{u}\n@@@ ASSISTANT\n{a}\n@@@ END\n\n" for u, a in kept)
FP.write_text(out, encoding="utf-8")
print(f"webdev_beginners: kept {len(kept)}, dropped {dropped}, chars {len(out):,}")

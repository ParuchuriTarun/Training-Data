"""Curate C:\\Projects\\Mavo\\Coding 1 2B\\Data.txt  ->  data/external/td_data_txt.txt

Data.txt is a chat export in a different marker style (@@USER / @ASSISTANT). Only the first block
(plain question-and-answer pairs, up to the line "Are you able to access the laptop files...") is real
training material. Everything after it is pasted agent chat (tool narration, project reports, this
project's own build conversation, the other-AI prompt) and is NOT used.

Per-entry decisions (reviewed by hand):
  1 BIOS resets            keep
  2+3 Excel spaces         keep, merged into ONE 2-turn conversation; the 'Remove Specific Types of Spaces'
                           section is removed (its formulas use LTRIM/RTRIM which Excel does not have)
  4 IndentationError       keep
  5 fruits/tropical        DROP  - answer is about a different program (if/elif num) than the question
  6 while i =< 6           DROP  - answer is about a different program (cricket list) + garbled ending
  7 pass statement         keep
  8 np.eye                 keep
  9 Pandas Series          keep; positional access changed to .iloc (prices[0] / prices[-1] on a string
                           index is deprecated and fails in pandas 3)
Run:  python data/add_data_txt.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "Data.txt"
OUT = ROOT / "data" / "external" / "td_data_txt.txt"


def split_qa(text):
    text = text.replace("\r\n", "\n")
    cut = re.search(r"^@@USER\nAre you able to access the laptop files", text, flags=re.M)
    if cut:
        text = text[:cut.start()]
    items = []
    for chunk in re.split(r"^@@USER[ \t]*\n", text, flags=re.M):
        if not chunk.strip():
            continue
        m = re.search(r"^@@?ASSI(?:STANT)?[ \t]*\n", chunk, flags=re.M)
        if not m:
            continue
        items.append((chunk[:m.start()].strip(), chunk[m.end():].strip()))
    return items


def main():
    items = split_qa(SRC.read_text(encoding="utf-8", errors="replace"))
    print("Q&A pairs found before the chat transcripts:", len(items))
    assert len(items) == 9, "Data.txt changed - re-review before adding"
    bios, xl1, xl2, indent, fruits, whilex, pass_, eye, pandas = items

    # Excel: drop the incorrect section
    a = xl1[1]
    a = re.sub(r"## Remove Specific Types of Spaces\n.*?(?=## For Non-Breaking Spaces)", "", a, flags=re.S)
    assert "LTRIM" not in a
    # Pandas: positional access with .iloc
    p = pandas[1]
    for old, new in [("print(prices[0])        # 1.50 (first element)", "print(prices.iloc[0])    # 1.50 (first element)"),
                     ("print(prices[-1])       # 3.25 (last element)", "print(prices.iloc[-1])   # 3.25 (last element)"),
                     ("print(prices[1:3])      # banana and orange", "print(prices.iloc[1:3])  # banana and orange")]:
        assert old in p
        p = p.replace(old, new)
    p = p.replace("### By index position:", "### By index position (use .iloc):")

    convs = [
        [bios],
        [(xl1[0], a), xl2],
        [indent],
        [pass_],
        [eye],
        [(pandas[0], p)],
    ]
    parts = []
    for turns in convs:
        for u, ans in turns:
            assert ans.count("```") % 2 == 0, u[:40]
            parts.append(f"@@@ USER\n{u}\n@@@ ASSISTANT\n{ans}")
        parts.append("@@@ END\n")
    OUT.write_text("\n".join(parts), encoding="utf-8", newline="\n")
    print(f"wrote {len(convs)} examples to {OUT}")


if __name__ == "__main__":
    main()

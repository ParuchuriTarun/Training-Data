"""Execute the ```sql blocks of one example in an in-memory SQLite database and print every SELECT result,
so the results written in comments of an answer can be compared with what the database really returns.

Usage:  python data/run_sql_blocks.py <file.txt> <example number>
"""
import re
import sqlite3
import sys
from pathlib import Path

FENCE = "`" * 3


def main():
    text = Path(sys.argv[1]).read_text(encoding="utf-8")
    n = int(sys.argv[2])
    ex = re.findall(r"@@@ USER\r?\n(.*?)\r?\n@@@ ASSISTANT\r?\n(.*?)\r?\n@@@ END", text, re.S)
    sql = "\n".join(re.findall(FENCE + r"sql\n(.*?)" + FENCE, ex[n - 1][1], re.S))
    con = sqlite3.connect(":memory:")
    buf = ""
    for line in sql.split("\n"):
        buf += line + "\n"
        if sqlite3.complete_statement(buf):
            stmt = buf.strip()
            buf = ""
            cur = con.execute(stmt)
            if stmt.lstrip().upper().startswith(("SELECT", "--")) or cur.description:
                print(">>", " ".join(stmt.split())[:90])
                for row in cur.fetchall():
                    print("   ", row)
    print("OK")


if __name__ == "__main__":
    main()

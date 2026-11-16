"""Build data/staging/claude_python_cli_21.txt. Every script is saved to a temporary folder and RUN (Python 3.13) with
the commands shown, and the real output and exit codes are pasted into the answer."""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

F = "`" * 3
OUT = Path(r"C:\Projects\Mavo\Coding 1 2B\data\staging\claude_python_cli_21.txt")
EXAMPLES = []


def run_session(files, runs, prefix):
    d = Path(tempfile.mkdtemp())
    for name, content in files.items():
        p = d / name
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            p.write_bytes(content)
        else:
            p.write_text(content, encoding="utf-8", newline="\n")
    blocks = []
    for args, stdin, env in runs:
        e = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
        e.pop("COLUMNS", None)
        e.update(env or {})
        p = subprocess.run([sys.executable] + prefix + list(args), cwd=str(d), env=e, input=stdin,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", timeout=60)
        shown = " ".join(('"' + a + '"') if (" " in a or a == "" or "'" in a) else a for a in args)
        lines = [("$ " + "".join(f"{k}={v} " for k, v in (env or {}).items()) + "python " + " ".join(prefix) + (" " + shown if shown else "")).rstrip()]
        if stdin is not None:
            lines[0] = "(standard input: " + repr(stdin).strip("'").replace("\\n", " / ").rstrip(" /") + ")\n" + lines[0]
        body = "\n".join(l.rstrip() for l in p.stdout.replace("\r", "").split("\n")).strip("\n")
        if body:
            lines.append(body)
        if p.returncode:
            lines.append(f"[exit code {p.returncode}]")
        blocks.append("\n".join(lines))
    shutil.rmtree(d, ignore_errors=True)
    return "\n\n".join(blocks)


def ex(question, intro, shown, runs, after, files=None, prefix=("app.py",), run_label="Runs"):
    """shown: list of (file name, language, content); files: what is really written (defaults to the shown files)."""
    real = dict(files or {})
    parts = [intro.strip()]
    for name, lang, content in shown:
        assert F not in content
        real.setdefault(name, content.strip("\n") + "\n")
        parts.append(f"`{name}`:\n\n{F}{lang}\n{content.strip(chr(10))}\n{F}")
    result = run_session(real, runs, list(prefix))
    parts.append(f"{run_label}:\n\n{F}\n{result}\n{F}")
    parts.append(after.strip())
    EXAMPLES.append((question, "\n\n".join(parts)))
    print(f"---- example {len(EXAMPLES)} ----\n{result}\n")


# 1 ---------------------------------------------------------------------------------------------
ex("How do I write a Python command-line script with argparse that has a file argument, an option with a number and a flag?",
   "Build an `ArgumentParser`, add the arguments, and let `parse_args` do the rest: it converts types, creates `--help`, and prints a clear error with exit code 2 on bad input. Keep the work in a `main(argv=None)` function that returns the exit code, so the script is easy to test, and call `sys.exit(main())` at the bottom.",
   [("wordcount.py", "python", r'''
import argparse
import re
import sys
from collections import Counter
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Show the most common words in a text file.")
    parser.add_argument("path", type=Path, help="text file to read")
    parser.add_argument("-n", "--top", type=int, default=5, help="how many words to show (default: %(default)s)")
    parser.add_argument("-i", "--ignore-case", action="store_true", help="count 'The' and 'the' as one word")
    args = parser.parse_args(argv)

    if not args.path.is_file():
        parser.error(f"{args.path} is not a file")      # prints the usage and exits with code 2

    text = args.path.read_text(encoding="utf-8")
    if args.ignore_case:
        text = text.lower()
    words = re.findall(r"[A-Za-z']+", text)
    for word, count in Counter(words).most_common(args.top):
        print(f"{count:>4}  {word}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''), ("text.txt", "text", "The cat and the dog. The dog barks; the cat sleeps. And the bird sings.")],
   [(["text.txt"], None, None), (["-n", "3", "-i", "text.txt"], None, None), (["missing.txt"], None, None),
    (["-n", "many", "text.txt"], None, None), (["--help"], None, None)],
   "Without `-i` the words `The` and `the` are counted separately, which is why `-i` changes the result. Every mistake of the user (missing file, `many` instead of a number) gives a short message and exit code 2, and you wrote no checking code for the number: `type=int` did it. `%(default)s` in a help text is replaced by the default value, so the help never goes out of date. Use `parser.error(...)` for problems with the arguments and `print(..., file=sys.stderr)` plus `return 1` for problems that happen while running.",
   prefix=("wordcount.py",))

# 2 ---------------------------------------------------------------------------------------------
ex("How do I build a command-line tool with subcommands like 'add', 'list' and 'done' in Python? Use argparse and a JSON file for storage.",
   "Use `add_subparsers`. Every subcommand gets its own parser with its own arguments, and `set_defaults(func=...)` attaches the function that handles it, so `main` only has to call `args.func(args)`. Options that belong to the whole program (here `--file`) go on the main parser and must be written before the subcommand.",
   [("todo.py", "python", r'''
import argparse
import json
import sys
from pathlib import Path


def load(path):
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, items):
    path.write_text(json.dumps(items, indent=2), encoding="utf-8")


def cmd_add(args):
    items = load(args.file)
    new_id = max((item["id"] for item in items), default=0) + 1
    items.append({"id": new_id, "title": args.title, "done": False})
    save(args.file, items)
    print(f"added #{new_id}: {args.title}")
    return 0


def cmd_list(args):
    for item in load(args.file):
        if args.pending and item["done"]:
            continue
        mark = "x" if item["done"] else " "
        print(f"{item['id']:>3} [{mark}] {item['title']}")
    return 0


def cmd_done(args):
    items = load(args.file)
    for item in items:
        if item["id"] == args.id:
            item["done"] = True
            save(args.file, items)
            print(f"done #{args.id}")
            return 0
    print(f"error: no task #{args.id}", file=sys.stderr)
    return 1


def build_parser():
    parser = argparse.ArgumentParser(prog="todo")
    parser.add_argument("--file", type=Path, default=Path("todo.json"), help="where the tasks are stored")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="add a task")
    add.add_argument("title")
    add.set_defaults(func=cmd_add)

    lst = sub.add_parser("list", help="show the tasks")
    lst.add_argument("--pending", action="store_true", help="hide finished tasks")
    lst.set_defaults(func=cmd_list)

    done = sub.add_parser("done", help="mark a task as finished")
    done.add_argument("id", type=int)
    done.set_defaults(func=cmd_done)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
''')],
   [(["add", "Buy milk"], None, None), (["add", "Call Sam"], None, None), (["done", "1"], None, None),
    (["list"], None, None), (["list", "--pending"], None, None), (["done", "9"], None, None),
    ([], None, None), (["--help"], None, None)],
   "`required=True` on the subparsers makes a missing command an error; without it, Python 3 would silently continue with `args.command` empty and crash on `args.func`. The ids are computed with `max(..., default=0) + 1`, which also works on an empty list. The program stores the whole list in one JSON file and rewrites it each time, which is fine for a personal tool; for concurrent use or large data, switch to SQLite (next examples).",
   prefix=("todo.py",))

# 3 ---------------------------------------------------------------------------------------------
ex("How do I make a Python script that reads from files or from a pipe (standard input) like grep, with the right exit codes?",
   "Treat standard input as one more source: when no file is given (or the name is `-`), read `sys.stdin`. Follow the grep convention for exit codes, because shell scripts rely on it: `0` when something matched, `1` when nothing matched, `2` when there was an error such as an unreadable file. Errors go to `stderr` so they do not mix with the matching lines.",
   [("pygrep.py", "python", r'''
import argparse
import re
import sys


def lines_of(name):
    if name == "-":
        yield from sys.stdin
    else:
        with open(name, encoding="utf-8") as handle:
            yield from handle


def main(argv=None):
    parser = argparse.ArgumentParser(prog="pygrep")
    parser.add_argument("pattern", help="regular expression")
    parser.add_argument("files", nargs="*", help="files to search (default: standard input)")
    parser.add_argument("-i", "--ignore-case", action="store_true")
    parser.add_argument("-n", "--line-number", action="store_true")
    args = parser.parse_args(argv)

    regex = re.compile(args.pattern, re.IGNORECASE if args.ignore_case else 0)
    sources = args.files or ["-"]
    found, failed = False, False
    for name in sources:
        try:
            for number, line in enumerate(lines_of(name), start=1):
                if regex.search(line):
                    found = True
                    prefix = (name + ":" if len(sources) > 1 else "") + (f"{number}:" if args.line_number else "")
                    print(prefix + line.rstrip("\n"))
        except OSError as error:
            print(f"pygrep: {name}: {error.strerror}", file=sys.stderr)
            failed = True
    return 2 if failed else (0 if found else 1)


if __name__ == "__main__":
    sys.exit(main())
''')],
   [(["apple"], "apple pie\nbanana\nCherry tart\napple tart\n", None),
    (["-i", "-n", "tart"], "apple pie\nbanana\nCherry tart\napple tart\n", None),
    (["zzz"], "apple pie\nbanana\n", None),
    (["tart", "a.txt", "b.txt"], None, None),
    (["pie", "nofile.txt", "a.txt"], None, None)],
   "The third run printed nothing and exited with code `1`, which is how `if pygrep ...; then` in a shell script knows that there was no match. In the last run the missing file is reported and the script still searches `a.txt` and prints its match; the final code is 2 because something went wrong, even though the other file was searched. Using `yield from` in `lines_of` keeps the memory use small, since a big file is read line by line and not loaded into a list.",
   files={"a.txt": "apple tart\nplum pie\n", "b.txt": "tart shell\nnothing here\n"},
   prefix=("pygrep.py",))

# 4 ---------------------------------------------------------------------------------------------
ex("How do I write a Python script that reads a CSV file, adds up the amounts per category and prints either a table or JSON? Some rows have bad data.",
   "Use `csv.DictReader` so each row is a dictionary, and `Decimal` for money (floats give results like `0.1 + 0.2 = 0.30000000000000004`). Report bad rows with their line number on `stderr` and keep going, so one bad row does not destroy the whole report. Open CSV files with `newline=\"\"`, as the `csv` module documentation requires.",
   [("report.py", "python", r'''
import argparse
import csv
import json
import sys
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Total the amounts per region.")
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--min", type=Decimal, default=Decimal(0), help="hide regions below this total")
    parser.add_argument("--json", action="store_true", help="print JSON instead of a table")
    args = parser.parse_args(argv)

    totals = defaultdict(Decimal)
    with args.csv_file.open(newline="", encoding="utf-8") as handle:
        for line_number, row in enumerate(csv.DictReader(handle), start=2):   # line 1 is the header
            try:
                region, amount = row["region"], Decimal(row["amount"])
            except (InvalidOperation, KeyError):
                print(f"warning: line {line_number}: bad row {dict(row)}, skipped", file=sys.stderr)
                continue
            totals[region] += amount

    shown = {region: total for region, total in sorted(totals.items()) if total >= args.min}
    if args.json:
        print(json.dumps({region: str(total) for region, total in shown.items()}, indent=2))
    else:
        for region, total in shown.items():
            print(f"{region:<10}{total:>10.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''), ("sales.csv", "csv", "region,amount\nnorth,120.50\nsouth,80.25\nnorth,19.50\neast,abc\nsouth,300\nwest,15.10")],
   [(["sales.csv"], None, None), (["sales.csv", "--min", "100"], None, None), (["sales.csv", "--json"], None, None)],
   "The warning for line 5 appears before the table because the whole file is read before the table is printed. With `report.py sales.csv > out.txt` the warning still appears on screen while `out.txt` receives only the report. A bug I fixed while writing this: my first version did `totals[row[\"region\"]] += Decimal(row[\"amount\"])` inside the `try`, and a region whose only row was bad still showed up with `0.00`, because the `defaultdict` creates the key before the right-hand side fails. Converting the values first and adding afterwards avoids that. The JSON values are strings (`\"120.50\"`) on purpose: `json.dumps` cannot write a `Decimal`, and turning it into a float would bring back the rounding problem. The line numbers start at 2 because `enumerate` is told to start there; row 1 of the file is the header.",
   prefix=("report.py",))

# 5 ---------------------------------------------------------------------------------------------
ex("How do I build a small notes tool in Python with sqlite3? I want add, search and delete, and I have heard about SQL injection.",
   "`sqlite3` is in the standard library, and one file holds the whole database. The rule against SQL injection is simple: never build SQL text with f-strings or `+`; put a `?` in the statement and pass the values as a separate tuple, and the database treats them as data, never as SQL. Use the connection as a context manager (`with db:`) so each change is committed, or rolled back if an error happens.",
   [("notes.py", "python", r'''
import argparse
import sqlite3
import sys


def connect(path):
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, text TEXT NOT NULL)")
    return db


def main(argv=None):
    parser = argparse.ArgumentParser(prog="notes")
    parser.add_argument("--db", default="notes.db")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("add").add_argument("text")
    sub.add_parser("search").add_argument("term")
    sub.add_parser("delete").add_argument("id", type=int)
    args = parser.parse_args(argv)

    db = connect(args.db)
    try:
        if args.command == "add":
            with db:
                cursor = db.execute("INSERT INTO notes (text) VALUES (?)", (args.text,))
            print(f"saved as #{cursor.lastrowid}")
        elif args.command == "search":
            rows = db.execute("SELECT id, text FROM notes WHERE text LIKE ? ORDER BY id", (f"%{args.term}%",))
            found = 0
            for note_id, text in rows:
                print(f"#{note_id}: {text}")
                found += 1
            print(f"{found} match(es)")
        else:
            with db:
                cursor = db.execute("DELETE FROM notes WHERE id = ?", (args.id,))
            if cursor.rowcount == 0:
                print(f"error: no note #{args.id}", file=sys.stderr)
                return 1
            print(f"deleted #{args.id}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
''')],
   [(["add", "Buy milk"], None, None), (["add", "Pay rent on Friday"], None, None), (["add", "O'Brien's phone number"], None, None),
    (["search", "milk"], None, None), (["search", "O'Brien"], None, None),
    (["search", "x' OR '1'='1"], None, None), (["delete", "2"], None, None), (["search", "rent"], None, None), (["delete", "2"], None, None)],
   "The apostrophe in `O'Brien's` works without any escaping, and the injection attempt `x' OR '1'='1` is just a search term that matches nothing, because it never became part of the SQL. With an f-string, the same input would have changed the meaning of the query. Only values can be parameters; table and column names cannot, so if they come from the user, check them against a fixed list. In a `LIKE` pattern, `%` and `_` in the search term still act as wildcards; for a literal search use `INSTR(text, ?) > 0` instead.",
   prefix=("notes.py",))

# 6 ---------------------------------------------------------------------------------------------
ex("How do I add logging and proper exit codes to a Python script that processes several files? One bad file should not stop the others.",
   "Use the `logging` module instead of `print` for messages about the run: it has levels, and you can show more detail with a `-v` flag without changing the code. Send the log to `stderr` (the default), keep `print` only for the real output, catch the specific errors you expect inside the loop, remember that the run had a problem, and return a non-zero code at the end.",
   [("linecount.py", "python", r'''
import argparse
import logging
import sys
from pathlib import Path

log = logging.getLogger("linecount")


def count_lines(path):
    with path.open(encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Count the lines of text files.")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("-v", "--verbose", action="store_true", help="also show debug messages")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING,
                        format="%(levelname)s: %(message)s")

    problems = 0
    for path in args.files:
        log.debug("reading %s", path)
        try:
            total = count_lines(path)
        except FileNotFoundError:
            log.error("%s: no such file", path)
            problems += 1
            continue
        except UnicodeDecodeError as error:
            log.warning("%s: not valid UTF-8 (%s), skipped", path, error.reason)
            problems += 1
            continue
        print(f"{total:>5} {path}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
''')],
   [(["a.txt", "b.txt"], None, None), (["a.txt", "missing.txt", "data.bin", "b.txt"], None, None),
    (["-v", "a.txt", "missing.txt"], None, None)],
   "The good files are processed even when others fail, and the exit code `1` tells a calling script that something went wrong. The log messages appear above the counts only because this output was captured through a pipe, where `print` output is held back until the program ends; in a terminal they appear in the order they happen. `log.error(\"%s: ...\", path)` passes the values separately instead of formatting the string first, so the work of formatting is only done when the message is really shown. Catch the specific exceptions (`FileNotFoundError`, `UnicodeDecodeError`), not a bare `except:`, which would also hide your own bugs and even Ctrl+C. For a log file, add `filename=\"run.log\"` to `basicConfig`; add `%(asctime)s` to the format when you want timestamps.",
   files={"a.txt": "one\ntwo\nthree\n", "b.txt": "single line\n", "data.bin": b"\xff\xfe\x00 not text"},
   prefix=("linecount.py",))

# 7 ---------------------------------------------------------------------------------------------
ex("How do I let a Python command-line tool take its defaults from environment variables, but let command-line options win?",
   "Read the environment variable when you define the default of the option. Then the order is automatically: option on the command line, then the environment variable, then the built-in value. For on/off settings use `argparse.BooleanOptionalAction` (Python 3.9+), which creates both `--shout` and `--no-shout`, so the command line can switch a setting off even when the environment turned it on.",
   [("greet.py", "python", r'''
import argparse
import os
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(prog="greet")
    parser.add_argument("name")
    parser.add_argument("--greeting", default=os.environ.get("GREET_WORD", "Hello"),
                        help="word to start with (env: GREET_WORD)")
    parser.add_argument("--shout", action=argparse.BooleanOptionalAction,
                        default=os.environ.get("GREET_SHOUT") == "1",
                        help="use capital letters (env: GREET_SHOUT=1)")
    args = parser.parse_args(argv)

    message = f"{args.greeting}, {args.name}!"
    print(message.upper() if args.shout else message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
''')],
   [(["Ann"], None, None), (["Ann"], None, {"GREET_WORD": "Hi"}),
    (["--greeting", "Hola", "Ann"], None, {"GREET_WORD": "Hi"}),
    (["Ann"], None, {"GREET_SHOUT": "1"}), (["--no-shout", "Ann"], None, {"GREET_SHOUT": "1"})],
   "Each line shows one layer winning: the built-in default, the environment variable, the option over the variable, the boolean from the environment, and `--no-shout` over the environment. Environment variables are always strings, which is why the boolean is compared with `== \"1\"` instead of being used directly (the string `\"0\"` would be true). Never put secrets such as passwords into the `--help` text or a default that is printed; reading a secret from the environment is fine, but do not echo it back.",
   prefix=("greet.py",))

# 8 ---------------------------------------------------------------------------------------------
ex("How do I write a safe bulk-rename tool in Python with pathlib and a --dry-run option?",
   "Split the work into two steps: first compute the plan (a list of old name and new name), then check it, and only then apply it. `--dry-run` simply stops after printing the plan. The check for clashes matters: if two files would get the same new name, or the new name already exists, `rename` would overwrite a file (on Windows it fails, on Linux and macOS it silently replaces), so the tool refuses before it touches anything.",
   [("renamer.py", "python", r'''
import argparse
import re
import sys
from pathlib import Path


def plan(folder, pattern, replacement):
    regex = re.compile(pattern)
    for path in sorted(folder.iterdir()):
        if path.is_file():
            new_name = regex.sub(replacement, path.name)
            if new_name != path.name:
                yield path, path.with_name(new_name)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Rename files by regular expression.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("pattern")
    parser.add_argument("replacement")
    parser.add_argument("--dry-run", action="store_true", help="only show what would happen")
    args = parser.parse_args(argv)

    moves = list(plan(args.folder, args.pattern, args.replacement))
    targets = [new for _, new in moves]
    clashes = sorted({new.name for new in targets if targets.count(new) > 1 or new.exists()})
    if clashes:
        print("error: refusing to rename, these names would clash: " + ", ".join(clashes), file=sys.stderr)
        return 1

    for old, new in moves:
        print(f"{old.name} -> {new.name}")
        if not args.dry_run:
            old.rename(new)
    print(f"{len(moves)} file(s) " + ("would be renamed" if args.dry_run else "renamed"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
''')],
   [(["photos", "^IMG_", "holiday-", "--dry-run"], None, None), (["photos", "^IMG_", "holiday-"], None, None),
    (["photos", "^IMG_", "holiday-"], None, None), (["clash", "^.", "x"], None, None)],
   "The first run changes nothing, the second renames three files, and the third finds nothing left to do because the names no longer match `^IMG_`, so running the tool twice is harmless. In the last run `a.txt` and `b.txt` would both become `x.txt`, so the tool stops with exit code 1 and renames neither. Use raw strings for patterns in your own code (`r\"^IMG_\"`) and remember that `\\1` in the replacement refers to the first group. When you need to move files across disks or overwrite on purpose, use `shutil.move` or `Path.replace` and say so in the option name.",
   files={"photos/IMG_001.jpg": "", "photos/IMG_002.jpg": "", "photos/IMG_003.jpg": "", "photos/notes.txt": "",
          "clash/a.txt": "", "clash/b.txt": ""},
   prefix=("renamer.py",))

# 9 ---------------------------------------------------------------------------------------------
ex("How do I turn my Python script into a package that I can run with 'python -m mytool'?",
   "Make a folder with an `__init__.py` file (it can hold just the version), put the logic in a module such as `cli.py`, and add a `__main__.py` file. Python runs `__main__.py` when you start the folder with `-m`. Keep `main(argv=None)` in `cli.py`, so the same function can later be used as a `console_scripts` entry point when you add a `pyproject.toml`, which creates a real `mytool` command at install time.",
   [("mytool/__init__.py", "python", '__version__ = "0.1.0"'),
    ("mytool/cli.py", "python", r'''
import argparse
import sys

from . import __version__


def main(argv=None):
    parser = argparse.ArgumentParser(prog="mytool")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    greet = sub.add_parser("greet", help="say hello")
    greet.add_argument("name")
    args = parser.parse_args(argv)

    if args.command == "greet":
        print(f"Hello, {args.name}!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''),
    ("mytool/__main__.py", "python", '''
from .cli import main

raise SystemExit(main())
''')],
   [(["greet", "Ann"], None, None), (["--version"], None, None), ([], None, None)],
   "The relative imports (`from . import ...`) only work inside a package, which is the reason for the folder: running `python mytool/cli.py` directly would fail with an import error, while `python -m mytool` works from the folder that contains `mytool/`. The `prog=\"mytool\"` makes the help and the error messages show the name of the tool instead of `__main__.py`. `argparse` has a ready-made `version` action, so `--version` needs no code of its own.",
   prefix=("-m", "mytool"))


# ------------------------------------------------------------------------------ write
text = ""
for q, a in EXAMPLES:
    text += f"@@@ USER\n{q}\n@@@ ASSISTANT\n{a}\n@@@ END\n\n"
OUT.write_text(text, encoding="utf-8")
print("wrote", OUT, len(EXAMPLES), "examples", len(text), "chars")

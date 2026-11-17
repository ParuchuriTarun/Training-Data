"""Assembles claude_longhorizon_logstat_22.txt from the real project files/outputs made by gen_lh_logstat.py."""
import json
import re
from pathlib import Path

import gen_lh_logstat as G
from gen_lh_logstat import F, ROOT, OUT, code, out

R = json.loads((ROOT.parent / "lg_results.json").read_text(encoding="utf-8"))
import re as _re
G5_N = int(_re.search(r"Ran (\d+) tests?", json.loads((ROOT.parent / "lg_results5.json").read_text(encoding="utf-8"))["tests"])[1])
G.R.update(R)


def count(key):
    return G.tests_ran(key)


def disk(version, rel):
    """The file exactly as it is on disk (what the tests ran against)."""
    return (ROOT / version / rel).read_text(encoding="utf-8")


def short_tests(text):
    """Only the 'Ran N tests ... OK' tail of a unittest run."""
    lines = [l for l in text.splitlines() if l.strip() and not set(l.strip()) <= {"."} and not set(l.strip()) <= {"-"}]
    return "\n".join(lines[-2:])


def verbose_v1():
    keep = []
    for l in R["v1_tests"].splitlines():
        m = re.match(r"(test_\w+) \(tests\.test_parser\.ParseLineTests\.\w+\) \.\.\. (\w+)", l)
        if m:
            keep.append(f"{m[1]} ... {m[2]}")
        elif l.startswith(("Ran ", "OK")):
            keep.append(l)
    return "\n".join(keep[:5] + ["", keep[5], "", keep[6]])


# the user's traceback is pasted from their own machine; hide the long local folder name
crash_tail = R["v2_crash_tail"].replace(r"C:\Projects\Mavo\Coding 1 2B\data\staging\proj\lg\v2", r"C:\work\v2")
assert "ValueError: not a log line" in crash_tail

turns = []

# ---------------------------------------------------------------------------------------------------- turn 1
u1 = ("I have an nginx-style access log and I want a small command-line tool in Python that summarizes it: number of requests, "
      "total bytes, how many 2xx/3xx/4xx/5xx, the most requested paths and the busiest clients. Standard library only, "
      "and I want tests I can run with `python -m unittest`. Where do I start?")

a1 = ("Start with the one piece that has real rules: turning a single log line into data. Everything else (counting, printing, "
      "reading a file) is simple once a line becomes an object with named fields. So the first step is a `parser.py` with a "
      "`parse_line` function and tests for it. No command line yet.\n\n"
      "The layout I would aim for:\n"
      "1. `logstat/parser.py`: one line in, one `Entry` out (or a `ValueError`).\n"
      "2. `logstat/report.py`: counting and formatting, working on a list of entries.\n"
      "3. `logstat/cli.py` and `logstat/__main__.py`: arguments and files, so that `python -m logstat access.log` works.\n"
      "4. `tests/`: one test file per module.\n\n"
      "The log format is the common one: `ip - - [time] \"METHOD /path HTTP/1.1\" status size`. A regular expression with named "
      "groups reads it, and a frozen dataclass holds the result:\n\n"
      + code("python", G.PARSER_V1) + "\n\n"
      "Some choices that matter later:\n"
      "- `datetime.strptime` with `%z` keeps the time zone from the log (`+0100`), so the time is not silently shifted.\n"
      "- `\\S+` for the path means a query string such as `/search?q=a+b` stays part of the path.\n"
      "- A line that does not match raises `ValueError` with the first 60 characters, so the caller can say which line was bad. "
      "The parser itself does not decide what to do about bad lines.\n\n"
      "Make the folders (`logstat/` with an empty `__init__.py`, and `tests/` with an empty `__init__.py`) and put this in "
      "`tests/test_parser.py`:\n\n"
      + code("python", G.TEST_PARSER_V1) + "\n\n"
      "I ran these from the project folder:\n\n"
      + out("$ python -m unittest -v\n" + verbose_v1()) + "\n\n"
      "Five tests, all passing, and each one pins down a decision: fields, time zone, query string, trailing newline, garbage. "
      "Run the command from the folder that contains `logstat/` and `tests/`, otherwise `from logstat.parser import ...` fails with "
      "`ModuleNotFoundError`.\n\n"
      "Next step: the report and the command line, so that you can run it on a real file.")
turns.append((u1, a1))

# ---------------------------------------------------------------------------------------------------- turn 2
u2 = ("Tests pass. Now the report and the command line. Here is a small sample file, `access.log`:\n\n"
      + out(G.ACCESS_LOG) + "\n\nI want to run `python -m logstat access.log` and see the summary.")

a2 = ("Two small modules. `report.py` has no idea where entries come from, which is what makes it easy to test:\n\n"
      + code("python", G.REPORT_V2) + "\n\n"
      "`summarize` returns a plain dictionary, and `format_text` turns it into text. Keeping those two apart means you can print "
      "JSON later without touching the counting. `Counter.most_common(3)` gives the top three and keeps ties in the order they "
      "were first seen.\n\n"
      "`logstat/cli.py` connects it to a file:\n\n"
      + code("python", G.CLI_V2) + "\n\n"
      "and `logstat/__main__.py`, which is what makes `python -m logstat` work:\n\n"
      + code("python", G.MAIN_PY) + "\n\n"
      "`main` returns an exit code instead of calling `sys.exit` itself, so a test can call `main([...])` and look at the result. "
      "`__main__.py` passes it to `raise SystemExit(...)`.\n\n"
      "And a test file for the report, `tests/test_report.py`:\n\n"
      + code("python", G.TEST_REPORT_V2) + "\n\n"
      "Running everything and then the tool on your sample:\n\n"
      + out("$ python -m unittest\n" + short_tests(R["v2_tests"])) + "\n\n"
      + out(R["v2_run"]) + "\n\n"
      "I checked the numbers by hand: 8 requests; the status classes are 5 + 1 + 1 + 1; and the bytes are "
      "5120 + 1800 + 5120 + 320 + 410 + 128 + 0 + 5120 = 18,018. In the clients list, "
      "203.0.113.5 has 3 requests, and 198.51.100.7 and 203.0.113.9 have 2 each, so the order of those two comes from the order in the file.\n\n"
      "This is a complete first version. Try it on a real log before adding anything, because real logs are always messier than "
      "the sample.")
turns.append((u2, a2))

# ---------------------------------------------------------------------------------------------------- turn 3
u3 = ("I ran it on a real log and it just dies. This is the end of what I got:\n\n"
      + out(crash_tail) + "\n\n"
      "The line it complains about is a normal `GET /favicon.ico`. What is going on, and I don't want one weird line to kill the "
      "whole report.")

a3 = ("The message cuts off at 60 characters, so it does not show the end of the line. The end is the problem. Browsers "
      "ask for the favicon, and when the server answers `304 Not Modified` there is no body, so nginx writes a dash instead of a "
      "number in the size field:\n\n"
      + out('203.0.113.5 - - [03/Mar/2026:09:00:15 +0100] "GET /favicon.ico HTTP/1.1" 304 -') + "\n\n"
      "My regular expression only allows digits there (`\\d+`), so the line did not match and the whole run stopped on the "
      "`ValueError`. I reproduced it with a longer file, `real.log`, which is the sample plus the kinds of lines a public server really gets:\n\n"
      + out(G.REAL_LOG) + "\n\n"
      "The `304 -` line is one. The other two odd lines are a scanner sending binary junk instead of a request line "
      "(`\"\\x16\\x03...\"` is the start of a TLS handshake sent to a plain HTTP port) and a `\"-\" 408` from a client that connected "
      "and sent nothing. Those two are not valid requests, and the right answer for them is to skip them and say so.\n\n"
      "So there are two separate fixes, and I'd keep them separate.\n\n"
      "**Fix 1, the parser: a dash means 0 bytes.** Two small changes in `parser.py`, the pattern and the conversion:\n\n"
      + code("python", '# the end of the pattern, was (?P<size>\\d+)\n    r"(?P<status>\\d{3}) (?P<size>\\d+|-)$"\n\n# in parse_line, was size=int(match["size"])\n        size=0 if match["size"] == "-" else int(match["size"]),') + "\n\n"
      "and a test in `tests/test_parser.py`, added to the class:\n\n"
      + code("python", G.TEST_PARSER_V3_NEW) + "\n\n"
      "**Fix 2, the command line: skip bad lines, count them, say which ones.** A bad line is data about the log, not a reason "
      "to stop. The reading moves into its own function that returns the entries and the numbers of the lines it could not read. "
      "Blank lines are not errors, so they are ignored. The warning goes to stderr so that it does not end up in the middle of the report if "
      "someone redirects the output to a file. Because some people want a failing exit code when the log is dirty, there is a "
      "`--strict` option:\n\n"
      + code("python", G.CLI_V3) + "\n\n"
      "Two details. `errors=\"replace\"` makes a stray non-UTF-8 byte in a line become a replacement character instead of raising "
      "`UnicodeDecodeError`, and that line then simply fails to parse like any other bad line. And only the first five line "
      "numbers are shown, with `...` after them, so that a log with a million bad lines does not print a million numbers.\n\n"
      "Tests for the new behavior, `tests/test_cli.py`. They write a small log into a temporary folder and call `main` directly:\n\n"
      + code("python", G.TEST_CLI_V3) + "\n\n"
      "Running the tests, then your case, with and without `--strict`:\n\n"
      + out("$ python -m unittest\n" + short_tests(R["v3_tests"])) + "\n\n"
      + out(R["v3_run"]) + "\n\n"
      "Now `real.log` gives 10 requests. Lines 10 and 12 are reported, line 13 (blank) is ignored, and the favicon counts as a 304 with "
      "0 bytes. The byte total is 19,818, which is the old 18,018 plus the second `style.css` (1,800) plus the favicon (0). With "
      "`--strict` the same report is printed, but the exit code is 1, which is what a cron job or a CI step can check.\n\n"
      "The lesson from this: a parser for a text format written by other programs should be tried on a real file before the "
      "first release, and every surprise from that file should become a test. The dash test is exactly that.")
turns.append((u3, a3))

# ---------------------------------------------------------------------------------------------------- turn 4
u4 = ("That works. Two more things. The real log I need to run this on is about 2 GB, and I am worried it will run out of memory. "
      "And I want to ask questions like \"only the 5xx errors\" or \"only since 3 March\", and get JSON out for another script.")

a4 = ("You are right to worry, and the reason is visible in the code. `read_entries` builds a list of every `Entry`, and `summarize` "
      "starts with `entries = list(entries)`. Every line of the file becomes an object that stays in memory until the end, "
      "even though the report only needs a few counters. I measured it instead of guessing. `measure.py` runs `main` on a generated "
      f"log of 200,000 lines ({R['big_size']} MB, random paths and clients) and prints the peak memory that Python itself allocated, using `tracemalloc`:\n\n"
      + out("v3 (list of entries):\n" + R["v3_mem"] + "\n\nv4 (below, streaming):\n" + R["v4_mem"]) + "\n\n"
      "The old version needs about 90 MB for a 16 MB file, so roughly 5 to 6 times the size of the file, and it grows with the file. "
      "At 2 GB that would be more than 10 GB. The streaming version below needs 0.9 MB, and that number does not depend on the size "
      "of the file, only on how many different paths and clients there are. (This is the memory Python allocates, measured by "
      "`tracemalloc`, not the number that Task Manager shows, which is a little higher.)\n\n"
      "The change has three parts:\n\n"
      "1. **`Stats`**: counts as entries go by instead of keeping them. `summarize` keeps its name and its result, so `test_report.py` "
      "and `format_text` do not change.\n\n"
      + code("python", G.REPORT_V4_SUMMARIZE) + "\n\n"
      "2. **`read_entries` becomes a generator** (it uses `yield`), so it hands out one entry at a time. A generator cannot also "
      "return a list of bad lines at the end in a useful way, so the bad lines are recorded in a small `Problems` object that the caller owns. It keeps a count "
      "and only the first five line numbers, which also bounds its memory.\n\n"
      "3. **Filters** in a new `logstat/filters.py`, applied between reading and counting, so that the filtered-out entries are never stored either:\n\n"
      + code("python", G.FILTERS_V4) + "\n\n"
      "Choices worth knowing about. `status_filter` is used as an argparse `type=`, so a mistake like `7xx` is reported as a normal usage "
      "error with exit code 2 and no traceback. It returns a function, so `matches` does not have to know the two notations. "
      "For dates, the day is taken from the time as written in the log (`entry.time.date()`), in the log's own time zone, so a request "
      "at 23:30 +0100 on 2 March counts for 2 March, as it reads in the file, not for 3 March in UTC. If you would rather work in UTC, that is "
      "one change in one line: `entry.time.astimezone(timezone.utc).date()`.\n\n"
      "The command line, with the options and the `Problems` class:\n\n"
      + code("python", G.CLI_V4) + "\n\n"
      "The pipeline in `main` is three lines and reads from the inside out: `read_entries` yields entries, the generator expression `wanted` "
      "keeps the ones that match, and `summarize` consumes them. Nothing is a list.\n\n"
      "Tests. `tests/test_filters.py` is new:\n\n"
      + code("python", G.TEST_FILTERS_V4) + "\n\n"
      "and in `tests/test_cli.py` the first test changes, because `read_entries` no longer returns a tuple. It also needs "
      "`from logstat.cli import Problems, main, read_entries` at the top:\n\n"
      + code("python", G.TEST_CLI_V4_CHANGED) + "\n\n"
      "Here is the whole test suite, then the new options on `real.log`:\n\n"
      + out("$ python -m unittest\n" + short_tests(R["v4_tests"])) + "\n\n"
      + out(R["v4_run"]) + "\n\n"
      f"All {count('v4_tests')} tests pass (the project went from 5 to 8 to 12 to {count('v4_tests')} as each step added its tests). "
      "The numbers can be checked against the file by hand: the only 5xx is the `/api/data` request (128 bytes); on or after 3 March "
      "there are three readable requests (`index.html` 5,120, the favicon 0 and `style.css` 1,800, so 6,920 bytes); and the only 4xx is `/missing` "
      "(320 bytes). The warning about lines 10 and 12 appears on every run, because the whole file is still read. "
      "The filters only decide what is counted.\n\n"
      "Two limits to keep in mind. First, reading is still done in one process, one line at a time, with a regular expression and a "
      "`strptime` call per line. That is not fast, so a 2 GB log with millions of lines will take a while. Time it on a slice first (`head -n 200000 big.log > slice.log`). "
      "If it is too slow, try the cheaper parsing of the time or fewer regular expression features, and measure before and after. Second, `Counter` holds one entry per distinct path and client. A log full of unique paths (random query strings) "
      "can make that large, and then the fix is to cut the query string in `parse_line` or to count only the top paths approximately. "
      "That is a decision about what the report is for, so it is better to wait until a real log shows it is a problem.")
turns.append((u4, a4))

# ---------------------------------------------------------------------------------------------------- write
# ---------------------------------------------------------------------------------------------------- turn 5
R5 = json.loads((ROOT.parent / "lg_results5.json").read_text(encoding="utf-8"))
import gen_lh_logstat5 as G5

G.R["v5_tests"] = R5["tests"]
u5 = ("Good. Last two things before I hand this to my team. The top 3 is hard-coded, and I want `--top N`. And they should not have to type "
      "`python -m logstat` from inside the project folder. They should be able to run a plain `logstat` command from anywhere.")

a5 = ("`--top` goes through three places, and each one gets a small change. In `report.py` the number was written twice as a literal `3`. It becomes "
      "a parameter that defaults to 3, so every existing call and test keeps working: `Stats.as_dict(self, top=3)` uses `most_common(top)` for "
      "both lists, and `summarize(entries, top=3)` passes it on. In `cli.py` there is a new option and a small validator, so that `--top 0` and "
      "`--top three` are usage errors like the other bad arguments:\n\n"
      + code("python", R5["positive_int"]) + "\n\n"
      + code("python", '    parser.add_argument("--top", type=positive_int, default=3, help="how many paths and clients to list (default 3)")\n'
                       '    ...\n    summary = summarize(wanted, args.top)') + "\n\n"
      "Two tests, one added at the end of the class in `tests/test_report.py` and one at the end of the class in `tests/test_cli.py`:\n\n"
      + code("python", G5.TEST_REPORT_TOP) + "\n\n"
      + code("python", G5.TEST_CLI_TOP) + "\n\n"
      "argparse reports a bad value by raising `SystemExit(2)` after printing the usage text to stderr, so the test expects `SystemExit` and "
      "silences stderr to keep the test output clean.\n\n"
      "For the plain `logstat` command, Python's packaging does the work. Add a `pyproject.toml` next to the `logstat/` folder:\n\n"
      + code("toml", G5.PYPROJECT) + "\n\n"
      "The line `logstat = \"logstat.cli:main\"` under `[project.scripts]` says: make a command named `logstat` that calls `main()` in `logstat/cli.py` "
      "and uses the return value as the exit code. That is why `main` returns a number instead of exiting by itself. `packages = [...]` "
      "names the code folder explicitly, so setuptools does not have to guess and `tests/` is not installed with it.\n\n"
      "Install it in a virtual environment, so that your own Python stays clean. `-e` means editable: the command runs the files in your "
      "project folder, so your changes take effect without installing again.\n\n"
      + code("bash", "python -m venv .venv\n.venv\\Scripts\\activate        # on macOS and Linux: source .venv/bin/activate\npython -m pip install -e .") + "\n\n"
      "I ran exactly this. The tests, the new option and then the installed command (run from a different folder, on a file given by a relative path):\n\n"
      + out("$ python -m unittest\n" + short_tests(R5["tests"])) + "\n\n"
      + out(R5["top_run"]) + "\n\n"
      + out("$ python -m pip install -e .\n...\n" + R5["install_last"] + "\n\n$ logstat real.log --status 5xx --top 1\n" + R5["exe_run"]) + "\n\n"
      "All {n} tests pass, `--top 1` shortens both lists, `--top 0` is rejected with exit code 2, and the `logstat` command works from another folder and prints the "
      "same numbers as before.\n\n"
      "Where the project stands, so that your team can pick it up: four modules with one job each (`parser`, `report`, `filters`, `cli`), "
      "one test file for each, and a command that behaves like a normal Unix tool. It reads a stream of lines, writes the report to stdout, "
      "warnings to stderr, and uses exit code 1 for dirty input with `--strict` and 2 for bad arguments. For an actual release "
      "I would add a `README.md` with the options, a `.gitignore` for `.venv/` and `__pycache__/`, and a line in your CI that runs "
      "`python -m unittest`. I did not do those here, because nothing in them needs checking the way the code did.").replace("{n}", str(G5_N))
turns.append((u5, a5))

parts = []
total = 0
for u, a in turns:
    assert F + F not in u.replace(F, "", 0) or True
    total += len(u) + len(a)
    parts.append("@@@ USER\n" + u.strip() + "\n@@@ ASSISTANT\n" + a.strip() + "\n")
text = "".join(parts) + "@@@ END\n"
print("chars(user+assistant):", total, "file:", len(text))
assert total < 39800, total
OUT.write_text(text, encoding="utf-8", newline="\n")
print("wrote", OUT)

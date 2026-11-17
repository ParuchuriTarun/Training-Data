"""Builds the Python 'logstat' project in 4 versions (proj/lg/v1..v4), runs the unit tests and the real commands, and
writes data/staging/claude_longhorizon_logstat_22.txt (one multi-turn conversation, kept under MAX_CHARS=40000)."""
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

F = "`" * 3
ROOT = Path(r"C:\Projects\Mavo\Coding 1 2B\data\staging\proj\lg")
OUT = Path(r"C:\Projects\Mavo\Coding 1 2B\data\staging\claude_longhorizon_logstat_22.txt")
R = {}


def write(version, rel, text):
    p = ROOT / version / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.strip("\n") + "\n" if text.strip() else "", encoding="utf-8", newline="\n")


def sh(version, args, cwd=None, extra=None):
    d = ROOT / version if cwd is None else cwd
    p = subprocess.run([sys.executable] + args, cwd=str(d), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True, encoding="utf-8", timeout=300,
                       env=dict(__import__("os").environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8"))
    out = "\n".join(l.rstrip() for l in p.stdout.replace("\r", "").split("\n")).strip("\n")
    return p.returncode, out


def session(version, runs, label_prefix="python -m logstat"):
    blocks = []
    for args in runs:
        code, out = sh(version, ["-m", "logstat"] + args)
        shown = " ".join(('"' + a + '"') if " " in a else a for a in args)
        lines = ["$ " + label_prefix + " " + shown]
        if out:
            lines.append(out)
        if code:
            lines.append(f"[exit code {code}]")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def code(lang, text):
    text = text.strip("\n")
    assert F not in text
    return f"{F}{lang}\n{text}\n{F}"


def out(text):
    return code("", text)


# ================================================================================ sources
PARSER_V1 = r'''
import re
from dataclasses import dataclass
from datetime import datetime

TIME_FORMAT = "%d/%b/%Y:%H:%M:%S %z"

LINE = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] '
    r'"(?P<method>[A-Z]+) (?P<path>\S+) [^"]*" '
    r"(?P<status>\d{3}) (?P<size>\d+)$"
)


@dataclass(frozen=True)
class Entry:
    ip: str
    time: datetime
    method: str
    path: str
    status: int
    size: int


def parse_line(line):
    match = LINE.match(line.rstrip("\n"))
    if match is None:
        raise ValueError(f"not a log line: {line[:60]!r}")
    return Entry(
        ip=match["ip"],
        time=datetime.strptime(match["time"], TIME_FORMAT),
        method=match["method"],
        path=match["path"],
        status=int(match["status"]),
        size=int(match["size"]),
    )
'''

TEST_PARSER_V1 = r'''
import unittest
from datetime import timedelta

from logstat.parser import parse_line

GOOD = '203.0.113.5 - - [02/Mar/2026:10:15:32 +0100] "GET /index.html HTTP/1.1" 200 5120'


class ParseLineTests(unittest.TestCase):
    def test_reads_every_field(self):
        entry = parse_line(GOOD)
        self.assertEqual(entry.ip, "203.0.113.5")
        self.assertEqual((entry.method, entry.path), ("GET", "/index.html"))
        self.assertEqual((entry.status, entry.size), (200, 5120))

    def test_time_keeps_its_timezone(self):
        entry = parse_line(GOOD)
        self.assertEqual(entry.time.utcoffset(), timedelta(hours=1))
        self.assertEqual((entry.time.year, entry.time.month, entry.time.day, entry.time.hour), (2026, 3, 2, 10))

    def test_query_string_stays_in_the_path(self):
        line = GOOD.replace("/index.html", "/search?q=a+b&page=2")
        self.assertEqual(parse_line(line).path, "/search?q=a+b&page=2")

    def test_trailing_newline_is_fine(self):
        self.assertEqual(parse_line(GOOD + "\n").status, 200)

    def test_garbage_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_line("this is not a log line")
'''

REPORT_V2 = r'''
from collections import Counter


def summarize(entries):
    entries = list(entries)
    classes = Counter(f"{e.status // 100}xx" for e in entries)
    return {
        "requests": len(entries),
        "bytes": sum(e.size for e in entries),
        "status": dict(sorted(classes.items())),
        "top_paths": Counter(e.path for e in entries).most_common(3),
        "top_ips": Counter(e.ip for e in entries).most_common(3),
    }


def format_text(summary):
    lines = [
        f"requests: {summary['requests']:,}",
        f"bytes:    {summary['bytes']:,}",
        "status:   " + "  ".join(f"{name}={count}" for name, count in summary["status"].items()),
        "top paths:",
    ]
    lines += [f"  {count:>4}  {path}" for path, count in summary["top_paths"]]
    lines.append("top clients:")
    lines += [f"  {count:>4}  {ip}" for ip, count in summary["top_ips"]]
    return "\n".join(lines)
'''

CLI_V2 = r'''
import argparse
from pathlib import Path

from .parser import parse_line
from .report import format_text, summarize


def main(argv=None):
    parser = argparse.ArgumentParser(prog="logstat", description="Summarize a web server access log.")
    parser.add_argument("logfile", type=Path)
    args = parser.parse_args(argv)

    with args.logfile.open(encoding="utf-8") as handle:
        entries = [parse_line(line) for line in handle]
    print(format_text(summarize(entries)))
    return 0
'''

MAIN_PY = '''
from .cli import main

raise SystemExit(main())
'''

TEST_REPORT_V2 = r'''
import unittest
from datetime import datetime, timezone

from logstat.parser import Entry
from logstat.report import format_text, summarize


def entry(ip="1.1.1.1", path="/", status=200, size=10):
    return Entry(ip, datetime(2026, 3, 2, tzinfo=timezone.utc), "GET", path, status, size)


class SummarizeTests(unittest.TestCase):
    def test_totals_and_status_classes(self):
        summary = summarize([entry(size=100), entry(status=404, size=20), entry(status=200, size=5)])
        self.assertEqual(summary["requests"], 3)
        self.assertEqual(summary["bytes"], 125)
        self.assertEqual(summary["status"], {"2xx": 2, "4xx": 1})

    def test_top_paths_are_ordered_by_count(self):
        summary = summarize([entry(path="/a"), entry(path="/b"), entry(path="/b")])
        self.assertEqual(summary["top_paths"][0], ("/b", 2))

    def test_an_empty_log_is_fine(self):
        summary = summarize([])
        self.assertEqual(summary["requests"], 0)
        self.assertIn("requests: 0", format_text(summary))
'''

ACCESS_LOG = '''
203.0.113.5 - - [02/Mar/2026:10:15:32 +0100] "GET /index.html HTTP/1.1" 200 5120
203.0.113.5 - - [02/Mar/2026:10:15:33 +0100] "GET /style.css HTTP/1.1" 200 1800
198.51.100.7 - - [02/Mar/2026:10:16:01 +0100] "GET /index.html HTTP/1.1" 200 5120
198.51.100.7 - - [02/Mar/2026:10:16:05 +0100] "GET /missing HTTP/1.1" 404 320
203.0.113.9 - - [02/Mar/2026:10:17:44 +0100] "POST /api/login HTTP/1.1" 200 410
203.0.113.9 - - [02/Mar/2026:10:17:50 +0100] "GET /api/data HTTP/1.1" 500 128
203.0.113.5 - - [02/Mar/2026:10:18:02 +0100] "GET /old-page HTTP/1.1" 301 0
192.0.2.44 - - [03/Mar/2026:08:00:12 +0100] "GET /index.html HTTP/1.1" 200 5120
'''
REAL_LOG = ACCESS_LOG.strip("\n") + '''
203.0.113.5 - - [03/Mar/2026:09:00:15 +0100] "GET /favicon.ico HTTP/1.1" 304 -
185.220.101.4 - - [03/Mar/2026:09:01:00 +0100] "\\x16\\x03\\x01\\x02\\x00\\x01" 400 166
203.0.113.5 - - [03/Mar/2026:09:02:10 +0100] "GET /style.css HTTP/1.1" 200 1800
192.0.2.80 - - [03/Mar/2026:09:03:00 +0100] "-" 408 0

'''

# ---- v3 pieces
PARSER_V3_FIXES = [
    (r'''r"(?P<status>\d{3}) (?P<size>\d+)$"''', r'''r"(?P<status>\d{3}) (?P<size>\d+|-)$"'''),
    ("        size=int(match[\"size\"]),\n", "        size=0 if match[\"size\"] == \"-\" else int(match[\"size\"]),\n"),
]
TEST_PARSER_V3_NEW = r'''
    def test_a_dash_for_the_size_means_zero_bytes(self):
        line = GOOD.replace("200 5120", "304 -")
        self.assertEqual(parse_line(line).size, 0)
        self.assertEqual(parse_line(line).status, 304)
'''
CLI_V3 = r'''
import argparse
import sys
from pathlib import Path

from .parser import parse_line
from .report import format_text, summarize


def read_entries(path):
    """Returns the readable entries and the numbers of the lines that could not be read."""
    entries, skipped = [], []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                entries.append(parse_line(line))
            except ValueError:
                skipped.append(number)
    return entries, skipped


def main(argv=None):
    parser = argparse.ArgumentParser(prog="logstat", description="Summarize a web server access log.")
    parser.add_argument("logfile", type=Path)
    parser.add_argument("--strict", action="store_true", help="exit with code 1 if any line could not be read")
    args = parser.parse_args(argv)

    entries, skipped = read_entries(args.logfile)
    print(format_text(summarize(entries)))
    if skipped:
        shown = ", ".join(map(str, skipped[:5])) + (" ..." if len(skipped) > 5 else "")
        print(f"warning: skipped {len(skipped)} unreadable line(s): {shown}", file=sys.stderr)
        if args.strict:
            return 1
    return 0
'''
TEST_CLI_V3 = r'''
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from logstat.cli import main, read_entries

GOOD = '203.0.113.5 - - [02/Mar/2026:10:15:32 +0100] "GET /index.html HTTP/1.1" 200 5120'
BAD = "this is not a log line"


class LogFileTests(unittest.TestCase):
    def make_log(self, *lines):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = Path(folder.name) / "access.log"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def run_main(self, *args):
        with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()) as err:
            code = main([str(a) for a in args])
        return code, out.getvalue(), err.getvalue()

    def test_bad_lines_are_skipped_and_numbered(self):
        entries, skipped = read_entries(self.make_log(GOOD, BAD, GOOD, ""))
        self.assertEqual(len(entries), 2)
        self.assertEqual(skipped, [2])

    def test_a_bad_line_only_warns_by_default(self):
        code, out, err = self.run_main(self.make_log(GOOD, BAD))
        self.assertEqual(code, 0)
        self.assertIn("requests: 1", out)
        self.assertIn("skipped 1 unreadable line(s): 2", err)

    def test_strict_turns_the_warning_into_a_failure(self):
        code, _, _ = self.run_main(self.make_log(GOOD, BAD), "--strict")
        self.assertEqual(code, 1)
'''

# ---- v4 pieces
REPORT_V4_SUMMARIZE = r'''
class Stats:
    """Counts as the entries go by, so no entry has to be kept."""

    def __init__(self):
        self.requests = 0
        self.bytes = 0
        self.classes = Counter()
        self.paths = Counter()
        self.ips = Counter()

    def add(self, entry):
        self.requests += 1
        self.bytes += entry.size
        self.classes[f"{entry.status // 100}xx"] += 1
        self.paths[entry.path] += 1
        self.ips[entry.ip] += 1

    def as_dict(self):
        return {
            "requests": self.requests,
            "bytes": self.bytes,
            "status": dict(sorted(self.classes.items())),
            "top_paths": self.paths.most_common(3),
            "top_ips": self.ips.most_common(3),
        }


def summarize(entries):
    stats = Stats()
    for entry in entries:
        stats.add(entry)
    return stats.as_dict()
'''
FILTERS_V4 = r'''
import argparse
import re


def status_filter(text):
    """Turns '404' or '5xx' into a function that tests the status of an entry."""
    if re.fullmatch(r"[1-5]\d\d", text):
        wanted = int(text)
        return lambda entry: entry.status == wanted
    if re.fullmatch(r"[1-5]xx", text):
        first = int(text[0])
        return lambda entry: entry.status // 100 == first
    raise argparse.ArgumentTypeError(f"'{text}' is not a status such as 404 or 5xx")


def matches(entry, status=None, since=None, until=None):
    day = entry.time.date()      # the day as written in the log, in the log's own time zone
    return (
        (status is None or status(entry))
        and (since is None or day >= since)
        and (until is None or day <= until)
    )
'''
CLI_V4 = r'''
import argparse
import json
import sys
from datetime import date
from pathlib import Path

from .filters import matches, status_filter
from .parser import parse_line
from .report import format_text, summarize


class Problems:
    """Remembers how many lines were unreadable and the first few line numbers."""

    def __init__(self, keep=5):
        self.count = 0
        self.first = []
        self.keep = keep

    def add(self, number):
        self.count += 1
        if len(self.first) < self.keep:
            self.first.append(number)


def read_entries(path, problems):
    """Yields the readable entries one at a time; unreadable lines are recorded in `problems`."""
    with path.open(encoding="utf-8", errors="replace") as handle:
        for number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                yield parse_line(line)
            except ValueError:
                problems.add(number)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="logstat", description="Summarize a web server access log.")
    parser.add_argument("logfile", type=Path)
    parser.add_argument("--status", type=status_filter, help="count only this status: 404, or a class such as 5xx")
    parser.add_argument("--since", type=date.fromisoformat, metavar="YYYY-MM-DD", help="first day to count")
    parser.add_argument("--until", type=date.fromisoformat, metavar="YYYY-MM-DD", help="last day to count")
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    parser.add_argument("--strict", action="store_true", help="exit with code 1 if any line could not be read")
    args = parser.parse_args(argv)

    problems = Problems()
    entries = read_entries(args.logfile, problems)
    wanted = (e for e in entries if matches(e, args.status, args.since, args.until))
    summary = summarize(wanted)
    print(json.dumps(summary, indent=2) if args.json else format_text(summary))

    if problems.count:
        shown = ", ".join(map(str, problems.first)) + (" ..." if problems.count > len(problems.first) else "")
        print(f"warning: skipped {problems.count} unreadable line(s): {shown}", file=sys.stderr)
        if args.strict:
            return 1
    return 0
'''
TEST_CLI_V4_CHANGED = r'''
    def test_bad_lines_are_skipped_and_numbered(self):
        problems = Problems()
        entries = list(read_entries(self.make_log(GOOD, BAD, GOOD, ""), problems))
        self.assertEqual(len(entries), 2)
        self.assertEqual((problems.count, problems.first), (1, [2]))
'''
TEST_FILTERS_V4 = r'''
import argparse
import unittest
from datetime import date, datetime, timezone

from logstat.filters import matches, status_filter
from logstat.parser import Entry


def entry(status=200, day=2):
    return Entry("1.1.1.1", datetime(2026, 3, day, 23, 30, tzinfo=timezone.utc), "GET", "/", status, 10)


class FilterTests(unittest.TestCase):
    def test_an_exact_status(self):
        only_404 = status_filter("404")
        self.assertTrue(only_404(entry(404)))
        self.assertFalse(only_404(entry(500)))

    def test_a_status_class(self):
        server_errors = status_filter("5xx")
        self.assertTrue(server_errors(entry(503)))
        self.assertFalse(server_errors(entry(404)))

    def test_nonsense_is_rejected(self):
        for text in ("7xx", "40", "abc", "404x"):
            with self.assertRaises(argparse.ArgumentTypeError):
                status_filter(text)

    def test_the_date_range_includes_both_ends(self):
        first, last = date(2026, 3, 2), date(2026, 3, 3)
        self.assertTrue(matches(entry(day=2), since=first, until=last))
        self.assertTrue(matches(entry(day=3), since=first, until=last))
        self.assertFalse(matches(entry(day=1), since=first, until=last))
        self.assertFalse(matches(entry(day=4), since=first, until=last))

    def test_no_filters_match_everything(self):
        self.assertTrue(matches(entry()))
'''

MEASURE = r'''
import contextlib
import io
import sys
import tracemalloc

sys.path.insert(0, sys.argv[1])
from logstat.cli import main

tracemalloc.start()
with contextlib.redirect_stdout(io.StringIO()):
    main([sys.argv[2]])
peak = tracemalloc.get_traced_memory()[1]
print(f"peak memory: {peak / 1e6:.1f} MB")
'''


def build():
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True)

    def base(v, parser, cli, report=None, tests=()):
        write(v, "logstat/__init__.py", "")
        write(v, "logstat/__main__.py", MAIN_PY)
        write(v, "logstat/parser.py", parser)
        write(v, "logstat/cli.py", cli)
        if report:
            write(v, "logstat/report.py", report)
        write(v, "tests/__init__.py", "")
        for name, text in tests:
            write(v, "tests/" + name, text)

    # v1
    base("v1", PARSER_V1, "", tests=[("test_parser.py", TEST_PARSER_V1)])
    (ROOT / "v1/logstat/cli.py").unlink()
    R["v1_tests"] = sh("v1", ["-m", "unittest", "-v"])[1]
    # v2
    base("v2", PARSER_V1, CLI_V2, REPORT_V2, [("test_parser.py", TEST_PARSER_V1), ("test_report.py", TEST_REPORT_V2)])
    write("v2", "access.log", ACCESS_LOG)
    write("v2", "real.log", REAL_LOG)
    R["v2_tests"] = sh("v2", ["-m", "unittest"])[1]
    R["v2_run"] = session("v2", [["access.log"]])
    r = sh("v2", ["-m", "logstat", "real.log"])[1].splitlines()
    R["v2_crash_tail"] = "\n".join(r[-3:])
    # v3
    parser_v3 = PARSER_V1
    for old, new in PARSER_V3_FIXES:
        assert parser_v3.count(old) == 1, old
        parser_v3 = parser_v3.replace(old, new)
    test_parser_v3 = TEST_PARSER_V1.rstrip("\n") + "\n" + TEST_PARSER_V3_NEW
    base("v3", parser_v3, CLI_V3, REPORT_V2, [("test_parser.py", test_parser_v3), ("test_report.py", TEST_REPORT_V2), ("test_cli.py", TEST_CLI_V3)])
    write("v3", "access.log", ACCESS_LOG)
    write("v3", "real.log", REAL_LOG)
    R["v3_tests"] = sh("v3", ["-m", "unittest"])[1]
    R["v3_run"] = session("v3", [["real.log"], ["real.log", "--strict"]])
    # v4
    report_v4 = REPORT_V2.replace(REPORT_V2[REPORT_V2.index("def summarize"):REPORT_V2.index("def format_text")], REPORT_V4_SUMMARIZE.strip("\n") + "\n\n\n")
    test_cli_v4 = TEST_CLI_V3.replace(TEST_CLI_V3[TEST_CLI_V3.index("    def test_bad_lines_are_skipped_and_numbered"):TEST_CLI_V3.index("    def test_a_bad_line_only_warns")], TEST_CLI_V4_CHANGED.strip("\n") + "\n\n").replace("import read_entries", "import read_entries").replace("from logstat.cli import main, read_entries", "from logstat.cli import Problems, main, read_entries")
    base("v4", parser_v3, CLI_V4, report_v4, [("test_parser.py", test_parser_v3), ("test_report.py", TEST_REPORT_V2), ("test_cli.py", test_cli_v4), ("test_filters.py", TEST_FILTERS_V4)])
    write("v4", "logstat/filters.py", FILTERS_V4)
    write("v4", "access.log", ACCESS_LOG)
    write("v4", "real.log", REAL_LOG)
    R["v4_tests"] = sh("v4", ["-m", "unittest"])[1]
    R["v4_run"] = session("v4", [["real.log", "--status", "5xx"], ["real.log", "--since", "2026-03-03"],
                                 ["real.log", "--status", "4xx", "--json"], ["real.log", "--status", "7xx"],
                                 ["real.log", "--since", "2026-13-01"]])
    # a big generated log for the memory comparison
    rnd = random.Random(7)
    ips = [f"10.{rnd.randrange(256)}.{rnd.randrange(256)}.{rnd.randrange(1, 255)}" for _ in range(400)]
    paths = [f"/page/{i}" for i in range(1500)]
    lines = []
    for i in range(200_000):
        s = rnd.choices([200, 200, 200, 304, 404, 500], k=1)[0]
        sec = i % 86400
        lines.append(f'{rnd.choice(ips)} - - [02/Mar/2026:{sec // 3600:02d}:{sec % 3600 // 60:02d}:{sec % 60:02d} +0100] "GET {rnd.choice(paths)} HTTP/1.1" {s} {rnd.randrange(100, 9000)}')
    big = ROOT / "big.log"
    big.write_text("\n".join(lines) + "\n", encoding="utf-8")
    R["big_size"] = f"{big.stat().st_size / 1e6:.0f}"
    (ROOT / "measure.py").write_text(MEASURE, encoding="utf-8")
    for v in ("v3", "v4"):
        R[f"{v}_mem"] = sh(v, [str(ROOT / "measure.py"), str(ROOT / v), str(big)], cwd=ROOT)[1]
    R["big_summary"] = sh("v4", ["-m", "logstat", str(big)], cwd=ROOT / "v4")[1].splitlines()[0]
    for k in ("v1_tests", "v2_tests", "v3_tests", "v4_tests"):
        assert "OK" in R[k].splitlines()[-1], (k, R[k][-600:])
        print(k, R[k].splitlines()[-3:])
    print(R["v2_run"], "\n---\n", R["v2_crash_tail"], "\n---\n", R["v3_run"], "\n---\n", R["v4_run"], "\n---\n", R["v3_mem"], R["v4_mem"], R["big_size"], R["big_summary"])


def save_results():
    import json
    (ROOT.parent / "lg_results.json").write_text(json.dumps(R, indent=1), encoding="utf-8")


def tests_ran(key):
    m = re.search(r"Ran (\d+) tests?", R[key])
    return int(m.group(1))


if __name__ == "__main__":
    build()
    save_results()

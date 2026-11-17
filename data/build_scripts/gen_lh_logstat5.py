"""Builds v5 of logstat (v4 + --top + pyproject/console script), runs it for real, saves lg_results5.json."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import gen_lh_logstat as G
from gen_lh_logstat import ROOT, sh

R5 = {}

PYPROJECT = '''[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "logstat"
version = "0.1.0"
description = "Summarize a web server access log"

[project.scripts]
logstat = "logstat.cli:main"

[tool.setuptools]
packages = ["logstat"]
'''

TEST_REPORT_TOP = r'''

    def test_top_controls_how_many_paths_and_clients_are_listed(self):
        entries = [entry(path="/a"), entry(path="/a"), entry(path="/b"), entry(path="/c")]
        self.assertEqual(len(summarize(entries)["top_paths"]), 3)
        self.assertEqual(summarize(entries, top=1)["top_paths"], [("/a", 2)])
'''

TEST_CLI_TOP = r'''

    def test_top_must_be_a_positive_whole_number(self):
        for bad in ("0", "-2", "three"):
            with self.assertRaises(SystemExit) as caught, redirect_stderr(io.StringIO()):
                main([str(self.make_log(GOOD)), "--top", bad])
            self.assertEqual(caught.exception.code, 2)
'''

POSITIVE_INT = '''def positive_int(text):
    try:
        value = int(text)
    except ValueError:
        value = 0
    if value < 1:
        raise argparse.ArgumentTypeError(f"'{text}' is not a whole number of 1 or more")
    return value


'''


def rep(text, old, new, n=1):
    assert text.count(old) == n, (old, text.count(old))
    return text.replace(old, new)


def build5():
    src, dst = ROOT / "v4", ROOT / "v5"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))

    rp = dst / "logstat/report.py"
    t = rp.read_text(encoding="utf-8")
    t = rep(t, "    def as_dict(self):", "    def as_dict(self, top=3):")
    t = rep(t, "most_common(3)", "most_common(top)", 2)
    t = rep(t, "def summarize(entries):", "def summarize(entries, top=3):")
    t = rep(t, "return stats.as_dict()", "return stats.as_dict(top)")
    rp.write_text(t, encoding="utf-8", newline="\n")

    cp = dst / "logstat/cli.py"
    t = cp.read_text(encoding="utf-8")
    t = rep(t, "def main(argv=None):", POSITIVE_INT + "def main(argv=None):")
    t = rep(t, '    parser.add_argument("--json"', '    parser.add_argument("--top", type=positive_int, default=3, help="how many paths and clients to list (default 3)")\n    parser.add_argument("--json"')
    t = rep(t, "summary = summarize(wanted)", "summary = summarize(wanted, args.top)")
    cp.write_text(t, encoding="utf-8", newline="\n")
    R5["positive_int"] = POSITIVE_INT.strip("\n")

    for rel, extra in (("tests/test_report.py", TEST_REPORT_TOP), ("tests/test_cli.py", TEST_CLI_TOP)):
        p = dst / rel
        p.write_text(p.read_text(encoding="utf-8").rstrip("\n") + "\n" + extra, encoding="utf-8", newline="\n")
    (dst / "pyproject.toml").write_text(PYPROJECT, encoding="utf-8", newline="\n")

    R5["tests"] = sh("v5", ["-m", "unittest"])[1]
    assert "OK" in R5["tests"].splitlines()[-1], R5["tests"][-800:]
    R5["top_run"] = G.session("v5", [["real.log", "--top", "1"], ["real.log", "--top", "0"]])

    env = dst / ".venv"
    subprocess.run([sys.executable, "-m", "venv", str(env)], check=True, cwd=str(dst))
    py = env / "Scripts" / "python.exe"
    p = subprocess.run([str(py), "-m", "pip", "install", "-e", ".", "--disable-pip-version-check"], cwd=str(dst),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", timeout=600)
    last = [l for l in p.stdout.splitlines() if l.strip()][-1]
    assert p.returncode == 0 and "Successfully installed logstat" in last, p.stdout[-1500:]
    R5["install_last"] = last
    exe = env / "Scripts" / "logstat.exe"
    assert exe.exists()
    # run the installed command from a different folder, on a file given by path
    other = ROOT / "elsewhere"
    other.mkdir(exist_ok=True)
    shutil.copy(dst / "real.log", other / "real.log")
    q = subprocess.run([str(exe), "real.log", "--status", "5xx", "--top", "1"], cwd=str(other), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True, encoding="utf-8", timeout=60)
    R5["exe_run"] = "\n".join(l.rstrip() for l in q.stdout.replace("\r", "").splitlines()).strip("\n")
    R5["exe_code"] = q.returncode
    assert q.returncode == 0 and "requests: 1" in R5["exe_run"], R5["exe_run"]
    shutil.rmtree(env, ignore_errors=True)
    (ROOT.parent / "lg_results5.json").write_text(json.dumps(R5, indent=1), encoding="utf-8")
    print(R5["tests"][-60:], "\n", R5["top_run"], "\n", R5["install_last"], "\n", R5["exe_run"])


if __name__ == "__main__":
    build5()

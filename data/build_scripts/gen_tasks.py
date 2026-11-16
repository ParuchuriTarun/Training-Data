"""Builds data/staging/claude_longhorizon_tasks_19.txt from the REAL project files in proj/tasks/ and the
REAL outputs in proj/tasks/results.json (see tasks_src.py)."""
import json
import re
from pathlib import Path

ROOT = Path(r"C:\Projects\Mavo\Coding 1 2B\data\staging\proj\tasks")
OUT = Path(r"C:\Projects\Mavo\Coding 1 2B\data\staging\claude_longhorizon_tasks_19.txt")
F = "`" * 3
R = json.loads((ROOT / "results.json").read_text(encoding="utf-8"))


def rd(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def chunk(text, start, end, include_end=True):
    i = text.index(start)
    j = text.index(end, i)
    return text[i : j + (len(end) if include_end else 0)]


def before(text, marker):
    return text[: text.index(marker)]


def code(lang, text):
    text = re.sub(r"\n{3,}", "\n\n", text.strip("\n"))
    assert F not in text, "nested fence"
    return f"{F}{lang}\n{text}\n{F}"


def out(text):
    return code("", text)


def clean(text):
    return re.sub(r"(thread '[^']*') \(\d+\)", r"\1", text)


def tests_full(key):
    return clean(R[key + "_test"]["stdout"].strip("\n"))


def tests_trim(key):
    lines = clean(R[key + "_test"]["stdout"].strip("\n")).splitlines()
    head = lines[0]
    failed = [l for l in lines if l.endswith("FAILED")]
    tail = lines[lines.index("failures:") :]
    return "\n".join([head, "..."] + failed + ["..."] + [""] + tail)


def result_line(key):
    for l in R[key + "_test"]["stdout"].splitlines():
        if l.startswith("test result:"):
            return l
    raise SystemExit("no result line for " + key)


def passed(key):
    m = re.search(r"test result: \w+\. (\d+) passed; (\d+) failed", R[key + "_test"]["stdout"])
    return int(m.group(1)), int(m.group(2))


def session(recs, short=False, codes=True):
    blocks = []
    for r in recs:
        lines = ["$ " + r["cmd"].rstrip()]
        if r["out"]:
            lines.append(r["out"].rstrip("\n"))
        if r["err"]:
            e = r["err"].rstrip("\n")
            if short and "\n\nusage:" in e:
                e = e.split("\n\nusage:")[0] + "\n(the usage text follows here)"
            lines.append(e)
        if r["code"] != 0 and codes:
            lines.append(f"[exit code {r['code']}]")
        blocks.append("\n".join(lines))
    return "\n".join(blocks)


# ------------------------------------------------------------------------------ pieces from the real files
t1, t1_main, t1_cargo = rd("v1/src/task.rs"), rd("v1/src/main.rs"), rd("v1/Cargo.toml")
t1_body = before(t1, "#[cfg(test)]")
# The loader drops examples longer than MAX_CHARS (40,000), so the conversation shows excerpts of the longer test lists.
t1_tests = (
    chunk(t1, "#[cfg(test)]", "    #[test]\n    fn wrong_field_count_is_an_error", include_end=False)
    + "    // ... one test each for the wrong field count, a bad id, a bad done flag, an unknown\n"
    + "    // priority, the priority order and the priority text, in the same style ...\n}"
)

t2, s2, c2 = rd("v2/src/task.rs"), rd("v2/src/store.rs"), rd("v2/src/cli.rs")
m2 = rd("v2/src/main.rs")
s2_body = before(s2, "#[cfg(test)]\npub fn temp_path")
s2_temp = chunk(s2, "#[cfg(test)]\npub fn temp_path", "\n}\n")
c2_body = before(c2, "#[cfg(test)]\nmod tests")
c2_test = chunk(c2, "    #[test]\n    fn list_shows_priority_and_due_date", "\n    }\n")
t2_display = chunk(t2, "impl fmt::Display for Priority", "\n}\n")
t2_width_test = chunk(t2, "    #[test]\n    fn priority_respects_a_width", "\n    }\n")

d3, c3 = rd("v3/src/date.rs"), rd("v3/src/cli.rs")
d3_body = before(d3, "#[cfg(test)]")
d3_leap = chunk(d3, "    #[test]\n    fn february_follows", "\n    }\n")
d3_ascii = chunk(d3, "    #[test]\n    fn non_ascii_digits", "\n    }\n")
c3_due = chunk(c3, '            "--due" => {', "\n            }\n")
c3_list = chunk(c3, "fn list(", "\nfn format_task", include_end=False)
c3_helpers = chunk(c3, "    fn ids(", "\n    }\n") + "\n\n" + chunk(c3, "    fn add_four(", "\n    }\n")
c3_due_test = chunk(c3, "    #[test]\n    fn list_sorts_by_due_date", "\n    }\n")

t4a = rd("v4a/src/task.rs")
t4, s4, c4 = rd("v4/src/task.rs"), rd("v4/src/store.rs"), rd("v4/src/cli.rs")
t4a_test = chunk(t4a, "    #[test]\n    fn a_title_with_a_pipe_round_trips", "\n    }\n")
t4_toline = chunk(t4, "    /// One task per line", "\n    }\n")
t4_fromline_head = chunk(t4, "    pub fn from_line", "        let id = parts[0]", include_end=False)
t4_helpers = chunk(t4, "/// Makes a field safe", "#[cfg(test)]", include_end=False)
t4_new_tests = chunk(t4, "    #[test]\n    fn backslashes_and_line_breaks_round_trip", "    #[test]\n    fn bad_escapes_are_errors", include_end=False)
assert R["v4_tmp_left"] == ["tasks.txt"]
s4_io = chunk(s4, "/// Reads every task", "pub fn next_id", include_end=False)
s4_new_tests = chunk(s4, "    #[test]\n    fn a_bad_line_is_an_error_that_names_the_line", "\n    }\n") + "\n\n" + chunk(s4, "    #[test]\n    fn save_leaves_no_temporary_file_behind", "\n    }\n")

c5, m5 = rd("v5/src/cli.rs"), rd("v5/src/main.rs")
c5_head = chunk(c5, "#[derive(Debug, PartialEq)]", "fn value<'a>", include_end=False)
c5_edit = chunk(c5, "fn edit(", "\nfn stats(", include_end=False)
c5_stats = chunk(c5, "fn stats(", "#[cfg(test)]", include_end=False)
c5_tests = chunk(c5, "    #[test]\n    fn edit_reports_what_is_wrong", "\n    }\n") + "\n\n" + chunk(c5, "    #[test]\n    fn mistakes_in_the_command_line", "\n    }\n")

n1, n2, n3, n4, n5 = (passed(k)[0] for k in ("v1", "v2", "v3", "v4", "v5"))
assert passed("v2a") == (n2 - 2, 1), (passed("v2a"), n2)  # v2 adds the width test and the failing one now passes
assert passed("v4a")[1] == 1

# ------------------------------------------------------------------------------ the conversation
turns = []


def user(text):
    turns.append(("USER", text.strip()))


def assistant(*parts):
    turns.append(("ASSISTANT", "\n\n".join(p.strip("\n") for p in parts)))


# ---- turn 1 -------------------------------------------------------------------------------------
user('''
I want to build a small command-line task manager in Rust. Standard library only, no crates. Each task has a title, a done flag, a priority and an optional due date, and the list is saved in a plain text file. Where do I start?
''')

assistant(
    '''
Start with the data, not with the command line. The program is mostly rules (what a task is, how it is written to a file and read back), and those rules can live in plain functions that you can test without touching the terminal or the disk. The commands come later as a thin layer on top.

The layers:
1. `task.rs`: `Task`, `Priority` and the text format of one task. No files, no terminal.
2. `store.rs`: reads and writes the file.
3. `cli.rs`: turns command-line arguments into actions and returns the text to print.
4. `main.rs`: a few lines that connect these to the real process.

The file format is one task per line, `id|title|done|priority|due`, for example `7|Write report|false|high|2026-03-01`. It is readable, easy to edit by hand and easy to compare with `git diff`. JSON would be the usual choice, but without crates there is no serde, and a hand-written JSON parser would be bigger than the rest of this program.

Create the project:''',
    code("bash", "cargo new tasks\ncd tasks"),
    "`Cargo.toml` stays as generated, with an empty `[dependencies]` section:",
    code("toml", t1_cargo),
    "For now only `src/main.rs` and `src/task.rs` matter. `main.rs`:",
    code("rust", t1_main),
    "The attribute silences the \"never used\" warnings for the module; nothing calls it yet. Now `src/task.rs`:",
    code("rust", t1_body),
    '''
How it works:
- `Priority` derives `PartialOrd` and `Ord`. Variants compare in the order they are declared, so `Low < Normal < High`. That gives us sorting by priority later for free.
- `Display` turns a priority into `high` for writing, and `FromStr` does the reverse, so `"high".parse::<Priority>()` works. Unknown text is an `Err` with a message.
- `due` is an `Option<String>`. `None` is written as an empty last field, and `as_deref()` turns `Option<String>` into `Option<&str>` so `unwrap_or("")` works without cloning.
- `from_line` checks the number of fields first, so the indexing of `parts[0]` to `parts[4]` can never go out of bounds. Then it checks each field and says which one is wrong. The errors are plain `String` messages for now.

One gap I already know about: the title is written exactly as it is, so a title that contains `|` cannot be read back. I am leaving that until the basic commands work, and then I will come back to it properly.

Now the tests, which are the specification of the format. They go at the bottom of `task.rs`:''',
    code("rust", t1_tests),
    '''
`assert_eq!` can compare `Result<Task, String>` values because `Task` derives `PartialEq` and `Debug`. Run them with one test at a time, so the output order is stable:''',
    code("bash", "cargo test -- --test-threads=1"),
    out(tests_full("v1")),
    "All " + str(n1) + " pass. Next comes the storage and the first commands.",
)

# ---- turn 2 -------------------------------------------------------------------------------------
user('''
Good. Now make it a real tool: add, list, done and rm, saved to a file. Let me choose the file location with an environment variable.
''')

assistant(
    '''
Two design decisions first:
1. `run(args, path)` returns `Result<String, String>`: the text to print, or an error message. It never prints and never exits. Tests can call it directly and compare the text, and `main` is the only place that touches stdout, stderr and the exit code.
2. The file path is a parameter, not a constant. `main` reads it from `TASKS_FILE` (default `tasks.txt`), and tests give each test its own temporary file.

`src/store.rs`:''',
    code("rust", s2_body),
    '''
A file that does not exist yet is an empty list, so the first `add` works without any setup. `next_id` is the highest id plus one. One consequence: if you remove the task with the highest id, the next `add` reuses that number. For a personal tool that is fine.

Tests need a file that no other test touches. This helper builds a name from the process id and the test name, and deletes leftovers from an earlier run:''',
    code("rust", s2_temp),
    "`src/cli.rs`:",
    code("rust", c2_body),
    '''
Points worth knowing:
- `args.split_first()` gives the command and the remaining arguments in one step.
- `add` parses its flags by hand with an index, because `--priority` and `--due` take a value. The helper `value` returns a `&str` borrowed from the arguments, which is why it carries the lifetime `'a`.
- `done` uses `iter_mut().find(...)` to get a mutable reference to the task. The title is cloned before saving, so the borrow of `tasks` has ended when `save` needs it.
- `rm` finds the position, removes the task and reports its title.

`src/main.rs` becomes the only place with side effects. Errors go to stderr, so they never mix with output that is piped into another program, and the exit code is 1:''',
    code("rust", m2),
    "The tests for `cli.rs` call `run` with a temporary file and compare the returned text: one test each for add, list, done, rm, unknown ids, missing titles and unknown commands.",
    "I ran the tests before trying anything by hand, and one failed. I removed the passing lines:",
    out(tests_trim("v2a")),
    '''
The expected text has `high` padded to six characters, the actual text does not, so in the terminal the priority column would be ragged.''',
    '''
The cause is in `Display for Priority`: `write!(f, "{}", name)` writes the text but ignores the width in `{:<6}`. Padding is only applied when the implementation uses `f.pad`. The fix is one line:''',
    code("rust", t2_display),
    "and a small test so it cannot come back:",
    code("rust", t2_width_test),
    out(result_line("v2")),
    '''
Now a real session. Build with `cargo build`. I write `tasks` for the binary (`target/debug/tasks`; `cargo run --` followed by the same arguments does the same). This ran in an empty folder with `TASKS_FILE` not set, so the data went to `tasks.txt` there:''',
    out(session(R["v2_run"][:8])),
    '''
Error messages go to stderr and the exit code is 1, which is what a script would check. The foundation is done; next come the extra features.''',
)

# ---- turn 3 -------------------------------------------------------------------------------------
user('''
Now I want to filter the list (only pending or only done), sort it by priority or by due date, and reject impossible due dates like 2026-02-30.
''')

assistant(
    '''
Dates first. A due date is valid when it has the right shape and the day exists in that month. Without a date crate that is a short function; the only subtle part is the leap-year rule. New file `src/date.rs`:''',
    code("rust", d3_body),
    '''
Two details:
- The slicing `text[0..4]` works on byte positions, and slicing in the middle of a multi-byte character panics. That is why the function first checks that the length is 10 bytes and that every byte is an ASCII digit or one of the two dashes. After that check, every byte is one character, so the slices are safe and the `unwrap()` calls cannot fail.
- February has 29 days when the year is divisible by 4, except for century years, unless the year is divisible by 400. So 2028 and 2000 are leap years, 2027 and 2100 are not.

Both are covered by tests, including one that feeds in non-ASCII digits and must not panic.''',
    "Add `mod date;` to `main.rs`. In `cli.rs`, the `--due` branch of `add` now rejects bad dates:",
    code("rust", c3_due),
    "and `list` learns two options, `--pending` / `--done` and `--sort`:",
    code("rust", c3_list),
    '''
Why it is written this way:
- `retain` keeps only the tasks for which the closure is true, so the filter is one line.
- `sort_by` is stable: tasks that compare equal keep their previous order. With `b.priority.cmp(&a.priority)` the highest priority comes first, and tasks with the same priority stay in id order without any extra code.
- A plain sort on `Option<String>` would put `None` before `Some`, the opposite of what we want. The key `(t.due.is_none(), t.due.clone())` compares `false` before `true`, so tasks with a date come first, soonest first (ISO dates sort correctly as text), and tasks without a date come last.

The usage text mentions the new options too. The tests for sorting add four tasks with different priorities and dates and compare the order of the ids that `list` prints.''',
    out(result_line("v3")),
    "A session with the new features. Note the impossible date and the unknown sort being refused:",
    out(session([r for i, r in enumerate(R["v3_run"]) if i != 8])),
    '''
In the `--sort priority` output the two high-priority tasks (#1 and #4) are in id order, and in `--sort due` the tasks without a date (#3 and #4) are at the end, also in id order. That is the stable sort at work.''',
)

# ---- turn 4 -------------------------------------------------------------------------------------
user(
    '''
I think I hit the problem you warned about, but it is worse than I expected. I added a task with a pipe in the title:

'''
    + code("", session(R["v4_before"], codes=False))
    + '''

The file contains this one line:

'''
    + code("", R["v4_before_file"].strip("\n"))
    + '''

Now nothing works, not even `add`. Can you fix it so this cannot happen again, and tell me how to get my list back?'''
)

assistant(
    '''
There are two separate problems, and the second one matters more.

1. **The format cannot hold a `|` in a title.** `1|Compare a|b|false|normal|` splits into six pieces, and the parser expects five.
2. **One bad line disables the whole tool.** The loader stops at the first bad line with `?`, and every command loads the file first, so `add` and `done` fail too. The message also does not say where the problem is.

I will fix both. First, a failing test that reproduces the report, added to `task.rs`:''',
    code("rust", t4a_test),
    "Against the current code, with the passing lines removed:",
    out(tests_trim("v4a")),
    '''
The other tests pass because none of them used a pipe; that is exactly the gap I mentioned at the start.

**The fix for the format** is escaping. A backslash starts an escape sequence, so the characters with a special meaning get a two-character form: `\\\\` for a backslash, `\\|` for a pipe, `\\n` and `\\r` for line breaks (a newline in a title would otherwise split one task into two lines). The writer escapes the title and the reader undoes it. The reader can no longer use `split('|')`, because it has to skip escaped pipes, so it walks through the characters itself. New helpers at the bottom of `task.rs`:''',
    code("rust", t4_helpers),
    "`to_line` escapes the title, and `from_line` starts with the new splitter (the rest of the function is the same, except that the match on the done flag is now `match parts[2].as_str()`, because the fields are `String`s now):",
    code("rust", t4_toline.strip("\n") + "\n\n" + t4_fromline_head.strip("\n")),
    "The new tests round-trip awkward titles (a pipe, backslashes, a title with a line break), check what the stored line looks like, and check the error cases: a bad escape, a lone backslash at the end of a line, and an old-format line with a bare pipe, which must still be reported.",
    '''
**The fix for the failure mode** is in `store.rs`, and it has two parts:
- The loader reports the file and line number of the first bad line.
- `save` writes the new content to `tasks.txt.tmp` and then renames it over `tasks.txt`. If the program is killed in the middle of the write, the old file is still complete, instead of being cut off half way.

''' + "I kept the loader strict on purpose: it does not skip bad lines. The next `save` writes only the tasks it has in memory, so skipping a bad line would silently delete it from your file the next time you add anything. An error that names the line is safer.",
    code("rust", s4_io),
    "Two more tests cover these: one checks that the error ends with `:2: bad done flag 'maybe'`, the other that no `.tmp` file is left behind after a save.",
    out(result_line("v4")),
    '''
**Getting your list back.** The old file was written by the old version, so it still has the bare pipe. This is what the fixed version says about it, using the same file:''',
    out(session(R["v4_after_old_file"][:1])),
    '''
It names the line instead of just failing. Open `tasks.txt` in any editor and put a backslash in front of the pipe in the title:''',
    code("", "1|Compare a|b|false|normal|\n1|Compare a\\|b|false|normal|"),
    "(first line: before, second line: after). Now everything works, including titles with pipes and backslashes:",
    out(session(R["v4_after_fix"][:2])),
    "and the file looks like this:",
    out(R["v4_after_file"].strip("\n")),
    '''
For a new file the same thing happens from the start. After `tasks add "Compare a|b"` and `tasks done 1` the file contains:''',
    out(R["v4_new_file"].strip("\n")),
    "and the folder contains only `tasks.txt`; no `.tmp` file is left over.",
    '''
One caveat for old files: a title that contains a backslash, written by the old version (for example `C:\\temp`), will now be reported as `bad escape` with its line number. The fix is the same by hand: double the backslash.''',
)

# ---- turn 5 -------------------------------------------------------------------------------------
user('''
Last round. I want an `edit` command that only changes the fields I give it, a `stats` command, and proper exit codes and error messages so I can use the tool from scripts.
''')

assistant(
    '''
Scripts need to tell two situations apart: the command line was wrong (the usage should be printed), and the command was fine but could not be carried out (a task does not exist, the file is damaged). The convention is exit code 2 for the first and 1 for the second. I model that with an enum instead of a plain `String`:''',
    code("rust", c5_head),
    '''
`From<String>` is the trick that keeps the code short: the store still returns `String` errors, and the `?` operator now converts them into `CliError::Failed` automatically. Usage mistakes are created explicitly with the `usage(...)` helper. The `USAGE` constant (its text is visible in the output below) is built with `concat!` so that the indentation of its lines is kept. The checks for titles, dates and priorities, `parse_id` and `find_index` are small helper functions that return these errors; `add` and `list` use them for bad options. `main.rs` is the only place that turns the enum into exit codes:''',
    code("rust", m5),
    '''
`edit` has to tell "not given" from "clear it". For the due date that is `Option<Option<String>>`: `None` means the option was not given, `Some(None)` means `--due none` (clear the date), and `Some(Some(date))` sets it. The other fields only need one `Option` level.''',
    code("rust", c5_edit),
    "`stats` is a short function that counts the done tasks and the pending tasks per priority; its output is in the session below.",
    "The tests check both kinds: a mistake in the command line must give `CliError::Usage`, and a missing task or a damaged file must give `CliError::Failed`.",
    out(result_line("v5")),
    "A session with the new commands:",
    out(session(R["v5_run"])),
    "And the error handling. A failure that is not the user's typing mistake gives exit code 1 and no usage text:",
    out(session([R["v5_errors"][0]]) + "\n" + session(R["v5_corrupt"])),
    "A mistake in the command line gives exit code 2 and the usage text:",
    out(session([R["v5_errors"][1]])),
    "(`tasks add` without a title, `tasks frobnicate` and `tasks` with no command behave the same way, with a different first line.)",
    '''
Where the project stands:
- `task.rs` and `date.rs` hold the rules, `store.rs` the file handling, `cli.rs` the commands, and `main.rs` only connects them to the process. The rules are covered by ''' + str(n5) + ''' tests.
- Each feature followed the same pattern: put the rule in a function with tests, wire it into a command, then run the real binary. When two bugs appeared (the padding and the pipe), I reproduced each with a failing test before fixing it, and kept the test.

Possible next steps: `cargo install --path .` to put the tool on your path, an `overdue` filter (it needs today's date, which the standard library only gives as a timestamp, so that is where a date crate becomes worth it), and `clap` for argument parsing if you ever allow a dependency.''',
)

# ------------------------------------------------------------------------------ write
text = ""
for role, body in turns:
    text += f"@@@ {role}\n{body}\n"
text += "@@@ END\n\n"
assert len(text) < 39800, ("too long for MAX_CHARS=40000 in mavo/data.py", len(text))
OUT.write_text(text, encoding="utf-8")
print("wrote", OUT, len(turns), "turns", len(text), "chars", "tests:", n1, n2, n3, n4, n5)

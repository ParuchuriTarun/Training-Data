"""Builds the Rust task-manager project in 5 versions under proj/tasks/, runs cargo test and the real binary,
and stores every real output in proj/tasks/results.json (consumed by gen_tasks.py)."""
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(r"C:\Projects\Mavo\Coding 1 2B\data\staging\proj\tasks")
TARGET = ROOT / "target"
BIN = ROOT / "bin"
RESULTS = {}

ENV = dict(os.environ, CARGO_TARGET_DIR=str(TARGET), CARGO_TERM_COLOR="never", PYTHONIOENCODING="utf-8")
ENV.pop("TASKS_FILE", None)


def patch(text, old, new):
    assert text.count(old) == 1, ("patch anchor not unique/found", old[:60], text.count(old))
    return text.replace(old, new)


def write(version, rel, text):
    p = ROOT / version / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.strip("\n") + "\n", encoding="utf-8", newline="\n")


def cargo(version, *args):
    p = subprocess.run(["cargo", *args], cwd=ROOT / version, env=ENV, capture_output=True, text=True, encoding="utf-8", timeout=900)
    return p


def build_and_test(version, key):
    t = cargo(version, "test", "--", "--test-threads=1")
    warnings = [l for l in t.stderr.splitlines() if l.startswith("warning") or l.startswith("error")]
    RESULTS[key + "_test"] = {"stdout": t.stdout, "code": t.returncode, "warnings": warnings}
    print(version, key, "test exit", t.returncode, "warnings:", warnings[:3])
    b = cargo(version, "build")
    assert b.returncode == 0, b.stderr
    BIN.mkdir(parents=True, exist_ok=True)
    shutil.copy(TARGET / "debug" / "tasks.exe", BIN / f"tasks_{key}.exe")
    return t


def disp(args):
    out = []
    for a in args:
        out.append('"' + a + '"' if (" " in a or "|" in a or "\\" in a or a == "") else a)
    return " ".join(out)


def scenario(key, exe_key, steps, rundir_name, fresh=True):
    rundir = ROOT / "run" / rundir_name
    if fresh and rundir.exists():
        shutil.rmtree(rundir)
    rundir.mkdir(parents=True, exist_ok=True)
    exe = BIN / f"tasks_{exe_key}.exe"
    recs = []
    for args in steps:
        p = subprocess.run([str(exe)] + args, cwd=rundir, env=ENV, capture_output=True, text=True, encoding="utf-8", timeout=60)
        recs.append({"cmd": "tasks " + disp(args), "out": p.stdout, "err": p.stderr, "code": p.returncode})
    RESULTS[key] = recs
    return rundir


CARGO_TOML = """
[package]
name = "tasks"
version = "0.1.0"
edition = "2021"

[dependencies]
"""

# ============================================================================================ task.rs
TASK_V1 = r'''
use std::fmt;
use std::str::FromStr;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Priority {
    Low,
    Normal,
    High,
}

impl fmt::Display for Priority {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        let name = match self {
            Priority::Low => "low",
            Priority::Normal => "normal",
            Priority::High => "high",
        };
        write!(f, "{}", name)
    }
}

impl FromStr for Priority {
    type Err = String;

    fn from_str(text: &str) -> Result<Priority, String> {
        match text {
            "low" => Ok(Priority::Low),
            "normal" => Ok(Priority::Normal),
            "high" => Ok(Priority::High),
            other => Err(format!("unknown priority '{}'", other)),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Task {
    pub id: u32,
    pub title: String,
    pub done: bool,
    pub priority: Priority,
    pub due: Option<String>,
}

impl Task {
    pub fn new(id: u32, title: &str) -> Task {
        Task {
            id,
            title: title.to_string(),
            done: false,
            priority: Priority::Normal,
            due: None,
        }
    }

    /// One task per line: id|title|done|priority|due
    pub fn to_line(&self) -> String {
        format!(
            "{}|{}|{}|{}|{}",
            self.id,
            self.title,
            self.done,
            self.priority,
            self.due.as_deref().unwrap_or("")
        )
    }

    pub fn from_line(line: &str) -> Result<Task, String> {
        let parts: Vec<&str> = line.split('|').collect();
        if parts.len() != 5 {
            return Err(format!("expected 5 fields, found {}", parts.len()));
        }
        let id = parts[0]
            .parse::<u32>()
            .map_err(|_| format!("bad id '{}'", parts[0]))?;
        let done = match parts[2] {
            "true" => true,
            "false" => false,
            other => return Err(format!("bad done flag '{}'", other)),
        };
        let priority = parts[3].parse::<Priority>()?;
        let due = if parts[4].is_empty() {
            None
        } else {
            Some(parts[4].to_string())
        };
        Ok(Task {
            id,
            title: parts[1].to_string(),
            done,
            priority,
            due,
        })
    }
}
'''

TASK_TESTS_V1 = r'''
#[cfg(test)]
mod tests {
    use super::*;

    fn sample() -> Task {
        Task {
            id: 7,
            title: "Write report".to_string(),
            done: false,
            priority: Priority::High,
            due: Some("2026-03-01".to_string()),
        }
    }

    #[test]
    fn to_line_has_five_fields() {
        assert_eq!(sample().to_line(), "7|Write report|false|high|2026-03-01");
    }

    #[test]
    fn a_missing_due_date_is_an_empty_last_field() {
        assert_eq!(Task::new(1, "Buy milk").to_line(), "1|Buy milk|false|normal|");
    }

    #[test]
    fn a_line_round_trips() {
        let task = sample();
        assert_eq!(Task::from_line(&task.to_line()), Ok(task));
    }

    #[test]
    fn a_line_without_due_round_trips() {
        let task = Task::new(3, "Call Sam");
        assert_eq!(Task::from_line(&task.to_line()), Ok(task));
    }

    #[test]
    fn wrong_field_count_is_an_error() {
        assert_eq!(
            Task::from_line("1|only|three"),
            Err("expected 5 fields, found 3".to_string())
        );
    }

    #[test]
    fn bad_id_is_an_error() {
        assert_eq!(Task::from_line("x|A|false|low|"), Err("bad id 'x'".to_string()));
    }

    #[test]
    fn bad_done_flag_is_an_error() {
        assert_eq!(
            Task::from_line("1|A|maybe|low|"),
            Err("bad done flag 'maybe'".to_string())
        );
    }

    #[test]
    fn unknown_priority_is_an_error() {
        assert_eq!(
            Task::from_line("1|A|false|urgent|"),
            Err("unknown priority 'urgent'".to_string())
        );
    }

    #[test]
    fn priorities_order_from_low_to_high() {
        assert!(Priority::Low < Priority::Normal);
        assert!(Priority::Normal < Priority::High);
    }

    #[test]
    fn priority_prints_as_lowercase_text() {
        assert_eq!(Priority::High.to_string(), "high");
    }
}
'''

MAIN_V1 = r'''
#[allow(dead_code)] // nothing calls this yet
mod task;

fn main() {
    println!("tasks: not much here yet");
}
'''

# ============================================================================================ store.rs
STORE_V2 = r'''
use crate::task::Task;
use std::fs;
use std::io::ErrorKind;
use std::path::Path;

/// Reads every task from the file. A file that does not exist yet is an empty list.
pub fn load(path: &Path) -> Result<Vec<Task>, String> {
    let text = match fs::read_to_string(path) {
        Ok(text) => text,
        Err(e) if e.kind() == ErrorKind::NotFound => return Ok(Vec::new()),
        Err(e) => return Err(format!("cannot read {}: {}", path.display(), e)),
    };
    let mut tasks = Vec::new();
    for line in text.lines() {
        if line.trim().is_empty() {
            continue;
        }
        tasks.push(Task::from_line(line)?);
    }
    Ok(tasks)
}

pub fn save(path: &Path, tasks: &[Task]) -> Result<(), String> {
    let mut text = String::new();
    for task in tasks {
        text.push_str(&task.to_line());
        text.push('\n');
    }
    fs::write(path, text).map_err(|e| format!("cannot write {}: {}", path.display(), e))
}

pub fn next_id(tasks: &[Task]) -> u32 {
    tasks.iter().map(|t| t.id).max().unwrap_or(0) + 1
}

#[cfg(test)]
pub fn temp_path(name: &str) -> std::path::PathBuf {
    let path = std::env::temp_dir().join(format!("tasks-test-{}-{}.txt", std::process::id(), name));
    let _ = fs::remove_file(&path);
    path
}
'''

STORE_TESTS_HEAD = r'''
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_missing_file_loads_as_empty() {
        let path = temp_path("store-missing");
        assert_eq!(load(&path), Ok(Vec::new()));
    }

    #[test]
    fn save_then_load_round_trips() {
        let path = temp_path("store-roundtrip");
        let mut second = Task::new(2, "Call Sam");
        second.done = true;
        second.due = Some("2026-04-01".to_string());
        let tasks = vec![Task::new(1, "Buy milk"), second];
        save(&path, &tasks).unwrap();
        assert_eq!(load(&path), Ok(tasks));
        fs::remove_file(&path).unwrap();
    }

    #[test]
    fn blank_lines_are_skipped() {
        let path = temp_path("store-blank");
        fs::write(&path, "1|A|false|normal|\n\n   \n2|B|false|normal|\n").unwrap();
        assert_eq!(load(&path).unwrap().len(), 2);
        fs::remove_file(&path).unwrap();
    }

    #[test]
    fn next_id_starts_at_one() {
        assert_eq!(next_id(&[]), 1);
    }

    #[test]
    fn next_id_is_the_highest_id_plus_one() {
        let tasks = vec![Task::new(3, "A"), Task::new(9, "B")];
        assert_eq!(next_id(&tasks), 10);
    }
'''

STORE_BAD_LINE_V2 = r'''
    #[test]
    fn a_bad_line_is_an_error() {
        let path = temp_path("store-bad");
        fs::write(&path, "1|A|false|normal|\nnonsense\n").unwrap();
        assert_eq!(load(&path), Err("expected 5 fields, found 1".to_string()));
        fs::remove_file(&path).unwrap();
    }
}
'''

STORE_BAD_LINE_V4 = r'''
    #[test]
    fn a_bad_line_is_an_error_that_names_the_line() {
        let path = temp_path("store-bad");
        fs::write(&path, "1|A|false|normal|\n2|B|maybe|normal|\n").unwrap();
        let err = load(&path).unwrap_err();
        assert!(err.ends_with(":2: bad done flag 'maybe'"), "got: {}", err);
        fs::remove_file(&path).unwrap();
    }

    #[test]
    fn save_leaves_no_temporary_file_behind() {
        let path = temp_path("store-atomic");
        save(&path, &[Task::new(1, "A")]).unwrap();
        let mut tmp = path.as_os_str().to_owned();
        tmp.push(".tmp");
        assert!(!std::path::Path::new(&tmp).exists());
        assert!(path.exists());
        fs::remove_file(&path).unwrap();
    }
}
'''

# ============================================================================================ cli.rs (v2)
CLI_V2 = r'''
use crate::store;
use crate::task::{Priority, Task};
use std::path::Path;

pub fn run(args: &[String], path: &Path) -> Result<String, String> {
    let (command, rest) = match args.split_first() {
        Some((command, rest)) => (command.as_str(), rest),
        None => return Err(usage()),
    };
    match command {
        "add" => add(rest, path),
        "list" => list(path),
        "done" => done(rest, path),
        "rm" => remove(rest, path),
        other => Err(format!("unknown command '{}'\n{}", other, usage())),
    }
}

fn usage() -> String {
    [
        "usage: tasks add TITLE [--priority low|normal|high] [--due YYYY-MM-DD]",
        "       tasks list",
        "       tasks done ID",
        "       tasks rm ID",
    ]
    .join("\n")
}

fn value<'a>(args: &'a [String], i: usize, flag: &str) -> Result<&'a str, String> {
    args.get(i)
        .map(|s| s.as_str())
        .ok_or_else(|| format!("{} needs a value", flag))
}

fn add(args: &[String], path: &Path) -> Result<String, String> {
    let mut title: Option<String> = None;
    let mut priority = Priority::Normal;
    let mut due: Option<String> = None;
    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--priority" => {
                i += 1;
                priority = value(args, i, "--priority")?.parse::<Priority>()?;
            }
            "--due" => {
                i += 1;
                due = Some(value(args, i, "--due")?.to_string());
            }
            option if option.starts_with("--") => {
                return Err(format!("unknown option '{}'", option));
            }
            text => {
                if title.is_some() {
                    return Err("only one title allowed (put it in quotes)".to_string());
                }
                title = Some(text.to_string());
            }
        }
        i += 1;
    }
    let title = title.ok_or("add needs a title")?;
    if title.trim().is_empty() {
        return Err("title cannot be empty".to_string());
    }
    let mut tasks = store::load(path)?;
    let id = store::next_id(&tasks);
    let mut task = Task::new(id, &title);
    task.priority = priority;
    task.due = due;
    tasks.push(task);
    store::save(path, &tasks)?;
    Ok(format!("added #{}: {}\n", id, title))
}

fn list(path: &Path) -> Result<String, String> {
    let tasks = store::load(path)?;
    if tasks.is_empty() {
        return Ok("no tasks\n".to_string());
    }
    let mut out = String::new();
    for task in &tasks {
        out.push_str(&format_task(task));
        out.push('\n');
    }
    Ok(out)
}

fn format_task(task: &Task) -> String {
    let mark = if task.done { "x" } else { " " };
    let due = match &task.due {
        Some(date) => format!("  due {}", date),
        None => String::new(),
    };
    format!("{:>3} [{}] {:<6} {}{}", task.id, mark, task.priority, task.title, due)
}

fn parse_id(args: &[String], command: &str) -> Result<u32, String> {
    let raw = args
        .first()
        .ok_or_else(|| format!("{} needs a task id", command))?;
    raw.parse::<u32>()
        .map_err(|_| format!("'{}' is not a task id", raw))
}

fn done(args: &[String], path: &Path) -> Result<String, String> {
    let id = parse_id(args, "done")?;
    let mut tasks = store::load(path)?;
    let task = tasks
        .iter_mut()
        .find(|t| t.id == id)
        .ok_or_else(|| format!("no task #{}", id))?;
    task.done = true;
    let title = task.title.clone();
    store::save(path, &tasks)?;
    Ok(format!("done #{}: {}\n", id, title))
}

fn remove(args: &[String], path: &Path) -> Result<String, String> {
    let id = parse_id(args, "rm")?;
    let mut tasks = store::load(path)?;
    let position = tasks
        .iter()
        .position(|t| t.id == id)
        .ok_or_else(|| format!("no task #{}", id))?;
    let removed = tasks.remove(position);
    store::save(path, &tasks)?;
    Ok(format!("removed #{}: {}\n", id, removed.title))
}
'''

CLI_TESTS_HEAD = r'''
#[cfg(test)]
mod tests {
    use super::*;
    use crate::store::temp_path;

    fn args(parts: &[&str]) -> Vec<String> {
        parts.iter().map(|s| s.to_string()).collect()
    }

    fn run_ok(parts: &[&str], path: &Path) -> String {
        run(&args(parts), path).unwrap()
    }
'''

CLI_TESTS_V2 = [
    r'''
    #[test]
    fn add_assigns_increasing_ids() {
        let path = temp_path("cli-add");
        assert_eq!(run_ok(&["add", "Buy milk"], &path), "added #1: Buy milk\n");
        assert_eq!(run_ok(&["add", "Call Sam"], &path), "added #2: Call Sam\n");
        let _ = std::fs::remove_file(&path);
    }
''',
    r'''
    #[test]
    fn list_shows_priority_and_due_date() {
        let path = temp_path("cli-list");
        run_ok(&["add", "Write report", "--priority", "high", "--due", "2026-03-01"], &path);
        run_ok(&["add", "Buy milk"], &path);
        assert_eq!(
            run_ok(&["list"], &path),
            "  1 [ ] high   Write report  due 2026-03-01\n  2 [ ] normal Buy milk\n"
        );
        let _ = std::fs::remove_file(&path);
    }
''',
    r'''
    #[test]
    fn list_on_a_new_file_says_so() {
        let path = temp_path("cli-empty");
        assert_eq!(run_ok(&["list"], &path), "no tasks\n");
    }
''',
    r'''
    #[test]
    fn done_marks_a_task() {
        let path = temp_path("cli-done");
        run_ok(&["add", "Buy milk"], &path);
        assert_eq!(run_ok(&["done", "1"], &path), "done #1: Buy milk\n");
        assert_eq!(run_ok(&["list"], &path), "  1 [x] normal Buy milk\n");
        let _ = std::fs::remove_file(&path);
    }
''',
    r'''
    #[test]
    fn rm_removes_a_task() {
        let path = temp_path("cli-rm");
        run_ok(&["add", "Buy milk"], &path);
        run_ok(&["add", "Call Sam"], &path);
        assert_eq!(run_ok(&["rm", "1"], &path), "removed #1: Buy milk\n");
        assert_eq!(run_ok(&["list"], &path), "  2 [ ] normal Call Sam\n");
        let _ = std::fs::remove_file(&path);
    }
''',
    r'''
    #[test]
    fn an_unknown_id_is_an_error() {
        let path = temp_path("cli-unknown-id");
        assert_eq!(run(&args(&["done", "9"]), &path), Err("no task #9".to_string()));
        assert_eq!(run(&args(&["rm", "x"]), &path), Err("'x' is not a task id".to_string()));
    }
''',
    r'''
    #[test]
    fn add_needs_a_title_and_a_known_priority() {
        let path = temp_path("cli-add-errors");
        assert_eq!(run(&args(&["add"]), &path), Err("add needs a title".to_string()));
        assert_eq!(
            run(&args(&["add", "X", "--priority", "urgent"]), &path),
            Err("unknown priority 'urgent'".to_string())
        );
        assert_eq!(
            run(&args(&["add", "X", "--priority"]), &path),
            Err("--priority needs a value".to_string())
        );
        assert_eq!(run(&args(&["add", "   "]), &path), Err("title cannot be empty".to_string()));
    }
''',
    r'''
    #[test]
    fn an_unknown_command_shows_the_usage() {
        let path = temp_path("cli-unknown-command");
        let err = run(&args(&["frobnicate"]), &path).unwrap_err();
        assert!(err.starts_with("unknown command 'frobnicate'"));
        assert!(err.contains("usage: tasks add"));
    }
''',
]

# ---- v3 pieces
DATE_V3 = r'''
/// True when `text` is a real calendar date written as YYYY-MM-DD.
pub fn is_valid_date(text: &str) -> bool {
    let bytes = text.as_bytes();
    if bytes.len() != 10 || bytes[4] != b'-' || bytes[7] != b'-' {
        return false;
    }
    let digits_only = bytes
        .iter()
        .enumerate()
        .all(|(i, b)| i == 4 || i == 7 || b.is_ascii_digit());
    if !digits_only {
        return false;
    }
    // Every byte is ASCII now, so slicing by byte position cannot split a character.
    let year: u32 = text[0..4].parse().unwrap();
    let month: u32 = text[5..7].parse().unwrap();
    let day: u32 = text[8..10].parse().unwrap();
    (1..=12).contains(&month) && day >= 1 && day <= days_in_month(year, month)
}

fn is_leap(year: u32) -> bool {
    (year % 4 == 0 && year % 100 != 0) || year % 400 == 0
}

fn days_in_month(year: u32, month: u32) -> u32 {
    match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        _ => {
            if is_leap(year) {
                29
            } else {
                28
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn real_dates_are_valid() {
        assert!(is_valid_date("2026-03-01"));
        assert!(is_valid_date("2026-12-31"));
        assert!(is_valid_date("2026-04-30"));
    }

    #[test]
    fn the_wrong_shape_is_invalid() {
        for text in ["", "2026-3-01", "2026/03/01", "20260301", "2026-03-1x", "2026-03-011"] {
            assert!(!is_valid_date(text), "{:?} should be invalid", text);
        }
    }

    #[test]
    fn non_ascii_digits_do_not_panic() {
        assert!(!is_valid_date("２０２６-03-01"));
        assert!(!is_valid_date("2026-0é-01"));
    }

    #[test]
    fn months_and_days_must_exist() {
        assert!(!is_valid_date("2026-00-10"));
        assert!(!is_valid_date("2026-13-10"));
        assert!(!is_valid_date("2026-04-31"));
        assert!(!is_valid_date("2026-05-00"));
        assert!(!is_valid_date("2026-01-32"));
    }

    #[test]
    fn february_follows_the_leap_year_rules() {
        assert!(is_valid_date("2028-02-29"));
        assert!(!is_valid_date("2027-02-29"));
        assert!(!is_valid_date("2100-02-29"));
        assert!(is_valid_date("2000-02-29"));
        assert!(is_valid_date("2027-02-28"));
    }
}
'''

CLI_DUE_V2 = r'''
            "--due" => {
                i += 1;
                due = Some(value(args, i, "--due")?.to_string());
            }
'''
CLI_DUE_V3 = r'''
            "--due" => {
                i += 1;
                let text = value(args, i, "--due")?;
                if !date::is_valid_date(text) {
                    return Err(format!("'{}' is not a real date (use YYYY-MM-DD)", text));
                }
                due = Some(text.to_string());
            }
'''

LIST_V2 = r'''
fn list(path: &Path) -> Result<String, String> {
    let tasks = store::load(path)?;
    if tasks.is_empty() {
'''
LIST_V3 = r'''
fn list(args: &[String], path: &Path) -> Result<String, String> {
    let mut only_done: Option<bool> = None;
    let mut sort = "id";
    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--pending" => only_done = Some(false),
            "--done" => only_done = Some(true),
            "--sort" => {
                i += 1;
                sort = value(args, i, "--sort")?;
                if !["id", "priority", "due"].contains(&sort) {
                    return Err(format!("unknown sort '{}' (use id, priority or due)", sort));
                }
            }
            other => return Err(format!("unknown option '{}'", other)),
        }
        i += 1;
    }
    let mut tasks = store::load(path)?;
    if let Some(wanted) = only_done {
        tasks.retain(|t| t.done == wanted);
    }
    match sort {
        // sort_by is stable, so equal priorities keep their id order
        "priority" => tasks.sort_by(|a, b| b.priority.cmp(&a.priority)),
        // false sorts before true, so tasks with a date come first, soonest first
        "due" => tasks.sort_by_key(|t| (t.due.is_none(), t.due.clone())),
        _ => {}
    }
    if tasks.is_empty() {
'''

CLI_TESTS_V3_NEW = [
    r'''
    fn ids(out: &str) -> Vec<&str> {
        out.lines().map(|line| line[..3].trim()).collect()
    }

    fn add_four(path: &Path) {
        run_ok(&["add", "Low job", "--priority", "low"], path);
        run_ok(&["add", "Big job", "--priority", "high", "--due", "2026-05-01"], path);
        run_ok(&["add", "Normal job", "--due", "2026-04-15"], path);
        run_ok(&["add", "Other high", "--priority", "high"], path);
    }
''',
    r'''
    #[test]
    fn an_impossible_due_date_is_rejected() {
        let path = temp_path("cli-bad-date");
        assert_eq!(
            run(&args(&["add", "X", "--due", "2026-02-30"]), &path),
            Err("'2026-02-30' is not a real date (use YYYY-MM-DD)".to_string())
        );
        assert_eq!(run_ok(&["list"], &path), "no tasks\n");
    }
''',
    r'''
    #[test]
    fn list_can_show_only_pending_or_only_done() {
        let path = temp_path("cli-filter");
        add_four(&path);
        run_ok(&["done", "2"], &path);
        assert_eq!(ids(&run_ok(&["list", "--pending"], &path)), ["1", "3", "4"]);
        assert_eq!(ids(&run_ok(&["list", "--done"], &path)), ["2"]);
        let _ = std::fs::remove_file(&path);
    }
''',
    r'''
    #[test]
    fn list_sorts_by_priority_highest_first() {
        let path = temp_path("cli-sort-priority");
        add_four(&path);
        assert_eq!(ids(&run_ok(&["list", "--sort", "priority"], &path)), ["2", "4", "3", "1"]);
        let _ = std::fs::remove_file(&path);
    }
''',
    r'''
    #[test]
    fn list_sorts_by_due_date_with_undated_tasks_last() {
        let path = temp_path("cli-sort-due");
        add_four(&path);
        assert_eq!(ids(&run_ok(&["list", "--sort", "due"], &path)), ["3", "2", "1", "4"]);
        let _ = std::fs::remove_file(&path);
    }
''',
    r'''
    #[test]
    fn list_rejects_unknown_options() {
        let path = temp_path("cli-list-options");
        assert_eq!(
            run(&args(&["list", "--sort", "colour"]), &path),
            Err("unknown sort 'colour' (use id, priority or due)".to_string())
        );
        assert_eq!(run(&args(&["list", "--oldest"]), &path), Err("unknown option '--oldest'".to_string()));
    }
''',
]

# ---- v4 pieces
TASK_V4_TOLINE_OLD = r'''
            self.id,
            self.title,
            self.done,
'''
TASK_V4_TOLINE_NEW = r'''
            self.id,
            escape(&self.title),
            self.done,
'''
TASK_V4_SPLIT_OLD = r'''
        let parts: Vec<&str> = line.split('|').collect();
'''
TASK_V4_SPLIT_NEW = r'''
        let parts = split_fields(line)?;
'''
TASK_V4_HELPERS = r'''

/// Makes a field safe to put between `|` separators.
fn escape(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    for c in text.chars() {
        match c {
            '\\' => out.push_str("\\\\"),
            '|' => out.push_str("\\|"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            _ => out.push(c),
        }
    }
    out
}

/// Splits a line at every `|` that is not escaped, and undoes the escaping.
fn split_fields(line: &str) -> Result<Vec<String>, String> {
    let mut fields = Vec::new();
    let mut current = String::new();
    let mut chars = line.chars();
    while let Some(c) = chars.next() {
        match c {
            '|' => fields.push(std::mem::take(&mut current)),
            '\\' => match chars.next() {
                Some('\\') => current.push('\\'),
                Some('|') => current.push('|'),
                Some('n') => current.push('\n'),
                Some('r') => current.push('\r'),
                Some(other) => return Err(format!("bad escape '\\{}'", other)),
                None => return Err("line ends with a lone backslash".to_string()),
            },
            _ => current.push(c),
        }
    }
    fields.push(current);
    Ok(fields)
}
'''

TASK_TESTS_V4_NEW = r'''
    #[test]
    fn a_title_with_a_pipe_round_trips() {
        let task = Task::new(1, "Compare a|b");
        assert_eq!(Task::from_line(&task.to_line()), Ok(task));
    }

    #[test]
    fn backslashes_and_line_breaks_round_trip() {
        for title in ["C:\\temp\\notes", "ends with a backslash\\", "two\nlines", "\\|\\\\|", "a||b"] {
            let task = Task::new(2, title);
            let line = task.to_line();
            assert!(!line.contains('\n'), "line must stay one line: {:?}", line);
            assert_eq!(Task::from_line(&line), Ok(task), "title {:?}", title);
        }
    }

    #[test]
    fn the_pipe_is_escaped_in_the_stored_line() {
        assert_eq!(Task::new(1, "a|b").to_line(), "1|a\\|b|false|normal|");
    }

    #[test]
    fn bad_escapes_are_errors() {
        assert_eq!(
            Task::from_line("1|A\\q|false|low|"),
            Err("bad escape '\\q'".to_string())
        );
        assert_eq!(
            Task::from_line("1|A|false|low|\\"),
            Err("line ends with a lone backslash".to_string())
        );
    }

    #[test]
    fn a_line_from_the_old_format_with_a_bare_pipe_is_still_an_error() {
        assert_eq!(
            Task::from_line("1|Compare a|b|false|normal|"),
            Err("expected 5 fields, found 6".to_string())
        );
    }
'''

STORE_SAVE_V2 = r'''
    fs::write(path, text).map_err(|e| format!("cannot write {}: {}", path.display(), e))
'''
STORE_SAVE_V4 = r'''
    // Write the whole new file next to the real one, then swap it in. If the program dies
    // half way through the write, the old file is still intact.
    let mut tmp = path.as_os_str().to_owned();
    tmp.push(".tmp");
    let tmp = PathBuf::from(tmp);
    fs::write(&tmp, text).map_err(|e| format!("cannot write {}: {}", tmp.display(), e))?;
    fs::rename(&tmp, path).map_err(|e| format!("cannot replace {}: {}", path.display(), e))
'''
STORE_LOOP_V2 = r'''
    for line in text.lines() {
        if line.trim().is_empty() {
            continue;
        }
        tasks.push(Task::from_line(line)?);
    }
'''
STORE_LOOP_V4 = r'''
    for (n, line) in text.lines().enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        let task = Task::from_line(line)
            .map_err(|e| format!("{}:{}: {}", path.display(), n + 1, e))?;
        tasks.push(task);
    }
'''

CLI_TEST_V4_NEW = r'''
    #[test]
    fn a_title_with_a_pipe_survives_add_and_list() {
        let path = temp_path("cli-pipe");
        run_ok(&["add", "Compare a|b"], &path);
        run_ok(&["add", "Second"], &path);
        assert_eq!(
            run_ok(&["list"], &path),
            "  1 [ ] normal Compare a|b\n  2 [ ] normal Second\n"
        );
        let _ = std::fs::remove_file(&path);
    }
'''

# ============================================================================================ v5 cli
CLI_V5 = r'''
use crate::date;
use crate::store;
use crate::task::{Priority, Task};
use std::path::Path;

pub const USAGE: &str = concat!(
    "usage: tasks add TITLE [--priority low|normal|high] [--due YYYY-MM-DD]\n",
    "       tasks list [--pending|--done] [--sort id|priority|due]\n",
    "       tasks done ID\n",
    "       tasks rm ID\n",
    "       tasks edit ID [--title TEXT] [--priority low|normal|high] [--due YYYY-MM-DD|none]\n",
    "       tasks stats\n",
    "\n",
    "The tasks are stored in the file named by TASKS_FILE (default: tasks.txt)."
);

#[derive(Debug, PartialEq)]
pub enum CliError {
    /// The command line was wrong: the usage is shown and the exit code is 2.
    Usage(String),
    /// The command was fine but could not be carried out: exit code 1.
    Failed(String),
}

// Errors from the store are plain strings; they are failures, not usage mistakes.
impl From<String> for CliError {
    fn from(message: String) -> CliError {
        CliError::Failed(message)
    }
}

fn usage<T>(message: impl Into<String>) -> Result<T, CliError> {
    Err(CliError::Usage(message.into()))
}

pub fn run(args: &[String], path: &Path) -> Result<String, CliError> {
    let (command, rest) = match args.split_first() {
        Some((command, rest)) => (command.as_str(), rest),
        None => return usage("missing command"),
    };
    match command {
        "add" => add(rest, path),
        "list" => list(rest, path),
        "done" => done(rest, path),
        "rm" => remove(rest, path),
        "edit" => edit(rest, path),
        "stats" => stats(rest, path),
        "help" | "--help" | "-h" => Ok(format!("{}\n", USAGE)),
        other => usage(format!("unknown command '{}'", other)),
    }
}

fn value<'a>(args: &'a [String], i: usize, flag: &str) -> Result<&'a str, CliError> {
    match args.get(i) {
        Some(text) => Ok(text.as_str()),
        None => usage(format!("{} needs a value", flag)),
    }
}

fn check_title(title: &str) -> Result<String, CliError> {
    if title.trim().is_empty() {
        return usage("title cannot be empty");
    }
    Ok(title.to_string())
}

fn check_date(text: &str) -> Result<String, CliError> {
    if date::is_valid_date(text) {
        Ok(text.to_string())
    } else {
        usage(format!("'{}' is not a real date (use YYYY-MM-DD)", text))
    }
}

fn check_priority(text: &str) -> Result<Priority, CliError> {
    text.parse::<Priority>().map_err(CliError::Usage)
}

fn parse_id(args: &[String], command: &str) -> Result<u32, CliError> {
    let raw = match args.first() {
        Some(raw) => raw,
        None => return usage(format!("{} needs a task id", command)),
    };
    match raw.parse::<u32>() {
        Ok(id) => Ok(id),
        Err(_) => usage(format!("'{}' is not a task id", raw)),
    }
}

fn find_index(tasks: &[Task], id: u32) -> Result<usize, CliError> {
    match tasks.iter().position(|t| t.id == id) {
        Some(i) => Ok(i),
        None => Err(CliError::Failed(format!("no task #{}", id))),
    }
}

fn add(args: &[String], path: &Path) -> Result<String, CliError> {
    let mut title: Option<String> = None;
    let mut priority = Priority::Normal;
    let mut due: Option<String> = None;
    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--priority" => {
                i += 1;
                priority = check_priority(value(args, i, "--priority")?)?;
            }
            "--due" => {
                i += 1;
                due = Some(check_date(value(args, i, "--due")?)?);
            }
            option if option.starts_with("--") => {
                return usage(format!("unknown option '{}'", option));
            }
            text => {
                if title.is_some() {
                    return usage("only one title allowed (put it in quotes)");
                }
                title = Some(check_title(text)?);
            }
        }
        i += 1;
    }
    let title = match title {
        Some(title) => title,
        None => return usage("add needs a title"),
    };
    let mut tasks = store::load(path)?;
    let id = store::next_id(&tasks);
    let mut task = Task::new(id, &title);
    task.priority = priority;
    task.due = due;
    tasks.push(task);
    store::save(path, &tasks)?;
    Ok(format!("added #{}: {}\n", id, title))
}

fn list(args: &[String], path: &Path) -> Result<String, CliError> {
    let mut only_done: Option<bool> = None;
    let mut sort = "id";
    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--pending" => only_done = Some(false),
            "--done" => only_done = Some(true),
            "--sort" => {
                i += 1;
                sort = value(args, i, "--sort")?;
                if !["id", "priority", "due"].contains(&sort) {
                    return usage(format!("unknown sort '{}' (use id, priority or due)", sort));
                }
            }
            other => return usage(format!("unknown option '{}'", other)),
        }
        i += 1;
    }
    let mut tasks = store::load(path)?;
    if let Some(wanted) = only_done {
        tasks.retain(|t| t.done == wanted);
    }
    match sort {
        "priority" => tasks.sort_by(|a, b| b.priority.cmp(&a.priority)),
        "due" => tasks.sort_by_key(|t| (t.due.is_none(), t.due.clone())),
        _ => {}
    }
    if tasks.is_empty() {
        return Ok("no tasks\n".to_string());
    }
    let mut out = String::new();
    for task in &tasks {
        out.push_str(&format_task(task));
        out.push('\n');
    }
    Ok(out)
}

fn format_task(task: &Task) -> String {
    let mark = if task.done { "x" } else { " " };
    let due = match &task.due {
        Some(date) => format!("  due {}", date),
        None => String::new(),
    };
    format!("{:>3} [{}] {:<6} {}{}", task.id, mark, task.priority, task.title, due)
}

fn done(args: &[String], path: &Path) -> Result<String, CliError> {
    let id = parse_id(args, "done")?;
    let mut tasks = store::load(path)?;
    let i = find_index(&tasks, id)?;
    tasks[i].done = true;
    let message = format!("done #{}: {}\n", id, tasks[i].title);
    store::save(path, &tasks)?;
    Ok(message)
}

fn remove(args: &[String], path: &Path) -> Result<String, CliError> {
    let id = parse_id(args, "rm")?;
    let mut tasks = store::load(path)?;
    let i = find_index(&tasks, id)?;
    let removed = tasks.remove(i);
    store::save(path, &tasks)?;
    Ok(format!("removed #{}: {}\n", id, removed.title))
}

fn edit(args: &[String], path: &Path) -> Result<String, CliError> {
    let id = parse_id(args, "edit")?;
    let mut title: Option<String> = None;
    let mut priority: Option<Priority> = None;
    // None = leave the date alone, Some(None) = clear it, Some(Some(d)) = set it
    let mut due: Option<Option<String>> = None;
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--title" => {
                i += 1;
                title = Some(check_title(value(args, i, "--title")?)?);
            }
            "--priority" => {
                i += 1;
                priority = Some(check_priority(value(args, i, "--priority")?)?);
            }
            "--due" => {
                i += 1;
                let text = value(args, i, "--due")?;
                due = Some(if text == "none" { None } else { Some(check_date(text)?) });
            }
            other => return usage(format!("unknown option '{}'", other)),
        }
        i += 1;
    }
    if title.is_none() && priority.is_none() && due.is_none() {
        return usage("edit needs at least one of --title, --priority, --due");
    }
    let mut tasks = store::load(path)?;
    let index = find_index(&tasks, id)?;
    let task = &mut tasks[index];
    if let Some(title) = title {
        task.title = title;
    }
    if let Some(priority) = priority {
        task.priority = priority;
    }
    if let Some(due) = due {
        task.due = due;
    }
    let message = format!("updated #{}: {}\n", id, task.title);
    store::save(path, &tasks)?;
    Ok(message)
}

fn stats(args: &[String], path: &Path) -> Result<String, CliError> {
    if !args.is_empty() {
        return usage("stats takes no arguments");
    }
    let tasks = store::load(path)?;
    let done = tasks.iter().filter(|t| t.done).count();
    let pending: Vec<&Task> = tasks.iter().filter(|t| !t.done).collect();
    let count = |p: Priority| pending.iter().filter(|t| t.priority == p).count();
    Ok(format!(
        "total:   {}\ndone:    {}\npending: {}\n  high:   {}\n  normal: {}\n  low:    {}\n",
        tasks.len(),
        done,
        pending.len(),
        count(Priority::High),
        count(Priority::Normal),
        count(Priority::Low)
    ))
}
'''

CLI_TESTS_V5 = [
    r'''
    fn failed(message: &str) -> CliError {
        CliError::Failed(message.to_string())
    }

    fn usage_error(message: &str) -> CliError {
        CliError::Usage(message.to_string())
    }

    fn ids(out: &str) -> Vec<&str> {
        out.lines().map(|line| line[..3].trim()).collect()
    }

    fn add_four(path: &Path) {
        run_ok(&["add", "Low job", "--priority", "low"], path);
        run_ok(&["add", "Big job", "--priority", "high", "--due", "2026-05-01"], path);
        run_ok(&["add", "Normal job", "--due", "2026-04-15"], path);
        run_ok(&["add", "Other high", "--priority", "high"], path);
    }
''',
    r'''
    #[test]
    fn add_assigns_increasing_ids() {
        let path = temp_path("cli-add");
        assert_eq!(run_ok(&["add", "Buy milk"], &path), "added #1: Buy milk\n");
        assert_eq!(run_ok(&["add", "Call Sam"], &path), "added #2: Call Sam\n");
        let _ = std::fs::remove_file(&path);
    }
''',
    r'''
    #[test]
    fn list_shows_priority_and_due_date() {
        let path = temp_path("cli-list");
        run_ok(&["add", "Write report", "--priority", "high", "--due", "2026-03-01"], &path);
        run_ok(&["add", "Buy milk"], &path);
        assert_eq!(
            run_ok(&["list"], &path),
            "  1 [ ] high   Write report  due 2026-03-01\n  2 [ ] normal Buy milk\n"
        );
        let _ = std::fs::remove_file(&path);
    }
''',
    r'''
    #[test]
    fn done_and_rm_change_the_list() {
        let path = temp_path("cli-done-rm");
        run_ok(&["add", "Buy milk"], &path);
        run_ok(&["add", "Call Sam"], &path);
        assert_eq!(run_ok(&["done", "1"], &path), "done #1: Buy milk\n");
        assert_eq!(run_ok(&["rm", "2"], &path), "removed #2: Call Sam\n");
        assert_eq!(run_ok(&["list"], &path), "  1 [x] normal Buy milk\n");
        let _ = std::fs::remove_file(&path);
    }
''',
    r'''
    #[test]
    fn list_filters_and_sorts() {
        let path = temp_path("cli-list-options");
        add_four(&path);
        run_ok(&["done", "2"], &path);
        assert_eq!(ids(&run_ok(&["list", "--pending"], &path)), ["1", "3", "4"]);
        assert_eq!(ids(&run_ok(&["list", "--sort", "priority"], &path)), ["2", "4", "3", "1"]);
        assert_eq!(ids(&run_ok(&["list", "--sort", "due"], &path)), ["3", "2", "1", "4"]);
        let _ = std::fs::remove_file(&path);
    }
''',
    r'''
    #[test]
    fn a_title_with_a_pipe_survives_add_and_list() {
        let path = temp_path("cli-pipe");
        run_ok(&["add", "Compare a|b"], &path);
        assert_eq!(run_ok(&["list"], &path), "  1 [ ] normal Compare a|b\n");
        let _ = std::fs::remove_file(&path);
    }
''',
    r'''
    #[test]
    fn edit_changes_only_the_fields_that_are_given() {
        let path = temp_path("cli-edit");
        run_ok(&["add", "Buy milk", "--due", "2026-03-01"], &path);
        run_ok(&["edit", "1", "--priority", "high"], &path);
        assert_eq!(run_ok(&["list"], &path), "  1 [ ] high   Buy milk  due 2026-03-01\n");
        run_ok(&["edit", "1", "--title", "Buy oat milk", "--due", "none"], &path);
        assert_eq!(run_ok(&["list"], &path), "  1 [ ] high   Buy oat milk\n");
        let _ = std::fs::remove_file(&path);
    }
''',
    r'''
    #[test]
    fn edit_reports_what_is_wrong() {
        let path = temp_path("cli-edit-errors");
        run_ok(&["add", "Buy milk"], &path);
        assert_eq!(run(&args(&["edit", "9", "--title", "X"]), &path), Err(failed("no task #9")));
        assert_eq!(
            run(&args(&["edit", "1"]), &path),
            Err(usage_error("edit needs at least one of --title, --priority, --due"))
        );
        assert_eq!(
            run(&args(&["edit", "1", "--due", "2026-02-30"]), &path),
            Err(usage_error("'2026-02-30' is not a real date (use YYYY-MM-DD)"))
        );
        let _ = std::fs::remove_file(&path);
    }
''',
    r'''
    #[test]
    fn stats_counts_pending_tasks_by_priority() {
        let path = temp_path("cli-stats");
        add_four(&path);
        run_ok(&["done", "2"], &path);
        assert_eq!(
            run_ok(&["stats"], &path),
            "total:   4\ndone:    1\npending: 3\n  high:   1\n  normal: 1\n  low:    1\n"
        );
        let _ = std::fs::remove_file(&path);
    }
''',
    r'''
    #[test]
    fn mistakes_in_the_command_line_are_usage_errors() {
        let path = temp_path("cli-usage");
        assert_eq!(run(&args(&[]), &path), Err(usage_error("missing command")));
        assert_eq!(run(&args(&["frobnicate"]), &path), Err(usage_error("unknown command 'frobnicate'")));
        assert_eq!(run(&args(&["add"]), &path), Err(usage_error("add needs a title")));
        assert_eq!(run(&args(&["done", "x"]), &path), Err(usage_error("'x' is not a task id")));
        assert_eq!(run(&args(&["stats", "now"]), &path), Err(usage_error("stats takes no arguments")));
    }
''',
    r'''
    #[test]
    fn problems_with_the_data_are_failures() {
        let path = temp_path("cli-failures");
        assert_eq!(run(&args(&["done", "3"]), &path), Err(failed("no task #3")));
        std::fs::write(&path, "1|A|maybe|low|\n").unwrap();
        let err = run(&args(&["list"]), &path).unwrap_err();
        assert!(matches!(err, CliError::Failed(_)));
        let _ = std::fs::remove_file(&path);
    }
''',
    r'''
    #[test]
    fn help_prints_the_usage() {
        let path = temp_path("cli-help");
        let out = run_ok(&["help"], &path);
        assert!(out.starts_with("usage: tasks add"));
        assert!(out.contains("tasks stats"));
    }
''',
]

MAIN_V2 = r'''
mod cli;
mod store;
mod task;

use std::env;
use std::path::PathBuf;
use std::process;

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    let path = env::var("TASKS_FILE")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("tasks.txt"));
    match cli::run(&args, &path) {
        Ok(output) => print!("{}", output),
        Err(message) => {
            eprintln!("error: {}", message);
            process::exit(1);
        }
    }
}
'''

MAIN_V5 = r'''
mod cli;
mod date;
mod store;
mod task;

use cli::CliError;
use std::env;
use std::path::PathBuf;
use std::process;

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    let path = env::var("TASKS_FILE")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("tasks.txt"));
    match cli::run(&args, &path) {
        Ok(output) => print!("{}", output),
        Err(CliError::Usage(message)) => {
            eprintln!("error: {}\n\n{}", message, cli::USAGE);
            process::exit(2);
        }
        Err(CliError::Failed(message)) => {
            eprintln!("error: {}", message);
            process::exit(1);
        }
    }
}
'''


def main():
    if ROOT.exists():
        for child in ROOT.iterdir():
            if child.name != "target":
                shutil.rmtree(child) if child.is_dir() else child.unlink()
    ROOT.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ v1
    write("v1", "Cargo.toml", CARGO_TOML)
    write("v1", "src/main.rs", MAIN_V1)
    write("v1", "src/task.rs", TASK_V1 + "\n" + TASK_TESTS_V1)
    build_and_test("v1", "v1")

    # ------------------------------------------------------------------ v2 (first with the write! Display bug)
    store_v2 = STORE_V2 + "\n" + STORE_TESTS_HEAD + STORE_BAD_LINE_V2
    cli_v2 = CLI_V2 + "\n" + CLI_TESTS_HEAD + "".join(CLI_TESTS_V2) + "}\n"
    for ver, task_text in (("v2a", TASK_V1 + "\n" + TASK_TESTS_V1),):
        write(ver, "Cargo.toml", CARGO_TOML)
        write(ver, "src/main.rs", MAIN_V2)
        write(ver, "src/task.rs", task_text)
        write(ver, "src/store.rs", store_v2)
        write(ver, "src/cli.rs", cli_v2)
    t = build_and_test("v2a", "v2a")
    scenario("v2a_list", "v2a", [
        ["add", "Buy milk"],
        ["add", "Write report", "--priority", "high", "--due", "2026-03-01"],
        ["add", "Call Sam", "--priority", "low"],
        ["list"],
    ], "v2a")
    # fix: f.pad respects width/alignment
    task_v2 = patch(TASK_V1, '        write!(f, "{}", name)\n', "        f.pad(name)\n")
    task_tests_v2 = patch(
        TASK_TESTS_V1,
        "    #[test]\n    fn priority_prints_as_lowercase_text() {\n        assert_eq!(Priority::High.to_string(), \"high\");\n    }\n",
        "    #[test]\n    fn priority_prints_as_lowercase_text() {\n        assert_eq!(Priority::High.to_string(), \"high\");\n    }\n\n"
        "    #[test]\n    fn priority_respects_a_width() {\n        assert_eq!(format!(\"[{:<6}]\", Priority::High), \"[high  ]\");\n    }\n",
    )
    write("v2", "Cargo.toml", CARGO_TOML)
    write("v2", "src/main.rs", MAIN_V2)
    write("v2", "src/task.rs", task_v2 + "\n" + task_tests_v2)
    write("v2", "src/store.rs", store_v2)
    write("v2", "src/cli.rs", cli_v2)
    build_and_test("v2", "v2")
    scenario("v2_run", "v2", [
        ["add", "Buy milk"],
        ["add", "Write report", "--priority", "high", "--due", "2026-03-01"],
        ["add", "Call Sam", "--priority", "low"],
        ["list"],
        ["done", "1"],
        ["rm", "3"],
        ["list"],
        ["done", "9"],
        ["add"],
        ["add", "X", "--priority", "urgent"],
    ], "v2")

    # ------------------------------------------------------------------ v3
    cli_v3_body = CLI_V2
    cli_v3_body = patch(cli_v3_body, "use crate::store;\n", "use crate::date;\nuse crate::store;\n")
    cli_v3_body = patch(cli_v3_body, '"list" => list(path),', '"list" => list(rest, path),')
    cli_v3_body = patch(cli_v3_body, '"       tasks list",', '"       tasks list [--pending|--done] [--sort id|priority|due]",')
    cli_v3_body = patch(cli_v3_body, CLI_DUE_V2.strip("\n"), CLI_DUE_V3.strip("\n"))
    cli_v3_body = patch(cli_v3_body, LIST_V2.strip("\n"), LIST_V3.strip("\n"))
    cli_v3 = cli_v3_body + "\n" + CLI_TESTS_HEAD + "".join(CLI_TESTS_V2) + "".join(CLI_TESTS_V3_NEW) + "}\n"
    main_v3 = patch(MAIN_V2, "mod cli;\n", "mod cli;\nmod date;\n")
    write("v3", "Cargo.toml", CARGO_TOML)
    write("v3", "src/main.rs", main_v3)
    write("v3", "src/task.rs", task_v2 + "\n" + task_tests_v2)
    write("v3", "src/store.rs", store_v2)
    write("v3", "src/date.rs", DATE_V3)
    write("v3", "src/cli.rs", cli_v3)
    build_and_test("v3", "v3")
    scenario("v3_run", "v3", [
        ["add", "Write report", "--priority", "high", "--due", "2026-03-01"],
        ["add", "Buy milk", "--due", "2026-02-30"],
        ["add", "Buy milk", "--due", "2026-02-28"],
        ["add", "Call Sam", "--priority", "low"],
        ["add", "Book flights", "--priority", "high"],
        ["done", "3"],
        ["list", "--sort", "priority"],
        ["list", "--sort", "due"],
        ["list", "--pending"],
        ["list", "--sort", "colour"],
    ], "v3")

    # ------------------------------------------------------------------ v4 : the bug report
    # 1) the failing test first, against the v3 code
    write("v4a", "Cargo.toml", CARGO_TOML)
    write("v4a", "src/main.rs", main_v3)
    task_tests_v4_repro = patch(
        task_tests_v2,
        "    #[test]\n    fn priority_respects_a_width() {",
        TASK_TESTS_V4_NEW.split("    #[test]\n    fn backslashes_and_line_breaks_round_trip")[0].strip("\n") + "\n\n"
        "    #[test]\n    fn priority_respects_a_width() {",
    )
    write("v4a", "src/task.rs", task_v2 + "\n" + task_tests_v4_repro)
    write("v4a", "src/store.rs", store_v2)
    write("v4a", "src/date.rs", DATE_V3)
    write("v4a", "src/cli.rs", cli_v3)
    build_and_test("v4a", "v4a")
    # 2) what the user saw with the real v3 binary
    rd = scenario("v4_before", "v3", [
        ["add", "Compare a|b"],
        ["list"],
        ["add", "Another task"],
        ["done", "1"],
    ], "v4_before")
    RESULTS["v4_before_file"] = (rd / "tasks.txt").read_text(encoding="utf-8")

    # 3) the fix
    task_v4 = patch(task_v2, TASK_V4_TOLINE_OLD.strip("\n"), TASK_V4_TOLINE_NEW.strip("\n"))
    task_v4 = patch(task_v4, TASK_V4_SPLIT_OLD.strip("\n"), TASK_V4_SPLIT_NEW.strip("\n"))
    task_v4 = patch(task_v4, '= match parts[2] {', '= match parts[2].as_str() {')
    task_v4 = task_v4.rstrip("\n") + "\n" + TASK_V4_HELPERS
    new_tests_block = TASK_TESTS_V4_NEW.strip("\n") + "\n\n"
    task_tests_v4 = patch(
        task_tests_v2,
        "    #[test]\n    fn priority_respects_a_width() {",
        new_tests_block + "    #[test]\n    fn priority_respects_a_width() {",
    )
    store_v4_body = patch(STORE_V2, "use std::path::Path;\n", "use std::path::{Path, PathBuf};\n")
    store_v4_body = patch(store_v4_body, STORE_LOOP_V2.strip("\n"), STORE_LOOP_V4.strip("\n"))
    store_v4_body = patch(store_v4_body, STORE_SAVE_V2.strip("\n"), STORE_SAVE_V4.strip("\n"))
    store_v4_body = patch(
        store_v4_body,
        "    let _ = fs::remove_file(&path);\n    path\n",
        "    let _ = fs::remove_file(&path);\n    let mut tmp = path.as_os_str().to_owned();\n    tmp.push(\".tmp\");\n    let _ = fs::remove_file(PathBuf::from(tmp));\n    path\n",
    )
    store_v4 = store_v4_body + "\n" + STORE_TESTS_HEAD + STORE_BAD_LINE_V4
    cli_v4 = cli_v3_body + "\n" + CLI_TESTS_HEAD + "".join(CLI_TESTS_V2) + "".join(CLI_TESTS_V3_NEW) + CLI_TEST_V4_NEW + "}\n"
    write("v4", "Cargo.toml", CARGO_TOML)
    write("v4", "src/main.rs", main_v3)
    write("v4", "src/task.rs", task_v4 + "\n" + task_tests_v4)
    write("v4", "src/store.rs", store_v4)
    write("v4", "src/date.rs", DATE_V3)
    write("v4", "src/cli.rs", cli_v4)
    build_and_test("v4", "v4")
    # same data file, now read by the fixed binary
    rd = ROOT / "run" / "v4_before"
    shutil.copy(rd / "tasks.txt", rd / "tasks_from_v3.txt")
    scenario("v4_after_old_file", "v4", [["list"], ["add", "Another task"]], "v4_before", fresh=False)
    # hand-fix the old line (what the user would do), then it loads
    old = (rd / "tasks.txt").read_text(encoding="utf-8")
    fixed = old.replace("1|Compare a|b|false|normal|", "1|Compare a\\|b|false|normal|")
    assert fixed != old
    (rd / "tasks.txt").write_text(fixed, encoding="utf-8", newline="\n")
    scenario("v4_after_fix", "v4", [["list"], ["add", "Pipes | and \\ backslashes"], ["list"]], "v4_before", fresh=False)
    RESULTS["v4_after_file"] = (rd / "tasks.txt").read_text(encoding="utf-8")
    # a brand-new file
    rd2 = scenario("v4_new", "v4", [["add", "Compare a|b"], ["done", "1"], ["list"]], "v4_new")
    RESULTS["v4_new_file"] = (rd2 / "tasks.txt").read_text(encoding="utf-8")
    RESULTS["v4_tmp_left"] = sorted(p.name for p in rd2.iterdir())

    # ------------------------------------------------------------------ v5
    cli_v5 = CLI_V5 + "\n" + CLI_TESTS_HEAD + "".join(CLI_TESTS_V5) + "}\n"
    write("v5", "Cargo.toml", CARGO_TOML)
    write("v5", "src/main.rs", MAIN_V5)
    write("v5", "src/task.rs", task_v4 + "\n" + task_tests_v4)
    write("v5", "src/store.rs", store_v4)
    write("v5", "src/date.rs", DATE_V3)
    write("v5", "src/cli.rs", cli_v5)
    build_and_test("v5", "v5")
    scenario("v5_run", "v5", [
        ["add", "Write report", "--priority", "high", "--due", "2026-03-01"],
        ["add", "Buy milk"],
        ["add", "Call Sam", "--priority", "low"],
        ["add", "Book flights", "--priority", "high"],
        ["done", "2"],
        ["edit", "1", "--due", "2026-03-15", "--title", "Write the quarterly report"],
        ["edit", "3", "--priority", "normal"],
        ["edit", "1", "--due", "none"],
        ["list"],
        ["stats"],
    ], "v5")
    rd5 = ROOT / "run" / "v5"
    scenario("v5_errors", "v5", [
        ["done", "99"],
        ["edit", "1"],
        ["add"],
        ["frobnicate"],
        [],
        ["help"],
    ], "v5", fresh=False)
    # a corrupt data file is a failure (exit 1), not a usage error
    (ROOT / "run" / "v5_corrupt").mkdir(parents=True, exist_ok=True)
    (ROOT / "run" / "v5_corrupt" / "tasks.txt").write_text("1|Fine|false|normal|\n2|Broken|maybe|normal|\n", encoding="utf-8", newline="\n")
    scenario("v5_corrupt", "v5", [["list"]], "v5_corrupt", fresh=False)

    (ROOT / "results.json").write_text(json.dumps(RESULTS, indent=1), encoding="utf-8")
    print("OK results saved")


if __name__ == "__main__":
    main()

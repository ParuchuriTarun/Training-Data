"""Build data/staging/claude_rust_apps_13.txt. Every Rust program is compiled and RUN here,
and the real output is pasted into the answer, so the 'Output' blocks are true by construction."""
import subprocess
import sys
import tempfile
from pathlib import Path

F = "`" * 3
OUT = Path(r"C:\Projects\Mavo\Coding 1 2B\data\staging\claude_rust_apps_13.txt")


def run_rust(code):
    d = Path(tempfile.mkdtemp())
    (d / "m.rs").write_text(code, encoding="utf-8")
    r = subprocess.run(["rustc", "--edition", "2021", "-o", str(d / "m.exe"), str(d / "m.rs")],
                       capture_output=True, text=True)
    if r.returncode:
        print("COMPILE FAIL:\n", r.stderr[:1500])
        sys.exit(1)
    if r.stderr.strip():
        print("WARNINGS:\n", r.stderr[:800])
    p = subprocess.run([str(d / "m.exe")], capture_output=True, text=True, timeout=20)
    return p.stdout.rstrip("\n")


EXAMPLES = []


def ex(question, intro, code, after):
    out = run_rust(code)
    ans = f"{intro}\n\n{F}rust\n{code.strip()}\n{F}\n\nOutput:\n\n{F}\n{out}\n{F}\n\n{after.strip()}"
    EXAMPLES.append((question, ans))


# 1 ---------------------------------------------------------------------------------------------
ex("Write a small reverse Polish notation calculator in Rust with proper error handling (no unwrap, no panics).",
   "Here is a complete program. Errors are an `enum`, so the caller can tell them apart, and `Display` turns them into messages for the user.",
   r'''
use std::fmt;

#[derive(Debug, PartialEq)]
enum CalcError {
    StackUnderflow,
    DivideByZero,
    BadToken(String),
    LeftOver(usize),
}

impl fmt::Display for CalcError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            CalcError::StackUnderflow => write!(f, "not enough numbers on the stack"),
            CalcError::DivideByZero => write!(f, "division by zero"),
            CalcError::BadToken(t) => write!(f, "cannot understand '{}'", t),
            CalcError::LeftOver(n) => write!(f, "{} numbers left on the stack", n),
        }
    }
}

fn eval_rpn(input: &str) -> Result<f64, CalcError> {
    let mut stack: Vec<f64> = Vec::new();
    for token in input.split_whitespace() {
        match token {
            "+" | "-" | "*" | "/" => {
                let b = stack.pop().ok_or(CalcError::StackUnderflow)?;
                let a = stack.pop().ok_or(CalcError::StackUnderflow)?;
                let result = match token {
                    "+" => a + b,
                    "-" => a - b,
                    "*" => a * b,
                    _ => {
                        if b == 0.0 {
                            return Err(CalcError::DivideByZero);
                        }
                        a / b
                    }
                };
                stack.push(result);
            }
            number => {
                let n: f64 = number
                    .parse()
                    .map_err(|_| CalcError::BadToken(number.to_string()))?;
                stack.push(n);
            }
        }
    }
    match stack.len() {
        1 => Ok(stack[0]),
        0 => Err(CalcError::StackUnderflow),
        n => Err(CalcError::LeftOver(n)),
    }
}

fn main() {
    let inputs = ["3 4 +", "5 1 2 + 4 * + 3 -", "2 0 /", "1 +", "1 2", "2 x *"];
    for line in inputs {
        match eval_rpn(line) {
            Ok(v) => println!("{:<20} = {}", line, v),
            Err(e) => println!("{:<20} error: {}", line, e),
        }
    }
}
''',
   """
How it works:
- RPN needs only a stack. A number is pushed. An operator pops two numbers (`b` first, then `a`, because the right operand is on top), computes `a op b` and pushes the result.
- `stack.pop().ok_or(CalcError::StackUnderflow)?` turns the `Option` from `pop` into a `Result` and returns early with `?`. That is how `"1 +"` becomes an error instead of a panic.
- Division checks `b == 0.0` explicitly. For `f64`, dividing by zero would silently give `inf`, which is almost never what a calculator should show.
- At the end exactly one value must remain. Zero values or more than one both mean the expression was malformed, and `LeftOver(n)` says how many were left.
- `map_err` converts the `ParseFloatError` into your own error type, so the function has one error type for all failures.

To read expressions from the terminal, wrap `eval_rpn` in a loop over `std::io::stdin().lines()`; the function itself does not change.""")

# 2 ---------------------------------------------------------------------------------------------
ex("How do I count word frequencies in Rust and print the top words, sorted by count and then alphabetically?",
   "Use a `HashMap<String, usize>` to count, copy it into a `Vec`, and sort with a comparison that looks at the count first and the word second. `HashMap` has no order, so sorting is what makes the output stable.",
   r'''
use std::collections::HashMap;

fn count_words(text: &str) -> HashMap<String, usize> {
    let mut counts = HashMap::new();
    for raw in text.split_whitespace() {
        let word: String = raw
            .trim_matches(|c: char| !c.is_alphanumeric())
            .to_lowercase();
        if word.is_empty() {
            continue;
        }
        *counts.entry(word).or_insert(0) += 1;
    }
    counts
}

fn main() {
    let text = "The cat sat on the mat. The dog sat on the log; the cat ran. \
                A cat, a dog, and a log!";
    let counts = count_words(text);

    let mut items: Vec<(&String, &usize)> = counts.iter().collect();
    items.sort_by(|a, b| b.1.cmp(a.1).then(a.0.cmp(b.0)));

    for (word, n) in items.iter().take(5) {
        println!("{:<5} {}", word, n);
    }
    println!("distinct words: {}", counts.len());
}
''',
   """
Points to remember:
- `entry(word).or_insert(0)` returns a mutable reference to the counter, and `*... += 1` increments it. This is the standard counting idiom and does only one lookup.
- `trim_matches` with a closure removes punctuation from both ends only, so `mat.` becomes `mat` but a word like `don't` keeps its apostrophe.
- `b.1.cmp(a.1)` compares the counts in reverse (largest first). `.then(a.0.cmp(b.0))` is only used when the counts are equal and sorts those words alphabetically.
- To read a real file, replace the string with `std::fs::read_to_string("input.txt")?` and return `Result` from `main`.""")

# 3 ---------------------------------------------------------------------------------------------
ex("How do I parse a simple key=value config file into a struct in Rust, with error messages that include the line number?",
   "Implement `FromStr` for the config struct. Parse line by line, skip blank lines and `#` comments, and wrap every failure in an error type that remembers the line number.",
   r'''
use std::fmt;
use std::str::FromStr;

#[derive(Debug)]
struct ServerConfig {
    host: String,
    port: u16,
    debug: bool,
}

#[derive(Debug)]
enum ConfigError {
    MissingEquals { line: usize },
    UnknownKey { line: usize, key: String },
    BadValue { line: usize, key: String },
    Missing(&'static str),
}

impl fmt::Display for ConfigError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            ConfigError::MissingEquals { line } => write!(f, "line {}: expected key=value", line),
            ConfigError::UnknownKey { line, key } => write!(f, "line {}: unknown key '{}'", line, key),
            ConfigError::BadValue { line, key } => write!(f, "line {}: bad value for '{}'", line, key),
            ConfigError::Missing(key) => write!(f, "missing required key '{}'", key),
        }
    }
}

impl FromStr for ServerConfig {
    type Err = ConfigError;

    fn from_str(text: &str) -> Result<Self, Self::Err> {
        let mut host = None;
        let mut port = None;
        let mut debug = false;

        for (index, raw) in text.lines().enumerate() {
            let line = index + 1;
            let trimmed = raw.trim();
            if trimmed.is_empty() || trimmed.starts_with('#') {
                continue;
            }
            let (key, value) = trimmed
                .split_once('=')
                .ok_or(ConfigError::MissingEquals { line })?;
            let (key, value) = (key.trim(), value.trim());
            let bad = || ConfigError::BadValue { line, key: key.to_string() };
            match key {
                "host" => host = Some(value.to_string()),
                "port" => port = Some(value.parse::<u16>().map_err(|_| bad())?),
                "debug" => debug = value.parse::<bool>().map_err(|_| bad())?,
                other => {
                    return Err(ConfigError::UnknownKey { line, key: other.to_string() })
                }
            }
        }

        Ok(ServerConfig {
            host: host.ok_or(ConfigError::Missing("host"))?,
            port: port.ok_or(ConfigError::Missing("port"))?,
            debug,
        })
    }
}

fn main() {
    let samples = [
        "# my server\nhost = localhost\nport = 8080\ndebug = true\n",
        "host = example.org\nport = 99999\n",
        "host = example.org\nport\n",
        "host = example.org\ncolour = red\n",
        "port = 80\n",
    ];
    for text in samples {
        match text.parse::<ServerConfig>() {
            Ok(cfg) => println!("ok: {:?}", cfg),
            Err(e) => println!("error: {}", e),
        }
    }
}
''',
   """
Why this shape works:
- `impl FromStr` gives you `text.parse::<ServerConfig>()` for free, which reads naturally and plugs into generic code.
- `split_once('=')` splits at the first `=` only, so values may contain `=` themselves (for example a URL with a query string).
- `host` and `port` start as `Option` and are checked at the end, so the order of lines in the file does not matter and a missing key gets its own clear error.
- `99999` fails because it does not fit in a `u16` (maximum 65535). Choosing the field type is also the validation.
- The small closure `bad` avoids repeating the same `BadValue { line, key }` construction in every branch.

For real projects the `serde` and `toml` crates do this for you, but writing it once by hand shows what those crates are doing.""")

# 4 ---------------------------------------------------------------------------------------------
ex("When should I use trait objects (Box<dyn Trait>) in Rust? Show me an example with shapes.",
   "Use `Box<dyn Trait>` when you need one collection that holds different concrete types that share behaviour, and you only find out which types at run time. Here a `Vec` holds circles, rectangles and triangles together.",
   r'''
use std::f64::consts::PI;

trait Shape {
    fn area(&self) -> f64;
    fn name(&self) -> String;

    // A default method that every shape gets for free.
    fn describe(&self) -> String {
        format!("{} with area {:.2}", self.name(), self.area())
    }
}

struct Circle { radius: f64 }
struct Rect { width: f64, height: f64 }
struct Triangle { base: f64, height: f64 }

impl Shape for Circle {
    fn area(&self) -> f64 { PI * self.radius * self.radius }
    fn name(&self) -> String { "circle".to_string() }
}

impl Shape for Rect {
    fn area(&self) -> f64 { self.width * self.height }
    fn name(&self) -> String { "rectangle".to_string() }
}

impl Shape for Triangle {
    fn area(&self) -> f64 { 0.5 * self.base * self.height }
    fn name(&self) -> String { "triangle".to_string() }
    fn describe(&self) -> String {
        format!("a triangle (base {}, height {})", self.base, self.height)
    }
}

fn total_area(shapes: &[Box<dyn Shape>]) -> f64 {
    shapes.iter().map(|s| s.area()).sum()
}

fn main() {
    let shapes: Vec<Box<dyn Shape>> = vec![
        Box::new(Circle { radius: 1.5 }),
        Box::new(Rect { width: 2.0, height: 4.0 }),
        Box::new(Triangle { base: 3.0, height: 5.0 }),
    ];

    for s in &shapes {
        println!("{}", s.describe());
    }
    println!("total area: {:.3}", total_area(&shapes));

    let biggest = shapes
        .iter()
        .max_by(|a, b| a.area().partial_cmp(&b.area()).unwrap())
        .unwrap();
    println!("biggest: {}", biggest.name());
}
''',
   """
Notes:
- A `Vec<Shape>` is not possible, because the three types have different sizes. `Box<dyn Shape>` is a fixed-size pointer plus a table of methods, so they can live in one vector.
- Method calls on `dyn Trait` are resolved at run time (dynamic dispatch). That costs a small indirect call.
- If you know the set of types at compile time, an `enum Shape { Circle(..), Rect(..), Triangle(..) }` with a `match` is usually faster and lets the compiler check that you handled every case.
- If all items have the same type, use generics (`fn total<T: Shape>(items: &[T])`) to get static dispatch with no box.
- `partial_cmp(...).unwrap()` is needed because `f64` has `NaN` and therefore no total order. It is fine here because no area can be `NaN`.""")

# 5 ---------------------------------------------------------------------------------------------
ex("Show me the builder pattern in Rust for a struct with many optional fields.",
   "A builder collects the options with chained method calls and validates them once in `build()`. Required fields go into `new`, optional ones become setters.",
   r'''
use std::collections::BTreeMap;

#[derive(Debug)]
struct Request {
    url: String,
    method: String,
    headers: BTreeMap<String, String>,
    body: Option<String>,
    timeout_secs: u32,
}

struct RequestBuilder {
    url: String,
    method: String,
    headers: BTreeMap<String, String>,
    body: Option<String>,
    timeout_secs: u32,
}

impl RequestBuilder {
    fn new(url: &str) -> Self {
        RequestBuilder {
            url: url.to_string(),
            method: "GET".to_string(),
            headers: BTreeMap::new(),
            body: None,
            timeout_secs: 30,
        }
    }

    fn method(mut self, method: &str) -> Self {
        self.method = method.to_uppercase();
        self
    }

    fn header(mut self, key: &str, value: &str) -> Self {
        self.headers.insert(key.to_string(), value.to_string());
        self
    }

    fn json(mut self, body: &str) -> Self {
        self.body = Some(body.to_string());
        self.header("Content-Type", "application/json")
    }

    fn timeout(mut self, secs: u32) -> Self {
        self.timeout_secs = secs;
        self
    }

    fn build(self) -> Result<Request, String> {
        if !self.url.starts_with("http://") && !self.url.starts_with("https://") {
            return Err(format!("url must start with http:// or https://, got '{}'", self.url));
        }
        if self.body.is_some() && self.method == "GET" {
            return Err("a GET request cannot have a body".to_string());
        }
        if self.timeout_secs == 0 {
            return Err("timeout must be at least 1 second".to_string());
        }
        Ok(Request {
            url: self.url,
            method: self.method,
            headers: self.headers,
            body: self.body,
            timeout_secs: self.timeout_secs,
        })
    }
}

fn main() {
    let ok = RequestBuilder::new("https://api.example.com/items")
        .method("post")
        .json(r#"{"name":"pen"}"#)
        .header("X-Trace", "abc123")
        .timeout(10)
        .build();
    println!("{:#?}", ok);

    let bad = RequestBuilder::new("https://api.example.com/items")
        .json("{}")
        .build();
    println!("{:?}", bad.map(|r| r.url));

    let also_bad = RequestBuilder::new("ftp://old.example.com").build();
    println!("{:?}", also_bad.map(|r| r.url));
}
''',
   """
Why use `mut self` and return `Self`:
- Each setter takes the builder by value, changes it and gives it back. That is what allows the chained style `.method(..).header(..).build()`, and it means a half-built builder cannot be used by accident after `build()` consumed it.
- `json()` calls `self.header(...)` at the end, so one setter can reuse another.
- `build()` is the only place that checks rules involving several fields (a `GET` with a body). A struct with public fields cannot enforce that.
- `BTreeMap` keeps headers sorted, so the debug output is the same on every run. With `HashMap` the order would vary.

If a builder would be borrowed rather than consumed, change the setters to `&mut self -> &mut Self` and `build(&self)`. Use that form when you want to build the same configuration several times.""")

# 6 ---------------------------------------------------------------------------------------------
ex("How do I parse a list of strings into numbers in Rust and either fail on the first error or keep the good ones?",
   "There are two common needs, and iterators handle both. To fail on the first bad value, collect into `Result<Vec<_>, _>`. To keep the good values and report the bad ones, use `partition` on the results.",
   r'''
fn parse_all(items: &[&str]) -> Result<Vec<i32>, std::num::ParseIntError> {
    items.iter().map(|s| s.trim().parse::<i32>()).collect()
}

fn main() {
    // 1) Stop at the first error.
    println!("{:?}", parse_all(&["1", " 2 ", "3"]));
    println!("{:?}", parse_all(&["1", "two", "3", "four"]));

    // 2) Keep the good ones, report the bad ones.
    let input = ["10", "x", "30", "", "-5", "9999999999"];
    let (good, bad): (Vec<_>, Vec<_>) = input
        .iter()
        .map(|s| (s, s.parse::<i32>()))
        .partition(|(_, r)| r.is_ok());

    let numbers: Vec<i32> = good.into_iter().map(|(_, r)| r.unwrap()).collect();
    let errors: Vec<String> = bad
        .into_iter()
        .map(|(s, r)| format!("{:?}: {}", s, r.unwrap_err()))
        .collect();

    println!("numbers = {:?}", numbers);
    for e in &errors {
        println!("  {}", e);
    }

    // 3) Silently skip bad values (only when that is really what you want).
    let sum: i32 = input.iter().filter_map(|s| s.parse::<i32>().ok()).sum();
    println!("sum of valid = {}", sum);
}
''',
   """
Summary:
- `collect::<Result<Vec<_>, _>>()` works because `Result` knows how to collect an iterator of `Result`s: it stops at the first `Err` and returns it, otherwise it returns `Ok` with all the values. Note that it reports `"two"`, not `"four"`.
- `partition` splits an iterator into two collections by a predicate. Keeping the original string next to each result lets the error message say which input failed.
- Calling `unwrap()` and `unwrap_err()` is safe here only because `partition` already guaranteed each item is `Ok` or `Err` respectively.
- `filter_map(... .ok())` is short, but it hides errors. Use it for optional data, not for user input that should be reported.
- `9999999999` is a valid number but does not fit in an `i32`, so it is an error with a different message than the empty string.""")

# 7 ---------------------------------------------------------------------------------------------
ex("How do I structure a command-line app in Rust with subcommands without using any crates?",
   "Separate three things: parsing the arguments into a `Command` enum, running the command on your data, and printing. Because parsing takes a slice of strings and not `std::env::args()` directly, you can test it and call it from `main` with the real arguments.",
   r'''
#[derive(Debug, PartialEq)]
enum Command {
    Add { name: String, qty: u32 },
    Remove { name: String },
    List,
    Help,
}

fn parse_command(args: &[&str]) -> Result<Command, String> {
    match args {
        [] | ["help"] => Ok(Command::Help),
        ["list"] => Ok(Command::List),
        ["add", name, qty] => {
            let qty = qty
                .parse::<u32>()
                .map_err(|_| format!("quantity must be a whole number, got '{}'", qty))?;
            Ok(Command::Add { name: name.to_string(), qty })
        }
        ["add", ..] => Err("usage: add <name> <qty>".to_string()),
        ["remove", name] => Ok(Command::Remove { name: name.to_string() }),
        ["remove", ..] => Err("usage: remove <name>".to_string()),
        [other, ..] => Err(format!("unknown command '{}'", other)),
    }
}

struct Inventory {
    items: Vec<(String, u32)>,
}

impl Inventory {
    fn run(&mut self, cmd: Command) -> String {
        match cmd {
            Command::Add { name, qty } => {
                if let Some(item) = self.items.iter_mut().find(|(n, _)| *n == name) {
                    item.1 += qty;
                    format!("{} now has {}", name, item.1)
                } else {
                    self.items.push((name.clone(), qty));
                    format!("added {} x{}", name, qty)
                }
            }
            Command::Remove { name } => {
                let before = self.items.len();
                self.items.retain(|(n, _)| *n != name);
                if self.items.len() < before {
                    format!("removed {}", name)
                } else {
                    format!("no item called {}", name)
                }
            }
            Command::List => {
                if self.items.is_empty() {
                    "(empty)".to_string()
                } else {
                    self.items
                        .iter()
                        .map(|(n, q)| format!("{}: {}", n, q))
                        .collect::<Vec<_>>()
                        .join("\n")
                }
            }
            Command::Help => "commands: add <name> <qty> | remove <name> | list | help".to_string(),
        }
    }
}

fn main() {
    // In a real program: let owned: Vec<String> = std::env::args().skip(1).collect();
    //                    let args: Vec<&str> = owned.iter().map(String::as_str).collect();
    let script: [&[&str]; 8] = [
        &["help"],
        &["add", "pen", "3"],
        &["add", "book", "1"],
        &["add", "pen", "2"],
        &["add", "cup", "many"],
        &["remove", "book"],
        &["fly"],
        &["list"],
    ];

    let mut inv = Inventory { items: Vec::new() };
    for args in script {
        println!("> {}", args.join(" "));
        match parse_command(args) {
            Ok(cmd) => println!("{}", inv.run(cmd)),
            Err(e) => println!("error: {}", e),
        }
    }
}
''',
   """
What to take from it:
- Slice patterns such as `["add", name, qty]` make argument parsing a plain `match`. The order of the arms matters: `["add", ..]` comes after the exact form so that wrong argument counts give a usage message.
- The `Command` enum is the contract between parsing and running. You can add `Command::Rename` later and the compiler will point to every `match` that must handle it.
- `parse_command` is pure (no printing, no global state), so a unit test is one line: `assert_eq!(parse_command(&["list"]), Ok(Command::List))`.
- In the real `main`, collect `std::env::args().skip(1)` into a `Vec<String>`, then borrow it as `Vec<&str>` as the comment shows. `skip(1)` removes the program name.
- When the app grows past a few commands and flags, the `clap` crate saves a lot of code. Doing it by hand first helps you understand what it generates.""")

# 8 ---------------------------------------------------------------------------------------------
ex("Write Conway's Game of Life in Rust that prints a few generations of a glider.",
   "Store the board in a flat `Vec<bool>`, count the eight neighbours with wrap-around (a torus), and build the next generation into a new vector so the rules apply to all cells at the same moment.",
   r'''
struct Life {
    width: usize,
    height: usize,
    cells: Vec<bool>,
}

impl Life {
    fn new(width: usize, height: usize, alive: &[(usize, usize)]) -> Life {
        let mut cells = vec![false; width * height];
        for &(x, y) in alive {
            cells[y * width + x] = true;
        }
        Life { width, height, cells }
    }

    fn neighbours(&self, x: usize, y: usize) -> usize {
        let mut count = 0;
        for dy in [self.height - 1, 0, 1] {
            for dx in [self.width - 1, 0, 1] {
                if dx == 0 && dy == 0 {
                    continue;
                }
                let nx = (x + dx) % self.width;
                let ny = (y + dy) % self.height;
                if self.cells[ny * self.width + nx] {
                    count += 1;
                }
            }
        }
        count
    }

    fn step(&mut self) {
        let mut next = vec![false; self.cells.len()];
        for y in 0..self.height {
            for x in 0..self.width {
                let alive = self.cells[y * self.width + x];
                let n = self.neighbours(x, y);
                next[y * self.width + x] = matches!((alive, n), (true, 2) | (true, 3) | (false, 3));
            }
        }
        self.cells = next;
    }

    fn render(&self) -> String {
        self.cells
            .chunks(self.width)
            .map(|row| row.iter().map(|&c| if c { '#' } else { '.' }).collect::<String>())
            .collect::<Vec<_>>()
            .join("\n")
    }
}

fn main() {
    let mut life = Life::new(6, 6, &[(1, 0), (2, 1), (0, 2), (1, 2), (2, 2)]);
    for generation in 0..4 {
        println!("generation {}:\n{}\n", generation, life.render());
        life.step();
    }
    let alive = life.cells.iter().filter(|&&c| c).count();
    println!("cells alive after 4 steps: {}", alive);
}
''',
   """
How it works:
- Cell `(x, y)` lives at index `y * width + x`. One flat vector is simpler and faster than a `Vec<Vec<bool>>`.
- The wrap-around trick: to look one cell to the left, add `width - 1` and take `% width`. This avoids negative numbers, which `usize` cannot hold, so there are no `as i32` casts and no underflow panics at the edges.
- `step` writes into `next` and reads from `self.cells`. If you updated the board in place, the cells already updated would change the neighbour counts of later cells and give a wrong result.
- `matches!((alive, n), (true, 2) | (true, 3) | (false, 3))` is the whole rule set: a live cell with 2 or 3 neighbours survives, a dead cell with exactly 3 is born, everything else is dead.
- The glider keeps its 5 cells while it moves one cell diagonally every 4 generations.""")


def block(q, a):
    return f"@@@ USER\n{q}\n@@@ ASSISTANT\n{a}\n@@@ END\n\n"


OUT.write_text("".join(block(q, a) for q, a in EXAMPLES), encoding="utf-8")
print("wrote", OUT, len(EXAMPLES), "examples", OUT.stat().st_size, "bytes")

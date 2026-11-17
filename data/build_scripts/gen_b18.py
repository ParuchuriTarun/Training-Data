"""Build data/staging/claude_rust_patterns_18.txt. Every Rust program is compiled and RUN (or run as tests),
and the real output / compiler message is pasted into the answer."""
import subprocess
import sys
import tempfile
from pathlib import Path

F = "`" * 3
OUT = Path(r"C:\Projects\Mavo\Coding 1 2B\data\staging\claude_rust_patterns_18.txt")


def _run(cmd, d, timeout=60):
    p = subprocess.run(cmd, cwd=d, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True, encoding="utf-8", timeout=timeout)
    return p.returncode, p.stdout.replace("\r", "").rstrip("\n")


def build(code, test=False):
    d = Path(tempfile.mkdtemp())
    (d / "m.rs").write_text(code.strip() + "\n", encoding="utf-8", newline="\n")
    cmd = ["rustc", "--edition", "2021", "-o", "m.exe", "m.rs"]
    if test:
        cmd.insert(1, "--test")
    rc, out = _run(cmd, d)
    return d, rc, out


def run_rust(code):
    d, rc, out = build(code)
    if rc:
        print("COMPILE FAIL\n", out[:2000]); sys.exit(1)
    if out.strip():
        print("WARNINGS (check them):\n", out[:600])
    rc, out = _run([str(d / "m.exe")], d)
    return out


def run_tests(code):
    d, rc, out = build(code, test=True)
    if rc:
        print("TEST COMPILE FAIL\n", out[:2000]); sys.exit(1)
    rc, out = _run([str(d / "m.exe"), "--test-threads=1"], d)
    if rc:
        print("TESTS FAILED\n", out[:1500]); sys.exit(1)
    # drop the timing line, which changes on every run
    return "\n".join(l for l in out.splitlines() if "finished in" not in l).strip() + "\ntest result: ok (timing omitted)" if False else \
        "\n".join(l.split("; finished in")[0] if "test result" in l else l for l in out.splitlines())


def rust_error(code):
    d, rc, out = build(code)
    if rc == 0:
        print("EXPECTED A COMPILE ERROR"); sys.exit(1)
    keep = []
    for line in out.splitlines():
        if line.startswith("error: aborting") or line.startswith("For more information"):
            break
        keep.append(line)
    return "\n".join(keep).rstrip()


EXAMPLES = []


def ex(question, intro, code, after, lang="rust", tests=False):
    out = run_tests(code) if tests else run_rust(code)
    label = "Test output" if tests else "Output"
    ans = f"{intro}\n\n{F}{lang}\n{code.strip()}\n{F}\n\n{label}:\n\n{F}\n{out}\n{F}\n\n{after.strip()}"
    EXAMPLES.append((question, ans))


# 1 ---------------------------------------------------------------------------------------------
ex("How do I read a file in Rust and report errors well? I want my own error type, the ? operator and the line number of a bad line.",
   "Define one error `enum` for your module, implement `From<io::Error>` so that `?` converts automatically, and keep the line number inside the variants that need it. The demo writes its own sample files in a temporary folder, so you can run it as it is.",
   r'''
use std::collections::BTreeMap;
use std::error::Error;
use std::fmt;
use std::fs;
use std::num::ParseFloatError;
use std::path::Path;

#[derive(Debug)]
enum LedgerError {
    Io(std::io::Error),
    BadAmount { line: usize, source: ParseFloatError },
    BadLine { line: usize, text: String },
}

impl fmt::Display for LedgerError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            LedgerError::Io(_) => write!(f, "cannot read the file"),
            LedgerError::BadAmount { line, .. } => write!(f, "line {}: the amount is not a number", line),
            LedgerError::BadLine { line, text } => write!(f, "line {}: expected 'name, amount' but found '{}'", line, text),
        }
    }
}

impl Error for LedgerError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            LedgerError::Io(e) => Some(e),
            LedgerError::BadAmount { source, .. } => Some(source),
            LedgerError::BadLine { .. } => None,
        }
    }
}

impl From<std::io::Error> for LedgerError {
    fn from(e: std::io::Error) -> Self {
        LedgerError::Io(e)
    }
}

fn totals(path: &Path) -> Result<BTreeMap<String, f64>, LedgerError> {
    let text = fs::read_to_string(path)?; // io::Error becomes LedgerError through From
    let mut map = BTreeMap::new();
    for (index, line) in text.lines().enumerate() {
        let line_no = index + 1;
        if line.trim().is_empty() {
            continue;
        }
        let (name, amount) = line
            .split_once(',')
            .ok_or_else(|| LedgerError::BadLine { line: line_no, text: line.to_string() })?;
        let amount: f64 = amount
            .trim()
            .parse()
            .map_err(|source| LedgerError::BadAmount { line: line_no, source })?;
        *map.entry(name.trim().to_string()).or_insert(0.0) += amount;
    }
    Ok(map)
}

fn main() -> Result<(), Box<dyn Error>> {
    let dir = std::env::temp_dir().join("ledger_demo");
    fs::create_dir_all(&dir)?;

    let good = dir.join("good.csv");
    fs::write(&good, "food, 12.5\nrent, 800\n\nfood, 7.25\n")?;
    let bad_amount = dir.join("bad_amount.csv");
    fs::write(&bad_amount, "food, 12.5\nrent, lots\n")?;
    let bad_line = dir.join("bad_line.csv");
    fs::write(&bad_line, "food 12.5\n")?;
    let missing = dir.join("missing.csv");

    for path in [&good, &bad_amount, &bad_line, &missing] {
        let name = path.file_name().unwrap().to_string_lossy();
        match totals(path) {
            Ok(map) => println!("{name}: {map:?}"),
            Err(e) => {
                print!("{name}: error: {e}");
                if let Some(cause) = e.source() {
                    print!(" (cause: {cause})");
                }
                println!();
            }
        }
    }

    fs::remove_dir_all(&dir)?;
    Ok(())
}
''',
   """
Notes:
- `fs::read_to_string(path)?` returns early with an `Err` on failure. The `?` operator calls `From::from` on the error, which is why the `From<io::Error>` implementation lets you write one line instead of a `match`.
- `ok_or_else(|| ...)` turns the `Option` from `split_once` into a `Result`. The closure form creates the error (and clones the line) only when it is needed.
- Keeping the original error in `source` and returning it from `Error::source()` preserves the **chain of causes**. `Display` of your error says what failed in your domain ("line 2: the amount is not a number"), and `source()` gives the technical reason (`invalid float literal`). A caller or a logger can print both.
- The exact wording of the last message comes from the operating system, so it differs between Windows, Linux and macOS (only the part inside the parentheses; the first part is yours).
- `fn main() -> Result<(), Box<dyn Error>>` lets `main` use `?` too. If it returns `Err`, the program prints the error and exits with a non-zero status code.
- For larger projects the `thiserror` crate writes the `Display`, `source` and `From` code for you from attributes, and `anyhow` is a convenient error type for applications. It is useful to write the plain version once to see what they generate.""")

# 2 ---------------------------------------------------------------------------------------------
ex("How do I overload operators like + and * for my own type in Rust, and make it work with sum() and sorting?",
   "Implement the traits from `std::ops` for `+`, `-`, `*` and so on, `Display` for printing, and `Sum` for `.sum()`. Derive the comparison traits so that sorting and `max()` work. The example is a small `Money` type that stores whole cents.",
   r'''
use std::fmt;
use std::iter::Sum;
use std::ops::{Add, AddAssign, Mul, Neg, Sub};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Default)]
struct Money {
    cents: i64,
}

impl Money {
    fn new(dollars: i64, cents: i64) -> Money {
        Money { cents: dollars * 100 + cents }
    }
}

impl fmt::Display for Money {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        let sign = if self.cents < 0 { "-" } else { "" };
        let abs = self.cents.abs();
        write!(f, "{}${}.{:02}", sign, abs / 100, abs % 100)
    }
}

impl Add for Money {
    type Output = Money;
    fn add(self, other: Money) -> Money {
        Money { cents: self.cents + other.cents }
    }
}

impl Sub for Money {
    type Output = Money;
    fn sub(self, other: Money) -> Money {
        Money { cents: self.cents - other.cents }
    }
}

impl Neg for Money {
    type Output = Money;
    fn neg(self) -> Money {
        Money { cents: -self.cents }
    }
}

impl Mul<i64> for Money {
    type Output = Money;
    fn mul(self, times: i64) -> Money {
        Money { cents: self.cents * times }
    }
}

impl AddAssign for Money {
    fn add_assign(&mut self, other: Money) {
        self.cents += other.cents;
    }
}

impl Sum for Money {
    fn sum<I: Iterator<Item = Money>>(iter: I) -> Money {
        iter.fold(Money::default(), |a, b| a + b)
    }
}

impl<'a> Sum<&'a Money> for Money {
    fn sum<I: Iterator<Item = &'a Money>>(iter: I) -> Money {
        iter.fold(Money::default(), |a, b| a + *b)
    }
}

fn main() {
    let price = Money::new(12, 50);
    let items = vec![price, Money::new(3, 99), Money::new(0, 5)];

    let total: Money = items.iter().sum();
    println!("total          = {}", total);
    println!("3 x price      = {}", price * 3);
    println!("change from 50 = {}", Money::new(50, 0) - total);
    println!("negated total  = {}", -total);

    let mut running = Money::default();
    for m in &items {
        running += *m;
        println!("running total = {}", running);
    }

    println!("largest        = {}", items.iter().max().unwrap());
    let mut sorted = items.clone();
    sorted.sort();
    let text: Vec<String> = sorted.iter().map(|m| m.to_string()).collect();
    println!("sorted         = {}", text.join(" < "));
    println!("debug          = {:?}", price);
}
''',
   """
What to notice:
- `type Output = Money;` says what `a + b` produces. It could be a different type, as in `Mul<i64> for Money`, where a `Money` times a number gives `Money`. You can implement several `Mul` variants for different right-hand types.
- The operators take `self` **by value**. `Money` is `Copy`, so `a + b` does not consume the operands. For a type that is not `Copy`, implement the traits for references too (`impl Add for &Matrix`) to avoid forced clones.
- `AddAssign` is a separate trait for `+=`. It does not come automatically with `Add`.
- `Sum` is what makes `iter.sum::<Money>()` work. Implementing it both for `Money` and for `&Money` lets you sum `into_iter()` and `iter()`.
- `#[derive(PartialOrd, Ord)]` on a struct compares the fields **in the order they are declared**. With a single `cents` field, it is exactly what you want. With several fields, think about the order.
- Do not overload an operator for something that is not an obvious meaning of that operator. `Money + Money` is natural. `user + group` is not, and a named method would be clearer.""")

# 3 ---------------------------------------------------------------------------------------------
ex("When do I need Rc<RefCell<T>> in Rust, and how do I avoid reference cycles with Weak?",
   "`Rc<T>` gives **shared ownership** within one thread, and `RefCell<T>` moves the borrow checking from compile time to run time so you can change data behind a shared reference. Together they are for graphs and trees where several owners must exist. `Weak<T>` is a non-owning pointer, used for the back link (a child's reference to its parent) so that no cycle keeps the memory alive forever.",
   r'''
use std::cell::RefCell;
use std::rc::{Rc, Weak};

struct Account {
    balance: i64,
    log: Vec<String>,
}

struct Node {
    name: String,
    parent: RefCell<Weak<Node>>,
    children: RefCell<Vec<Rc<Node>>>,
}

fn path(node: &Rc<Node>) -> String {
    match node.parent.borrow().upgrade() {
        Some(parent) => format!("{}/{}", path(&parent), node.name),
        None => node.name.clone(),
    }
}

fn main() {
    // 1) Shared, changeable data.
    let shared = Rc::new(RefCell::new(Account { balance: 0, log: vec![] }));
    let a = Rc::clone(&shared);
    let b = Rc::clone(&shared);
    println!("owners: {}", Rc::strong_count(&shared));

    a.borrow_mut().balance += 100;
    b.borrow_mut().log.push("deposit made through b".to_string());
    b.borrow_mut().balance -= 30;

    {
        let r1 = shared.borrow();
        let r2 = shared.borrow(); // many readers at the same time are fine
        println!("two readers: {} and {}, log = {:?}", r1.balance, r2.balance, r1.log);
        match shared.try_borrow_mut() {
            Ok(_) => println!("writer got in (unexpected)"),
            Err(e) => println!("writer while readers exist: {}", e),
        }
    }
    println!("writer after readers are gone: {}", shared.try_borrow_mut().is_ok());

    drop(a);
    println!("owners after drop(a): {}", Rc::strong_count(&shared));

    // 2) A tree whose children can find their parent without a cycle.
    let root = Rc::new(Node { name: "root".into(), parent: RefCell::new(Weak::new()), children: RefCell::new(vec![]) });
    let docs = Rc::new(Node { name: "docs".into(), parent: RefCell::new(Weak::new()), children: RefCell::new(vec![]) });
    let readme = Rc::new(Node { name: "readme.md".into(), parent: RefCell::new(Weak::new()), children: RefCell::new(vec![]) });

    *docs.parent.borrow_mut() = Rc::downgrade(&root);
    root.children.borrow_mut().push(Rc::clone(&docs));
    *readme.parent.borrow_mut() = Rc::downgrade(&docs);
    docs.children.borrow_mut().push(Rc::clone(&readme));

    println!("path: {}", path(&readme));
    println!("docs: strong = {}, weak = {}", Rc::strong_count(&docs), Rc::weak_count(&docs));
    println!("root: strong = {}, weak = {}", Rc::strong_count(&root), Rc::weak_count(&root));

    drop(root);
    println!("parent of docs after dropping root: {:?}", docs.parent.borrow().upgrade().map(|p| p.name.clone()));
}
''',
   """
How to read it:
- `Rc::clone(&x)` does not copy the data. It increases a counter, and the data is freed when the last `Rc` is dropped. `Rc::strong_count` shows that counter.
- `RefCell` enforces the same rule as `&`/`&mut` (many readers **or** one writer), but while the program runs. A violation is a **panic** with `borrow_mut()`, or an `Err` with `try_borrow_mut()`, as in the demo. So keep borrows short, never hold a `borrow()` while calling code that may call `borrow_mut()` on the same cell.
- A parent owns its children through `Rc`, and each child points back through `Weak`. If both directions were `Rc`, the counts could never reach zero, and the memory would **leak**. `upgrade()` returns `Some(Rc)` while the target still exists and `None` after it has been freed, as the last line shows, because `root` was dropped.
- `Rc` is **not thread safe**. For several threads use `Arc<Mutex<T>>` or `Arc<RwLock<T>>`.
- Reach for these only when the design really needs shared ownership. Often a simpler structure is enough: indices into a `Vec`, passing `&mut`, or giving a single owner the whole data.""")

# 4 ---------------------------------------------------------------------------------------------
_lt_fail = r'''
fn longest_of<'a>(a: &'a str, b: &'a str) -> &'a str {
    if a.len() >= b.len() { a } else { b }
}

fn main() {
    let result;
    {
        let short_lived = String::from("temporary text");
        result = longest_of(&short_lived, "x");
    }
    println!("{}", result);
}
'''
_lt_msg = rust_error(_lt_fail)
ex("What are lifetimes in Rust? Explain 'a with an example that works and one that the compiler rejects.",
   f"""
A lifetime is the span of the program during which a reference is valid. The compiler checks that no reference can **outlive** the data it points to, which is how Rust prevents dangling pointers without a garbage collector. Most of the time you never write lifetimes because the compiler infers them. You write `'a` only when a function or struct holds references and the compiler cannot tell how they relate.

First, the rejected program. The function returns a reference that may point into either argument, and `result` is used after one of the arguments has been dropped:

{F}rust,compile_fail
{_lt_fail.strip()}
{F}

The compiler says:

{F}
{_lt_msg}
{F}

`longest_of<'a>(a: &'a str, b: &'a str) -> &'a str` means: the result lives no longer than **both** inputs. The string `short_lived` ends at the closing brace of the inner block, so a result that may refer to it cannot be used after that. The fix is to keep the data alive as long as the result is needed, for example by declaring `short_lived` in the outer scope.

Now a working example: a struct that holds a reference into the text, which is the typical case for parsers.""",
   r'''
struct Tokens<'a> {
    rest: &'a str,
}

impl<'a> Tokens<'a> {
    fn new(text: &'a str) -> Self {
        Tokens { rest: text }
    }
}

impl<'a> Iterator for Tokens<'a> {
    type Item = &'a str; // the tokens borrow from the original text, nothing is copied

    fn next(&mut self) -> Option<&'a str> {
        let s = self.rest.trim_start();
        let first = s.chars().next()?;
        let len = if first.is_ascii_digit() {
            s.find(|c: char| !c.is_ascii_digit()).unwrap_or(s.len())
        } else if first.is_alphabetic() {
            s.find(|c: char| !c.is_alphanumeric()).unwrap_or(s.len())
        } else {
            first.len_utf8()
        };
        let (token, rest) = s.split_at(len);
        self.rest = rest;
        Some(token)
    }
}

fn longest_of<'a>(a: &'a str, b: &'a str) -> &'a str {
    if a.len() >= b.len() { a } else { b }
}

fn main() {
    let text = String::from("let x1 = 42+foo(7);");
    let tokens: Vec<&str> = Tokens::new(&text).collect();
    println!("{:?}", tokens);

    let longest = tokens.iter().copied().fold("", |best, t| longest_of(best, t));
    println!("longest token: {}", longest);
}
''',
   """
Reading the lifetimes:
- `struct Tokens<'a>` says "a `Tokens` cannot live longer than the text it borrows". `impl<'a> Iterator for Tokens<'a>` and `type Item = &'a str` say that every token is a slice of that same text, so a token stays valid even after the iterator itself is gone, as long as `text` lives.
- Returning slices instead of new `String`s makes the tokenizer allocation free.
- **Lifetime elision.** The compiler fills in the obvious cases: `fn first_word(s: &str) -> &str` is read as "the output has the lifetime of the single input". You must write `'a` when there are several reference inputs and the output could come from either (`longest_of`), and in struct definitions.
- `'static` means "valid for the whole program", for example string literals. Do not use `T: 'static` or `&'static` to silence an error without understanding it. Usually the data has to live longer, or you should return an owned `String`.
- When lifetimes get hard, the usual cure is to **own** the data (`String`, `Vec`) in the struct or to clone it once. It costs a little performance and removes a whole class of complexity.""", tests=False) if False else None

# The example above mixes a rejected and a working program, so it is assembled by hand:
_lt_ok = r'''
struct Tokens<'a> {
    rest: &'a str,
}

impl<'a> Tokens<'a> {
    fn new(text: &'a str) -> Self {
        Tokens { rest: text }
    }
}

impl<'a> Iterator for Tokens<'a> {
    type Item = &'a str; // the tokens borrow from the original text, nothing is copied

    fn next(&mut self) -> Option<&'a str> {
        let s = self.rest.trim_start();
        let first = s.chars().next()?;
        let len = if first.is_ascii_digit() {
            s.find(|c: char| !c.is_ascii_digit()).unwrap_or(s.len())
        } else if first.is_alphabetic() {
            s.find(|c: char| !c.is_alphanumeric()).unwrap_or(s.len())
        } else {
            first.len_utf8()
        };
        let (token, rest) = s.split_at(len);
        self.rest = rest;
        Some(token)
    }
}

fn longest_of<'a>(a: &'a str, b: &'a str) -> &'a str {
    if a.len() >= b.len() { a } else { b }
}

fn main() {
    let text = String::from("let x1 = 42+foo(7);");
    let tokens: Vec<&str> = Tokens::new(&text).collect();
    println!("{:?}", tokens);

    let longest = tokens.iter().copied().fold("", |best, t| longest_of(best, t));
    println!("longest token: {}", longest);
}
'''
_lt_out = run_rust(_lt_ok)
EXAMPLES.append((
    "What are lifetimes in Rust? Explain 'a with an example that works and one that the compiler rejects.",
    f"""
A lifetime is the span of the program during which a reference is valid. The compiler checks that no reference can **outlive** the data it points to, which is how Rust prevents dangling pointers without a garbage collector. Most of the time you never write lifetimes because the compiler infers them. You write `'a` only when a function or struct holds references and the compiler cannot tell how they relate.

First, the rejected program. The function returns a reference that may point into either argument, and `result` is used after one of the arguments has been dropped:

{F}rust,compile_fail
{_lt_fail.strip()}
{F}

The compiler says:

{F}
{_lt_msg}
{F}

`longest_of<'a>(a: &'a str, b: &'a str) -> &'a str` means: the result lives no longer than **both** inputs. The string `short_lived` ends at the closing brace of the inner block, so a result that may refer to it cannot be used after that. The fix is to keep the data alive as long as the result is needed, for example by declaring `short_lived` in the outer scope.

Now a working example: a struct that holds a reference into the text, which is the typical case for parsers.

{F}rust
{_lt_ok.strip()}
{F}

Output:

{F}
{_lt_out}
{F}

Reading the lifetimes:
- `struct Tokens<'a>` says "a `Tokens` cannot live longer than the text it borrows". `impl<'a> Iterator for Tokens<'a>` and `type Item = &'a str` say that every token is a slice of that same text, so a token stays valid even after the iterator itself is gone, as long as `text` lives.
- Returning slices instead of new `String`s makes the tokenizer allocation free.
- **Lifetime elision.** The compiler fills in the obvious cases: `fn first_word(s: &str) -> &str` is read as "the output has the lifetime of the single input". You must write `'a` when there are several reference inputs and the output could come from either (`longest_of`), and in struct definitions.
- `'static` means "valid for the whole program", for example string literals. Do not add `'static` to silence an error without understanding it. Usually the data has to live longer, or you should return an owned `String`.
- When lifetimes get hard, the usual cure is to **own** the data (`String`, `Vec`) in the struct or to clone it once. It costs a little performance and removes a whole class of complexity.""".strip()))

# 5 ---------------------------------------------------------------------------------------------
ex("How do closures work in Rust? Explain Fn, FnMut and FnOnce and show how to return a closure or store several of them.",
   "A closure is an anonymous function that can capture variables from where it was written. The compiler gives each closure one of three traits depending on **what it does with the captured values**: `Fn` only reads them, `FnMut` changes them, and `FnOnce` consumes them, so it can be called only once.",
   r'''
fn make_adder(n: i32) -> impl Fn(i32) -> i32 {
    move |x| x + n // `move` copies n into the closure, so it can outlive this function
}

fn make_counter() -> impl FnMut() -> u32 {
    let mut count = 0;
    move || {
        count += 1; // the closure owns and changes its own `count`
        count
    }
}

fn apply_twice<F: Fn(i32) -> i32>(f: F, x: i32) -> i32 {
    f(f(x))
}

fn run_once<F: FnOnce() -> String>(f: F) -> String {
    f()
}

fn main() {
    let add5 = make_adder(5);
    println!("add5(10) = {}", add5(10));
    println!("apply_twice(&add5, 1) = {}", apply_twice(&add5, 1));

    let mut counter = make_counter();
    println!("counter: {} {} {}", counter(), counter(), counter());

    let name = String::from("Ferris");
    let greet = move || format!("hello, {}", name); // takes ownership of `name`
    println!("{}", run_once(greet));

    // Several different closures in one collection need a trait object: Box<dyn Fn>.
    let validators: Vec<(&str, Box<dyn Fn(&str) -> bool>)> = vec![
        ("not empty", Box::new(|s| !s.is_empty())),
        ("at most 8 chars", Box::new(|s| s.chars().count() <= 8)),
        ("letters only", Box::new(|s| s.chars().all(|c| c.is_alphabetic()))),
    ];

    for input in ["rustacean", "", "ok", "r2d2"] {
        let failed: Vec<&str> = validators
            .iter()
            .filter(|(_, check)| !check(input))
            .map(|(name, _)| *name)
            .collect();
        if failed.is_empty() {
            println!("{:?}: valid", input);
        } else {
            println!("{:?}: fails {}", input, failed.join(", "));
        }
    }
}
''',
   """
Summary:
- Every closure has its own anonymous type, so two closures with identical code still have different types. That is why a function returns `impl Fn(...)` (one specific closure, no allocation) and why a `Vec` of mixed closures needs `Box<dyn Fn(...)>`.
- Hierarchy: every `Fn` is also `FnMut`, and every `FnMut` is also `FnOnce`. In a function **parameter** ask for the weakest trait that you need: `FnOnce` accepts everything, `Fn` accepts only closures that do not change their state. In the demo, `apply_twice` calls `f` twice, so it needs `Fn` (or `FnMut`).
- `move` makes the closure take ownership of (or copy) what it uses. It is required when the closure outlives the scope that created it, as in `make_adder` and when you give a closure to `thread::spawn`.
- `apply_twice(&add5, 1)` works because a reference to an `Fn` closure is itself `Fn`, so `add5` is still usable afterwards.
- Calling a `FnMut` closure needs `let mut counter`, because calling it changes its captured state.
- `"rustacean"` has 9 letters, so it fails only the length rule. `"r2d2"` fails only the letters rule. The empty string fails only `not empty`: it counts as 'letters only' because `all` on an empty sequence is `true`, a classic surprise to remember. Each rule is checked independently of the others.""")

# 6 ---------------------------------------------------------------------------------------------
ex("How do I build a worker pool with threads and channels in Rust (no external crates)?",
   "Create one channel for jobs and one for results. The workers share the receiving end of the job channel through `Arc<Mutex<Receiver>>`. When the sender is dropped, `recv()` returns an error and each worker leaves its loop, so no special stop message is needed.",
   r'''
use std::sync::{mpsc, Arc, Mutex};
use std::thread;

fn is_prime(n: u64) -> bool {
    if n < 2 {
        return false;
    }
    let mut i = 2;
    while i * i <= n {
        if n % i == 0 {
            return false;
        }
        i += 1;
    }
    true
}

fn main() {
    let numbers: Vec<u64> = vec![97, 100, 7919, 1_000_003, 1_000_004, 15, 2, 561];

    let (job_tx, job_rx) = mpsc::channel::<(usize, u64)>();
    let job_rx = Arc::new(Mutex::new(job_rx));
    let (result_tx, result_rx) = mpsc::channel::<(usize, u64, bool)>();

    let mut workers = Vec::new();
    for _ in 0..3 {
        let jobs = Arc::clone(&job_rx);
        let results = result_tx.clone();
        workers.push(thread::spawn(move || loop {
            // The lock is released at the end of this statement, so the other workers can fetch jobs while we compute.
            let job = jobs.lock().unwrap().recv();
            match job {
                Ok((index, n)) => results.send((index, n, is_prime(n))).unwrap(),
                Err(_) => break, // the sender is gone and the queue is empty: time to stop
            }
        }));
    }
    drop(result_tx); // only the workers' clones remain, so the result channel closes when they finish

    for (index, n) in numbers.iter().enumerate() {
        job_tx.send((index, *n)).unwrap();
    }
    drop(job_tx); // closing the job channel tells the workers to stop

    let mut results: Vec<(usize, u64, bool)> = result_rx.iter().collect();
    results.sort(); // the order in which results arrive changes from run to run, so sort by the job index
    for (_, n, prime) in &results {
        println!("{:>8} is {}", n, if *prime { "prime" } else { "not prime" });
    }

    for worker in workers {
        worker.join().unwrap();
    }
    println!("{} results from 3 workers", results.len());
}
''',
   """
Why it is written this way:
- `mpsc` means multiple producers, single consumer. Only one receiver exists, so to let three threads take jobs from it, it is wrapped in `Arc<Mutex<...>>`. `Arc` is the thread-safe `Rc`, and `Mutex` makes the workers take turns when they call `recv()`.
- `jobs.lock().unwrap().recv()` is a single statement, and the lock guard is a temporary that is dropped at the semicolon. If you wrote `while let Ok(job) = jobs.lock().unwrap().recv() { ... }`, the guard would live for the whole loop body and the workers would run one at a time.
- **Shutting down.** `drop(job_tx)` closes the job channel. Once the queue is empty, `recv()` returns `Err` and each worker breaks out of its loop. Dropping the original `result_tx` matters too. The result channel only ends when **every** sender is gone, and the main thread's copy would keep `result_rx.iter()` waiting forever.
- Output order depends on thread timing, which is why the results carry their index and are sorted. Never assume that threads finish in the order that they started.
- `561` is a good test value: it is not prime, but it is the smallest Carmichael number, which fools some quick primality tests. Trial division handles it correctly.
- For real programs the `rayon` crate gives you `numbers.par_iter().map(is_prime)` with a ready pool, and `std::thread::scope` lets threads borrow local data without `Arc`.""")

# 7 ---------------------------------------------------------------------------------------------
ex("How do I write unit tests in Rust? Show #[cfg(test)], should_panic and a test that returns Result.",
   "Tests live next to the code in a `mod tests` marked `#[cfg(test)]`, so they are compiled only when testing. With Cargo you run them with `cargo test`. Here the same file is built with `rustc --test`, which is what Cargo does underneath, so that the output below is real.",
   r'''
/// Turns a title into a URL slug: lowercase ASCII letters and digits separated by single dashes.
pub fn slugify(title: &str) -> String {
    let mut slug = String::new();
    let mut pending_dash = false;
    for c in title.chars() {
        if c.is_ascii_alphanumeric() {
            if pending_dash && !slug.is_empty() {
                slug.push('-');
            }
            pending_dash = false;
            slug.push(c.to_ascii_lowercase());
        } else {
            pending_dash = true;
        }
    }
    slug
}

/// Splits text into lines of at most `width` characters, breaking only at spaces.
pub fn wrap(text: &str, width: usize) -> Result<Vec<String>, String> {
    if width == 0 {
        return Err("width must be at least 1".to_string());
    }
    let mut lines = Vec::new();
    let mut current = String::new();
    for word in text.split_whitespace() {
        if word.chars().count() > width {
            return Err(format!("the word '{}' is longer than {}", word, width));
        }
        let needed = if current.is_empty() { 0 } else { current.chars().count() + 1 } + word.chars().count();
        if needed > width {
            lines.push(std::mem::take(&mut current));
        }
        if !current.is_empty() {
            current.push(' ');
        }
        current.push_str(word);
    }
    if !current.is_empty() {
        lines.push(current);
    }
    Ok(lines)
}

fn main() {
    println!("{}", slugify("Hello, World! 2026"));
    println!("{:?}", wrap("the quick brown fox jumps", 10));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn slugify_basic() {
        assert_eq!(slugify("Hello, World! 2026"), "hello-world-2026");
    }

    #[test]
    fn slugify_trims_and_collapses_separators() {
        assert_eq!(slugify("  --Rust   &   Cargo--  "), "rust-cargo");
        assert_eq!(slugify("!!!"), "");
    }

    #[test]
    fn wrap_breaks_at_spaces() {
        let lines = wrap("the quick brown fox jumps", 10).unwrap();
        assert_eq!(lines, vec!["the quick", "brown fox", "jumps"]);
        assert!(lines.iter().all(|l| l.chars().count() <= 10));
    }

    // A test may return Result, so that `?` can be used inside it.
    #[test]
    fn wrap_errors_are_reported() -> Result<(), String> {
        assert_eq!(wrap("abc", 0), Err("width must be at least 1".to_string()));
        let err = wrap("supercalifragilistic", 5).unwrap_err();
        assert!(err.contains("longer than 5"), "unexpected message: {}", err);
        let lines = wrap("", 5)?;
        assert!(lines.is_empty());
        Ok(())
    }

    #[test]
    #[should_panic(expected = "width must be at least 1")]
    fn unwrap_on_zero_width_panics() {
        wrap("anything", 0).unwrap();
    }
}
''',
   """
Notes:
- `use super::*;` brings the functions of the parent module into the test module. `#[cfg(test)]` means the module is not compiled into your normal build, so tests cost nothing in the release binary.
- `assert_eq!(left, right)` prints both values when it fails, so it is better than `assert!(left == right)`. Add a message as the last arguments (`assert!(cond, "unexpected message: {}", err)`) when the failure needs context.
- A test **fails when it panics**. `#[should_panic(expected = "...")]` turns that around: it passes only if the panic message contains the text, which prevents the test from passing because of an unrelated panic.
- A test returning `Result<(), E>` fails when it returns `Err`, and lets you use `?` instead of `unwrap()` chains.
- Tests run in parallel on several threads and in no fixed order by default, so they must not depend on each other or on shared files without care. `cargo test -- --test-threads=1` runs them one by one, which was used here to get a stable listing. `cargo test slugify` runs only tests whose name contains `slugify`, and `cargo test -- --nocapture` shows `println!` output of passing tests.
- Put tests that use only the **public** API of a library in the `tests/` folder (integration tests). Examples in `///` doc comments are tested as well (doc tests).""",
   tests=True)

# 8 ---------------------------------------------------------------------------------------------
ex("How do I model a state machine in Rust with enums so that invalid transitions are impossible to ignore?",
   "Make the states and the events enums, and put all rules into one `match` on the pair `(state, event)`. Every legal transition gets an arm, and one last arm returns an error for everything else. With `try_fold` a whole list of events can be applied until the first error.",
   r'''
#[derive(Debug, Clone, Copy, PartialEq)]
enum Status {
    Created,
    Paid,
    Shipped,
    Delivered,
    Cancelled,
}

#[derive(Debug, Clone, Copy)]
enum Event {
    Pay,
    Ship,
    Deliver,
    Cancel,
}

fn next(status: Status, event: Event) -> Result<Status, String> {
    use Status::*;
    match (status, event) {
        (Created, Event::Pay) => Ok(Paid),
        (Paid, Event::Ship) => Ok(Shipped),
        (Shipped, Event::Deliver) => Ok(Delivered),
        (Created | Paid, Event::Cancel) => Ok(Cancelled),
        (s, e) => Err(format!("cannot {:?} an order that is {:?}", e, s)),
    }
}

fn run(events: &[Event]) -> Result<Status, String> {
    events.iter().copied().try_fold(Status::Created, next)
}

fn main() {
    let scenarios: Vec<(&str, Vec<Event>)> = vec![
        ("normal order", vec![Event::Pay, Event::Ship, Event::Deliver]),
        ("cancel before shipping", vec![Event::Pay, Event::Cancel]),
        ("ship without paying", vec![Event::Ship]),
        ("cancel after shipping", vec![Event::Pay, Event::Ship, Event::Cancel]),
        ("nothing happens", vec![]),
    ];
    for (name, events) in &scenarios {
        match run(events) {
            Ok(status) => println!("{:<24} -> {:?}", name, status),
            Err(e) => println!("{:<24} -> error: {}", name, e),
        }
    }

    // Terminal states: a handy helper that the compiler keeps complete.
    let all = [Status::Created, Status::Paid, Status::Shipped, Status::Delivered, Status::Cancelled];
    let terminal: Vec<Status> = all
        .into_iter()
        .filter(|s| matches!(s, Status::Delivered | Status::Cancelled))
        .collect();
    println!("terminal states: {:?}", terminal);
}
''',
   """
Why this is a good shape:
- A `Status` value can only be one of the listed states, so "status = 'shiped'" typos and impossible values cannot exist, unlike a string or an integer field.
- All business rules are in **one** function. To allow cancelling a shipped order you change one line, and the tests for that line are easy to find.
- The final arm `(s, e) => Err(...)` is a deliberate catch-all, so unknown combinations are rejected by default. If you list every allowed pair and keep the catch-all last, a newly added `Event` is refused until you decide what it does. If you prefer the compiler to force a decision for every pair, remove the catch-all and write out the pairs.
- `try_fold(start, next)` calls `next` for each event, passing the status along, and stops at the first `Err`, which becomes the result. That is `?` for a whole iterator.
- `(Created | Paid, Event::Cancel)` is an or-pattern inside a tuple pattern, so two states share one arm.
- To keep data per state (for example the tracking number only when `Shipped`), put it in the variant: `Shipped { tracking: String }`. Then a `Created` order simply has no tracking number field to forget to initialise.""")

# 9 ---------------------------------------------------------------------------------------------
ex("How do I format a table in the terminal with Rust's format! alignment, width and precision options?",
   "The format spec after the colon is `{:[fill][align][sign][#][0][width][.precision][type]}`. `<`, `^` and `>` align left, centre and right. The width can be a number or a name that you pass in (`{:<width$}`), which is how you align columns whose width depends on the data.",
   r'''
fn main() {
    let rows = [("Widget", 4, 3.5), ("Gadget (large)", 12, 19.999), ("Thing", 100, 0.5)];

    // Column width from the data: the longest name, but at least the header.
    let width = rows.iter().map(|r| r.0.chars().count()).max().unwrap().max("Item".len());

    println!("{:<width$} | {:>5} | {:>9}", "Item", "Qty", "Price", width = width);
    println!("{}", "-".repeat(width + 3 + 5 + 3 + 9));
    let mut total = 0.0;
    for (name, qty, price) in rows {
        println!("{:<width$} | {:>5} | {:>9.2}", name, qty, price, width = width);
        total += qty as f64 * price;
    }
    println!("{:<width$} | {:>5} | {:>9.2}", "Total", "", total, width = width);

    println!();
    println!("[{:^11}]   centred", "mid");
    println!("[{:*^11}]   centred with a fill character", "mid");
    println!("[{:>+8.1}]   sign and one decimal", 3.14159);
    println!("[{:08.3}]   zero padded", -2.5);
    println!("[{:#x}] [{:#010b}] [{:o}]   hex, binary, octal", 255, 5, 64);
    println!("[{:e}]   scientific", 1234.5);
    println!("[{0}-{0}-{1}]   positional arguments", "a", "b");
    let pct = 0.4567;
    println!("[{:.1}%]   inline variable and precision: {pct:.3}", pct * 100.0);
    println!("[{:5}] [{:<5}] [{:>5}]   text pads left-aligned by default, numbers right-aligned", "ab", "ab", "ab");
    println!("[{:5}] [{:<5}]", 42, 42);
}
''',
   """
Quick reference from the output:
- `{:<width$}` takes the width from the named argument `width = width`. A shorter form works when a variable of that name is in scope: `{:<width$}` finds `width` by itself in Rust 2021 (the explicit `width = width` is shown here for clarity). `{:1$}` uses the argument at position 1 as the width.
- `.2` after a float is the number of decimals (rounded: 19.999 becomes `20.00`). After a string it **truncates** to that many characters.
- `0` before the width pads numbers with zeros after the sign (`-002.500`). `+` always prints the sign. `#` adds the prefix for `x`, `b` and `o`.
- Without an alignment, **text is left-aligned and numbers are right-aligned**, as the last two lines show.
- Width counts characters (`char`s), not display columns. Wide characters such as emoji or Chinese characters can still misalign a table. For serious terminal tables use a crate such as `comfy-table` or `tabled`.
- `{:?}` is the debug format, `{:#?}` the pretty multi-line debug format, and `{{` and `}}` print literal braces.""")

# 10 --------------------------------------------------------------------------------------------
ex("Implement a generic LRU cache in Rust using only the standard library.",
   "A least-recently-used cache keeps at most `capacity` entries and throws away the one that was used longest ago. The simplest version uses a `HashMap` for the values and a `VecDeque` for the usage order. It is generic over the key and value types with trait bounds on the key.",
   r'''
use std::collections::{HashMap, VecDeque};
use std::hash::Hash;

struct LruCache<K, V> {
    capacity: usize,
    map: HashMap<K, V>,
    order: VecDeque<K>, // front = least recently used, back = most recently used
}

impl<K: Hash + Eq + Clone, V> LruCache<K, V> {
    fn new(capacity: usize) -> Self {
        assert!(capacity > 0, "capacity must be at least 1");
        LruCache { capacity, map: HashMap::new(), order: VecDeque::new() }
    }

    fn touch(&mut self, key: &K) {
        if let Some(pos) = self.order.iter().position(|k| k == key) {
            self.order.remove(pos);
        }
        self.order.push_back(key.clone());
    }

    fn get(&mut self, key: &K) -> Option<&V> {
        if self.map.contains_key(key) {
            self.touch(key);
            self.map.get(key)
        } else {
            None
        }
    }

    /// Inserts or replaces a value and returns the key that had to be evicted, if any.
    fn put(&mut self, key: K, value: V) -> Option<K> {
        let mut evicted = None;
        if !self.map.contains_key(&key) && self.map.len() == self.capacity {
            if let Some(oldest) = self.order.pop_front() {
                self.map.remove(&oldest);
                evicted = Some(oldest);
            }
        }
        self.touch(&key);
        self.map.insert(key, value);
        evicted
    }

    fn keys_oldest_first(&self) -> Vec<&K> {
        self.order.iter().collect()
    }
}

fn main() {
    let mut cache: LruCache<&str, u32> = LruCache::new(3);
    for (k, v) in [("a", 1), ("b", 2), ("c", 3)] {
        cache.put(k, v);
    }
    println!("order: {:?}", cache.keys_oldest_first());

    println!("get a = {:?}", cache.get(&"a"));
    println!("order: {:?}", cache.keys_oldest_first());

    println!("put d, evicted: {:?}", cache.put("d", 4));
    println!("get b = {:?}", cache.get(&"b"));

    println!("replace c, evicted: {:?}", cache.put("c", 30));
    println!("order: {:?}", cache.keys_oldest_first());
    println!("get c = {:?}, get a = {:?}", cache.get(&"c").copied(), cache.get(&"a").copied());
}
''',
   """
Walkthrough and limits:
- `K: Hash + Eq + Clone` is what `HashMap` requires of keys (`Hash + Eq`), plus `Clone` because the key is stored twice, in the map and in the order queue. `V` needs no bounds at all.
- `get` takes `&mut self`, because reading marks the entry as recently used. That is the nature of a cache, and it is why a plain `&self` getter cannot do the job.
- Putting a key that already exists replaces its value and does not evict anything (see the `replace c` line). Only a **new** key in a full cache evicts the oldest one.
- `touch` is `O(n)` because it searches the queue for the key. For a few hundred entries that is fine. A production cache gets `O(1)` by storing the entries in a doubly linked list with a map from key to node (in Rust usually with indices into a `Vec`, as the `lru` crate does).
- The struct is not thread safe. Share it between threads as `Arc<Mutex<LruCache<K, V>>>`.
- Choose a cache when computing or fetching the value is expensive and the same keys come back often. Always limit its size, otherwise it is a memory leak with a nice name.""")


def block(q, a):
    return f"@@@ USER\n{q}\n@@@ ASSISTANT\n{a}\n@@@ END\n\n"


OUT.write_text("".join(block(q, a) for q, a in EXAMPLES), encoding="utf-8")
print("wrote", OUT, len(EXAMPLES), "examples", OUT.stat().st_size, "bytes")

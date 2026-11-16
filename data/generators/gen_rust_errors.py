"""Rust compiler-error repair examples.

Each entry: a program that fails with a known error code, the fixed program, and an explanation
of exactly what changed and why. `python data/verify_rust.py` compiles every entry with rustc
to prove that the broken code really fails with that code and the fixed code really compiles.
"""

ENTRIES = [
    {
        "code": "E0382",
        "msg": "borrow of moved value: `s`",
        "title": "use of a moved value",
        "bad": '''fn main() {
    let s = String::from("hello");
    let t = s;
    println!("{} {}", s, t);
}''',
        "fixed": '''fn main() {
    let s = String::from("hello");
    let t = s.clone();
    println!("{} {}", s, t);
}''',
        "why": "`let t = s;` moves the String out of `s`. A String owns heap memory and can only have one owner, so after the move `s` is no longer valid and the `println!` that uses it is rejected.",
        "changes": [
            "`let t = s;` became `let t = s.clone();`. `clone` makes an independent copy, so `s` keeps its value.",
            "If you do not need two copies, borrow instead: `let t = &s;`. That costs nothing and keeps `s` valid.",
        ],
    },
    {
        "code": "E0499",
        "msg": "cannot borrow `v` as mutable more than once at a time",
        "title": "two mutable borrows alive at the same time",
        "bad": '''fn main() {
    let mut v = vec![1, 2, 3];
    let a = &mut v;
    let b = &mut v;
    a.push(4);
    b.push(5);
}''',
        "fixed": '''fn main() {
    let mut v = vec![1, 2, 3];
    let a = &mut v;
    a.push(4);
    let b = &mut v;
    b.push(5);
    println!("{:?}", v);
}''',
        "why": "Rust allows only one mutable reference to a value at a time, so two writers can never change the data simultaneously. In the broken code both `a` and `b` are still in use after the second borrow is created.",
        "changes": [
            "I finished using `a` (`a.push(4);`) before creating `b`. The compiler sees that `a` is no longer used, so the second mutable borrow is allowed.",
            "I added a final `println!` that uses `v` itself, which works because both borrows have ended.",
        ],
    },
    {
        "code": "E0502",
        "msg": "cannot borrow `v` as mutable because it is also borrowed as immutable",
        "title": "mutating a vector while holding a reference into it",
        "bad": '''fn main() {
    let mut v = vec![1, 2, 3];
    let first = &v[0];
    v.push(4);
    println!("{}", first);
}''',
        "fixed": '''fn main() {
    let mut v = vec![1, 2, 3];
    let first = v[0];
    v.push(4);
    println!("{}", first);
}''',
        "why": "`&v[0]` points into the vector's memory. `v.push(4)` may need to reallocate the vector, which would leave `first` pointing at freed memory. Rust refuses to compile that situation.",
        "changes": [
            "`let first = &v[0];` became `let first = v[0];`. For `i32` this copies the number, so `first` no longer borrows the vector.",
            "For a non-Copy element such as `String`, use `v[0].clone()` or move the `push` after the last use of the reference.",
        ],
    },
    {
        "code": "E0308",
        "msg": "mismatched types",
        "title": "a function that returns nothing because of a stray semicolon",
        "bad": '''fn double(x: i32) -> i32 {
    x * 2;
}

fn main() {
    println!("{}", double(4));
}''',
        "fixed": '''fn double(x: i32) -> i32 {
    x * 2
}

fn main() {
    println!("{}", double(4));
}''',
        "why": "In Rust the last expression of a block is its value only when it has no semicolon. `x * 2;` turns the expression into a statement, so the function body evaluates to `()` (nothing), but the signature promises an `i32`.",
        "changes": [
            "I removed the semicolon after `x * 2`, so the value is returned.",
            "Alternatively you could write `return x * 2;`, but the idiomatic style is to leave off the semicolon on the last line.",
        ],
    },
    {
        "code": "E0384",
        "msg": "cannot assign twice to immutable variable `count`",
        "title": "changing a variable that was not declared mutable",
        "bad": '''fn main() {
    let count = 0;
    count += 1;
    println!("{}", count);
}''',
        "fixed": '''fn main() {
    let mut count = 0;
    count += 1;
    println!("{}", count);
}''',
        "why": "Variables are immutable by default in Rust. `count += 1` tries to change the value, which is only allowed when the variable is declared with `mut`.",
        "changes": [
            "`let count = 0;` became `let mut count = 0;`.",
            "Only add `mut` to variables that really change; the compiler will warn you about unused `mut`.",
        ],
    },
    {
        "code": "E0425",
        "msg": "cannot find value `totl` in this scope",
        "title": "a misspelled variable name",
        "bad": '''fn main() {
    let total = 5;
    println!("{}", totl);
}''',
        "fixed": '''fn main() {
    let total = 5;
    println!("{}", total);
}''',
        "why": "The variable is called `total`, but the `println!` uses `totl`. Rust does not know any value with that name in this scope.",
        "changes": [
            "I corrected the typo `totl` to `total` in the `println!` call.",
            "When the compiler says \"cannot find value\", also check that the variable is declared in the same or an outer block and that you imported it with `use` if it comes from a module.",
        ],
    },
    {
        "code": "E0599",
        "msg": "no method named `sorted` found for struct `Vec<{integer}>` in the current scope",
        "title": "calling a method that does not exist",
        "bad": '''fn main() {
    let v = vec![3, 1, 2];
    let s = v.sorted();
    println!("{:?}", s);
}''',
        "fixed": '''fn main() {
    let mut v = vec![3, 1, 2];
    v.sort();
    println!("{:?}", v);
}''',
        "why": "`Vec` has no method called `sorted`. Rust's `sort` method sorts the vector in place and returns nothing, so the vector must be declared `mut`.",
        "changes": [
            "`let v` became `let mut v` because sorting modifies the vector.",
            "`v.sorted()` became `v.sort()`, and I print `v` itself since `sort` returns `()`.",
            "If you want a sorted copy and to keep the original, write `let mut s = v.clone(); s.sort();`.",
        ],
    },
    {
        "code": "E0277",
        "msg": "`Vec<{integer}>` doesn't implement `std::fmt::Display`",
        "title": "printing a type that has no Display implementation",
        "bad": '''fn main() {
    let numbers = vec![1, 2, 3];
    println!("{}", numbers);
}''',
        "fixed": '''fn main() {
    let numbers = vec![1, 2, 3];
    println!("{:?}", numbers);
}''',
        "why": "`{}` needs the `Display` trait, which is meant for user-facing text. `Vec` does not implement it because there is no single obvious way to show a list. `{:?}` uses the `Debug` trait, which `Vec` does implement.",
        "changes": [
            "`{}` became `{:?}` in the `println!`.",
            "Use `{:#?}` for pretty-printed multi-line output, or join the items yourself if you want a custom look.",
            "For your own struct add `#[derive(Debug)]` to use `{:?}`, or implement `std::fmt::Display` manually to use `{}`.",
        ],
    },
    {
        "code": "E0106",
        "msg": "missing lifetime specifier",
        "title": "a function returning a reference with two possible sources",
        "bad": '''fn longest(a: &str, b: &str) -> &str {
    if a.len() >= b.len() { a } else { b }
}

fn main() {
    println!("{}", longest("tree", "forest"));
}''',
        "fixed": '''fn longest<'a>(a: &'a str, b: &'a str) -> &'a str {
    if a.len() >= b.len() { a } else { b }
}

fn main() {
    println!("{}", longest("tree", "forest"));
}''',
        "why": "The function returns a reference, but it has two reference parameters, so the compiler cannot tell which input the result borrows from. You have to say so with a lifetime parameter.",
        "changes": [
            "I added a lifetime parameter `<'a>` to the function.",
            "I annotated both inputs and the return type with `'a`, meaning \"the result lives no longer than the shorter-lived of `a` and `b`\".",
        ],
    },
    {
        "code": "E0596",
        "msg": "cannot borrow `*v` as mutable, as it is behind a `&` reference",
        "title": "modifying data through a shared reference",
        "bad": '''fn add_item(v: &Vec<i32>) {
    v.push(1);
}

fn main() {
    let mut list = Vec::new();
    add_item(&list);
    println!("{:?}", list);
}''',
        "fixed": '''fn add_item(v: &mut Vec<i32>) {
    v.push(1);
}

fn main() {
    let mut list = Vec::new();
    add_item(&mut list);
    println!("{:?}", list);
}''',
        "why": "`&Vec<i32>` is a shared, read-only reference, but `push` changes the vector. Changing data requires an exclusive mutable reference, `&mut`.",
        "changes": [
            "The parameter type changed from `&Vec<i32>` to `&mut Vec<i32>`.",
            "The call changed from `add_item(&list)` to `add_item(&mut list)`. The variable `list` was already declared `mut`, which is required for this.",
        ],
    },
    {
        "code": "E0507",
        "msg": "cannot move out of `u.name` which is behind a shared reference",
        "title": "returning an owned field from a borrowed struct",
        "bad": '''struct User {
    name: String,
}

fn take_name(u: &User) -> String {
    u.name
}

fn main() {
    let user = User { name: String::from("Mira") };
    println!("{}", take_name(&user));
}''',
        "fixed": '''struct User {
    name: String,
}

fn take_name(u: &User) -> String {
    u.name.clone()
}

fn main() {
    let user = User { name: String::from("Mira") };
    println!("{}", take_name(&user));
}''',
        "why": "The function only borrows the user (`&User`), but `u.name` would move the String out of it and leave the original struct with a hole. You cannot take ownership of something you merely borrowed.",
        "changes": [
            "`u.name` became `u.name.clone()`, which returns a new owned String and leaves the user untouched.",
            "If cloning is wasteful, change the return type to `&str` and return `&u.name` so the caller just borrows the text.",
        ],
    },
    {
        "code": "E0373",
        "msg": "closure may outlive the current function, but it borrows `v`, which is owned by the current function",
        "title": "a thread closure that borrows local data",
        "bad": '''use std::thread;

fn main() {
    let v = vec![1, 2, 3];
    let handle = thread::spawn(|| {
        println!("{:?}", v);
    });
    handle.join().unwrap();
}''',
        "fixed": '''use std::thread;

fn main() {
    let v = vec![1, 2, 3];
    let handle = thread::spawn(move || {
        println!("{:?}", v);
    });
    handle.join().unwrap();
}''',
        "why": "A spawned thread can run longer than the function that created it, so it must not borrow local variables. The closure needs to own the data it uses.",
        "changes": [
            "I added the `move` keyword before the closure: `|| ...` became `move || ...`. The closure now takes ownership of `v`.",
            "After the move, `v` cannot be used in `main` anymore. If you need it in both places, wrap it in `Arc` and clone the `Arc` for the thread.",
        ],
    },
    {
        "code": "E0004",
        "msg": "non-exhaustive patterns: `Color::Blue` not covered",
        "title": "a match that forgets an enum variant",
        "bad": '''enum Color {
    Red,
    Green,
    Blue,
}

fn name(c: Color) -> &'static str {
    match c {
        Color::Red => "red",
        Color::Green => "green",
    }
}

fn main() {
    println!("{}", name(Color::Blue));
}''',
        "fixed": '''enum Color {
    Red,
    Green,
    Blue,
}

fn name(c: Color) -> &'static str {
    match c {
        Color::Red => "red",
        Color::Green => "green",
        Color::Blue => "blue",
    }
}

fn main() {
    println!("{}", name(Color::Blue));
}''',
        "why": "A `match` must cover every possible value. The variant `Color::Blue` has no arm, so Rust refuses to compile, which prevents bugs when you add a new variant later.",
        "changes": [
            "I added the missing arm `Color::Blue => \"blue\"`.",
            "A catch-all arm `_ => ...` would also compile, but listing every variant is better because the compiler will warn you when a new variant is added.",
        ],
    },
    {
        "code": "E0369",
        "msg": "cannot add `T` to `T`",
        "title": "using + on a generic type without a trait bound",
        "bad": '''fn add<T>(a: T, b: T) -> T {
    a + b
}

fn main() {
    println!("{}", add(2, 3));
}''',
        "fixed": '''use std::ops::Add;

fn add<T: Add<Output = T>>(a: T, b: T) -> T {
    a + b
}

fn main() {
    println!("{}", add(2, 3));
}''',
        "why": "A generic `T` could be any type, including types that cannot be added. You must declare that `T` supports `+` by adding a trait bound.",
        "changes": [
            "I imported `std::ops::Add`.",
            "I changed `<T>` to `<T: Add<Output = T>>`, which means \"T can be added to itself and the result is again a T\".",
        ],
    },
    {
        "code": "E0282",
        "msg": "type annotations needed for `Vec<T>`",
        "title": "an empty collection whose element type cannot be inferred",
        "bad": '''fn main() {
    let items = Vec::new();
    println!("{}", items.len());
}''',
        "fixed": '''fn main() {
    let items: Vec<i32> = Vec::new();
    println!("{}", items.len());
}''',
        "why": "`Vec::new()` could create a vector of anything, and nothing in the program says what the elements are, so the compiler cannot decide.",
        "changes": [
            "I added the type annotation `: Vec<i32>` to the variable. Use whatever element type you actually need.",
            "The annotation is unnecessary once you push a value, because the compiler then infers the type from it.",
        ],
    },
]


def _changes(e):
    return "\n".join(f"{i}. {c}" for i, c in enumerate(e["changes"], 1))


def generate():
    out = []
    for e in ENTRIES:
        explanation = (
            f"The compiler error `{e['code']}` ({e['msg']}) is caused by this:\n\n{e['why']}\n\n"
            f"Fixed code:\n\n```rust\n{e['fixed']}\n```\n\nChanges made:\n{_changes(e)}"
        )
        out.append((
            f"I get `error[{e['code']}]: {e['msg']}`. Here is my code:\n\n```rust\n{e['bad']}\n```",
            explanation,
        ))
        out.append((
            f"Fix this Rust code and tell me exactly what you changed:\n\n```rust\n{e['bad']}\n```",
            f"This program fails with `{e['code']}` ({e['title']}). {e['why']}\n\n"
            f"```rust\n{e['fixed']}\n```\n\nWhat I changed:\n{_changes(e)}",
        ))
        out.append((
            f"Why does the Rust compiler reject this code?\n\n```rust\n{e['bad']}\n```",
            f"It is rejected with `{e['code']}`: {e['msg']}.\n\n{e['why']}\n\n"
            f"Corrected version:\n\n```rust\n{e['fixed']}\n```\n\nSummary of the fix:\n{_changes(e)}",
        ))
    return out

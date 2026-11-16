"""Build data/staging/claude_typescript_24.txt. Every file is written to a temporary folder; the type errors are the REAL
output of tsc 5.9 and the program output is the real output of Node 24 running the .ts file directly."""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

F = "`" * 3
OUT = Path(r"C:\Projects\Mavo\Coding 1 2B\data\staging\claude_typescript_24.txt")
TOOLS = Path(r"C:\Projects\Mavo\Coding 1 2B\data\staging\proj\ts_tools")
NODE = shutil.which("node")
EXAMPLES = []

TSCONFIG = '''{
  "compilerOptions": {
    "target": "es2023",
    "module": "nodenext",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noEmit": true,
    "allowImportingTsExtensions": true,
    "erasableSyntaxOnly": true,
    "skipLibCheck": true
  },
  "include": ["*.ts"]
}
'''
PACKAGE = '{\n  "type": "module"\n}\n'


def run_session(files, runs):
    d = Path(tempfile.mkdtemp())
    for name, content in files.items():
        p = d / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8", newline="\n")
    subprocess.run(["cmd", "/c", "mklink", "/J", str(d / "node_modules"), str(TOOLS / "node_modules")],
                   stdout=subprocess.DEVNULL, check=True)
    blocks = []
    for kind, args in runs:
        if kind == "tsc":
            cmd = [NODE, str(TOOLS / "node_modules/typescript/bin/tsc"), "--pretty", "false"] + list(args)
            label = "$ npx tsc " + " ".join(list(args) + ["--pretty", "false"])
        else:
            cmd = [NODE] + list(args)
            label = "$ node " + " ".join(args)
        e = {k: v for k, v in os.environ.items() if k != "NODE_OPTIONS"}
        p = subprocess.run(cmd, cwd=str(d), env=e, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                           encoding="utf-8", timeout=120)
        body = p.stdout.replace("\r", "").replace(str(d), r"C:\work").replace(str(d).replace("\\", "/"), "C:/work")
        body = "\n".join(l.rstrip() for l in body.split("\n")).strip("\n")
        lines = [label]
        if body:
            lines.append(body)
        if p.returncode:
            lines.append(f"[exit code {p.returncode}]")
        blocks.append("\n".join(lines))
    shutil.rmtree(d, ignore_errors=True)
    return "\n\n".join(blocks)


def ex(question, intro, shown, runs, after, files=None, show_config=False):
    real = {"tsconfig.json": TSCONFIG, "package.json": PACKAGE}
    real.update(files or {})
    parts = [intro.strip()]
    for name, lang, content in shown:
        assert F not in content
        real[name] = content.strip("\n") + "\n"
        parts.append(f"`{name}`:\n\n{F}{lang}\n{content.strip(chr(10))}\n{F}")
    result = run_session(real, runs)
    parts.append(f"Running it:\n\n{F}\n{result}\n{F}")
    parts.append(after.strip())
    EXAMPLES.append((question, "\n\n".join(parts)))
    print(f"---- example {len(EXAMPLES)} ----\n{result}\n")


TSC = ("tsc", ["--noEmit"])

# 1 ---------------------------------------------------------------------------------------------
ex("What is the difference between interface and type in TypeScript, and which one should I use?",
   "For describing the shape of an object they are almost the same, and for most code either is fine. The real differences are few. An `interface` can be **declared again** and the declarations are merged, and it is extended with `extends`. A `type` is an alias for any type, so it is the only one that can name a **union** (`number | string`), a tuple or a computed type, and it combines types with `&`. A `type` cannot be declared twice. A common rule that works: use `interface` for the shape of objects and classes that others may extend, and `type` for everything else, and be consistent in one project.",
   [("ok.ts", "typescript", r'''
interface User { id: number; name: string }
interface User { email?: string }              // merged with the one above

type Id = number | string;                     // only a type can be a union
type Point = { x: number; y: number };
type Point3D = Point & { z: number };          // combine with &

interface Animal { name: string }
interface Dog extends Animal { bark(): string }

const user: User = { id: 1, name: "Ann", email: "ann@example.com" };
const point: Point3D = { x: 1, y: 2, z: 3 };
const dog: Dog = { name: "Rex", bark: () => "woof" };

function show(id: Id): string {
  return typeof id === "number" ? `#${id}` : id.toUpperCase();
}

console.log(user, point, dog.bark(), show(7), show("abc"));
'''),
    ("bad.ts", "typescript", r'''
type Point = { x: number };
type Point = { y: number };      // a type cannot be declared twice

interface Box { w: number }
interface Box { h: number }      // merges: Box now needs both w and h
const box: Box = { w: 1 };
''')],
   [TSC, ("node", ["ok.ts"])],
   "`tsc --noEmit` checks the types and writes no files, and Node runs `ok.ts` directly, because current Node versions can strip the type annotations by themselves. Read the three errors from `bad.ts`: the duplicate `type Point` is reported on both lines, and the second error shows what declaration merging means in practice, because `Box` now needs `h` as well and the object with only `w` is rejected. That surprise is the reason to be careful with `interface` names in the global scope, where an unrelated file can add members to your interface. Everything in `ok.ts` is a module-less script here only to keep the example short, and in a real project you would `export` the types.")

# 2 ---------------------------------------------------------------------------------------------
ex("How do I model data that can be one of several shapes in TypeScript, and make sure I handle every case?",
   "Use a **discriminated union**: every shape has the same field with a different literal value (here `kind`), and TypeScript narrows the type inside each `case`. To be sure that no case is forgotten, add a `default` branch that assigns the value to a variable of type `never`. As long as every case is handled, nothing can reach that branch and the code compiles. The day someone adds a new shape and forgets the `switch`, the compiler stops with an error at exactly that place.",
   [("shapes.ts", "typescript", r'''
export type Shape =
  | { kind: "circle"; radius: number }
  | { kind: "square"; side: number }
  | { kind: "rect"; width: number; height: number };

export function area(shape: Shape): number {
  switch (shape.kind) {
    case "circle":
      return Math.PI * shape.radius ** 2;
    case "square":
      return shape.side ** 2;
    case "rect":
      return shape.width * shape.height;
    default: {
      const unreachable: never = shape;
      throw new Error(`unhandled shape: ${JSON.stringify(unreachable)}`);
    }
  }
}
'''),
    ("main.ts", "typescript", r'''
import { area, type Shape } from "./shapes.ts";

const shapes: Shape[] = [
  { kind: "circle", radius: 1 },
  { kind: "square", side: 3 },
  { kind: "rect", width: 2, height: 5 },
];
for (const s of shapes) console.log(s.kind.padEnd(7), area(s).toFixed(2));
'''),
    ("later.ts", "typescript", r'''
// a month later, somebody adds a triangle to the union but forgets the switch
type Shape =
  | { kind: "circle"; radius: number }
  | { kind: "triangle"; base: number; height: number };

function area(shape: Shape): number {
  switch (shape.kind) {
    case "circle":
      return Math.PI * shape.radius ** 2;
    default: {
      const unreachable: never = shape;
      throw new Error(`unhandled shape: ${JSON.stringify(unreachable)}`);
    }
  }
}
console.log(area({ kind: "circle", radius: 1 }));
''')],
   [TSC, ("node", ["main.ts"])],
   "The error in `later.ts` is the useful one: it says that the triangle is not assignable to `never`, and it points at the line of the `default` branch, so the person who adds the shape knows where to go. At runtime the `throw` is the second line of defense for data that does not follow the types (for example JSON from outside), because types do not exist any more once the program runs. Note `import { area, type Shape }`: the `type` keyword marks an import that only exists for the compiler, which Node's type stripping needs to know about, and this is also why the import path ends in `.ts`.")

# 3 ---------------------------------------------------------------------------------------------
ex("What is the difference between any and unknown in TypeScript? How do I handle JSON.parse safely?",
   "`any` turns the type checker off for that value: you can do anything with it and TypeScript will not complain, even when the program will crash. `unknown` means \"I do not know what this is yet\": you can pass it around, but you cannot use it until you have checked what it is. `JSON.parse` returns `any`, which is why bugs hide there. The safe pattern is to put the result into an `unknown` variable and check it with a **type guard**, a function whose return type is `value is Something`. After the check, TypeScript knows the type.",
   [("ok.ts", "typescript", r'''
interface Config {
  host: string;
  port: number;
}

function isConfig(value: unknown): value is Config {
  if (typeof value !== "object" || value === null) return false;
  const record = value as Record<string, unknown>;
  return typeof record.host === "string" && typeof record.port === "number";
}

function parseConfig(text: string): Config {
  const data: unknown = JSON.parse(text);
  if (!isConfig(data)) throw new Error("config must look like {host: string, port: number}");
  return data;
}

console.log(parseConfig('{"host":"localhost","port":8080}'));
try {
  parseConfig('{"host":"localhost","port":"8080"}');
} catch (err) {
  console.log("error:", err instanceof Error ? err.message : String(err));
}
'''),
    ("bad.ts", "typescript", r'''
const raw: unknown = JSON.parse('{"a": 1}');
console.log(raw.a);             // not allowed: raw is unknown
''' ),
    ("loose.ts", "typescript", r'''
const loose = JSON.parse('{"a": 1}');   // type: any
try {
  console.log(loose.b.c.d);             // compiles without a single complaint
} catch (err) {
  console.log("crash at runtime:", (err as Error).message);
}
''')],
   [TSC, ("node", ["ok.ts"]), ("node", ["loose.ts"])],
   "The only error `tsc` reports is the one for `unknown` in `bad.ts`, and that is the compiler doing its job. `loose.ts` is the same mistake with `any`: there is **no** error, and the program fails at runtime. The type guard `isConfig` is checked at runtime, so it is real protection (a port that arrives as the string `\"8080\"` is caught), and its `value is Config` return type is a promise to the compiler that you have written the check correctly. If a check gets long, a validation library such as zod writes the guard for you, but the idea is the same. Turn on `strict` in `tsconfig.json`, so that implicit `any` is an error as well.")

# 4 ---------------------------------------------------------------------------------------------
ex("How do generics work in TypeScript? Show me a useful example, with constraints.",
   "A generic is a type that is a parameter of the function: `T` stands for whatever type the caller uses, and TypeScript works it out from the arguments, so you rarely write it yourself. A **constraint** (`K extends keyof T`) limits what `T` or `K` may be. The two functions below are typical: `pluck` takes a list of objects and the name of a property, and returns the values of that property **with the right type**, and it only accepts names that exist on the objects. `groupBy` sorts items into a record by a key function.",
   [("lib.ts", "typescript", r'''
export function pluck<T, K extends keyof T>(items: readonly T[], key: K): T[K][] {
  return items.map((item) => item[key]);
}

export function groupBy<T, K extends string>(items: readonly T[], keyOf: (item: T) => K): Record<K, T[]> {
  const groups = {} as Record<K, T[]>;
  for (const item of items) {
    (groups[keyOf(item)] ??= []).push(item);
  }
  return groups;
}
'''),
    ("ok.ts", "typescript", r'''
import { groupBy, pluck } from "./lib.ts";

const people = [
  { name: "Ann", age: 31, city: "Oslo" },
  { name: "Bo", age: 25, city: "Rome" },
  { name: "Cy", age: 42, city: "Oslo" },
];

const ages = pluck(people, "age");                 // number[]
const names = pluck(people, "name");               // string[]
console.log(ages, names, ages.reduce((a, b) => a + b, 0));
console.log(groupBy(people, (p) => p.city));
'''),
    ("bad.ts", "typescript", r'''
import { groupBy, pluck } from "./lib.ts";

const people = [{ name: "Ann", age: 31 }];
pluck(people, "salary");                           // no such property
groupBy(people, (p) => p.age);                     // the key must be a string
const total: string = pluck(people, "age")[0];     // the result type is number
''')],
   [TSC, ("node", ["ok.ts"])],
   "Look at what the compiler knows without being told anything: `pluck(people, \"age\")` is a `number[]`, which is why `reduce` with a number works, and `\"salary\"` is rejected with the list of the names that are allowed (the first error). `T[K]` is an *indexed access type*: the type of property `K` of `T`. The `{} as Record<K, T[]>` cast is the one honest lie in `groupBy`, because an empty object does not have all the keys yet, and it is acceptable here because the function fills in each key before anyone reads it. Keep generics simple: if a function has one use, a plain type is easier to read, and a type parameter that appears only once in the signature usually does nothing.")

# 5 ---------------------------------------------------------------------------------------------
ex("What does TypeScript's strict null checking catch, and how do I deal with undefined properly? What about array access?",
   "With `strict` on, `undefined` and `null` are separate types, so a value that may be missing says so in its type (`string | undefined`) and you must deal with it before you use it. The tools are optional chaining `a?.b` (stops and gives `undefined` if `a` is missing), the nullish default `??` (uses the default only for `null` and `undefined`, not for `0` or an empty string), and an ordinary `if` check. Array access is a special case: `names[5]` looks like a `string`, but it can be missing. The option `noUncheckedIndexedAccess` (it is **not** part of `strict`, so you add it yourself) makes it `string | undefined`, which is the truth.",
   [("ok.ts", "typescript", r'''
interface User {
  name: string;
  address?: { city?: string };
}

function cityOf(user: User): string {
  return user.address?.city ?? "unknown";
}

function first<T>(items: readonly T[]): T | undefined {
  return items[0];
}

function orDefault(value: number | null | undefined, fallback: number): number {
  return value ?? fallback;
}

const names = ["ann", "bo"];
const third = names[2];                            // string | undefined with noUncheckedIndexedAccess
const head = first(names);

console.log(cityOf({ name: "Ann" }), cityOf({ name: "Bo", address: { city: "Oslo" } }));
console.log(head?.toUpperCase(), third?.toUpperCase() ?? "no third name");
console.log(orDefault(0, 5), orDefault(null, 5), orDefault(undefined, 5));
'''),
    ("bad.ts", "typescript", r'''
interface User {
  name: string;
  address?: { city?: string };
}

function first<T>(items: readonly T[]): T | undefined {
  return items[0];
}

const user: User = { name: "Ann" };
console.log(user.address.city);                    // address may be missing
console.log(first(["x"]).length);                  // the list may be empty
const names = ["ann", "bo"];
console.log(names[2].length);                      // there may be no third element
''')],
   [TSC, ("node", ["ok.ts"])],
   "All three errors are real crashes that would have happened (`Cannot read properties of undefined`), found before the program ran. In the last line of the output, `orDefault(0, 5)` is `0`, because `??` replaces only `null` and `undefined`, and that is the difference to `||`, which would replace the `0` with the default as well. Avoid the `!` operator (`user.address!.city`) as the way to silence these errors, because it only tells the compiler to stop checking, and the crash comes back at runtime. If a value really cannot be missing at that point, write the check once (`if (!user.address) throw new Error(\"no address\")`), and after it the compiler knows.")

# 6 ---------------------------------------------------------------------------------------------
ex("How do I set up TypeScript for a Node project in 2026, and can I run .ts files without a build step?",
   "Current Node versions (22.18 and later, and 24) run `.ts` files directly: they remove the type annotations before running and do **not** check the types. So the two jobs are split. `node file.ts` runs the program, and `tsc --noEmit` checks the types (in your editor, in a pre-commit step and in CI). For this to work, the code may only use *erasable* syntax: types, interfaces and annotations can be deleted and what remains is valid JavaScript. Features that generate code, such as `enum`, `namespace` and constructor parameter properties, are not supported by the stripping. The `erasableSyntaxOnly` option makes the compiler report those immediately, so you find out in the editor and not when you run.",
   [("package.json", "json", '''
{
  "type": "module",
  "scripts": {
    "start": "node main.ts",
    "check": "tsc --noEmit"
  },
  "devDependencies": {
    "@types/node": "^24",
    "typescript": "^5.9"
  }
}
'''),
    ("tsconfig.json", "json", TSCONFIG),
    ("main.ts", "typescript", r'''
type Level = "debug" | "info" | "error";           // a union of strings instead of an enum
const LEVELS = ["debug", "info", "error"] as const;

function log(level: Level, message: string): void {
  console.log(`[${level.toUpperCase()}] ${message}`);
}

log("info", `levels: ${LEVELS.join(", ")}`);
'''),
    ("enum.ts", "typescript", r'''
enum Color {
  Red,
  Green,
}
console.log(Color.Green);
''')],
   [TSC, ("node", ["main.ts"]), ("node", ["enum.ts"])],
   "`tsc` rejects the `enum` with an error that names the option, and Node refuses to run it with its own error. Both tell you the same thing, which is the reason for the option. Replace `enum` with a union of string literals plus an `as const` array when you need the list of values at runtime, as `main.ts` does. The settings that matter in the `tsconfig.json`: `strict` (the checks that make TypeScript useful), `module: nodenext` (the module rules that Node really uses, so a missing file extension in an import is reported by the compiler), `noEmit` (there is nothing to build), and `allowImportingTsExtensions` (you write `./lib.ts` in the import, because that is the real file name Node looks for). If you need to publish JavaScript for others or run on an older Node, you add a build step with `tsc` or a bundler, and the source code does not change.")

# 7 ---------------------------------------------------------------------------------------------
ex("I typed my fetch function as Promise<User> and TypeScript is happy, but the program still crashes with the wrong data. Why?",
   "Because TypeScript types exist only while the compiler runs. `res.json()` returns `any`, and `as T` (or a return type such as `Promise<User>` on a generic function) is only a **promise from you to the compiler**, not a check. If the server sends something different, the compiler has no way to know. At every boundary where data comes from outside the program (a network call, a file, `JSON.parse`, user input), the type must be proven at runtime by a check, and after the check the types are trustworthy. The example runs a small local server that sends the wrong shape.",
   [("api.ts", "typescript", r'''
export interface User {
  id: number;
  name: string;
}

// compiles, but the "as T" is only a promise: nothing is checked
export async function getJsonUnsafe<T>(url: string): Promise<T> {
  const res = await fetch(url);
  return (await res.json()) as T;
}

export function asUser(data: unknown): User {
  const record = data as Record<string, unknown> | null;
  if (typeof record?.id !== "number" || typeof record?.name !== "string") {
    throw new Error(`not a User: ${JSON.stringify(data)}`);
  }
  return { id: record.id, name: record.name };
}

export async function getUser(url: string): Promise<User> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return asUser(await res.json());
}
'''),
    ("main.ts", "typescript", r'''
import http from "node:http";
import { asUser, getJsonUnsafe, getUser, type User } from "./api.ts";

// the server's data does not follow the type: id is a string and name is missing
const server = http.createServer((req, res) => {
  res.writeHead(200, { "Content-Type": "application/json" }).end(JSON.stringify({ id: "7" }));
});
await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
const url = `http://127.0.0.1:${(server.address() as { port: number }).port}/user`;

const user = await getJsonUnsafe<User>(url);
console.log("unsafe: id + 1 =", user.id + 1);          // "71": a string was added, not a number
try {
  console.log(user.name.toUpperCase());
} catch (err) {
  console.log("unsafe: crash:", (err as Error).message);
}

try {
  await getUser(url);
} catch (err) {
  console.log("checked:", (err as Error).message);
}
server.close();
''')],
   [TSC, ("node", ["main.ts"])],
   "`tsc` prints nothing, which is how it reports success, and that is exactly the problem: the unsafe version passes every check and still gives `71` instead of `8` and then crashes. The checked version fails at the boundary, with a message that shows the data that arrived, so the error points at the server and not at some line far away that happened to use the value. This is the main limit of TypeScript, and the reason that tools such as zod, valibot or hand-written guards exist: they produce the **type** and the **runtime check** from one description, so the two cannot disagree.")

# 8 ---------------------------------------------------------------------------------------------
ex("Which TypeScript utility types are worth knowing? Partial, Pick, Omit, Record, Readonly, ReturnType, Awaited.",
   "They build new types from existing ones, so you do not copy and keep two versions in step. Put them in your head as small transformations: `Partial<T>` makes every property optional; `Pick<T, K>` keeps only the listed properties and `Omit<T, K>` removes them; `Readonly<T>` forbids assignment; `Record<K, V>` is an object with exactly the keys `K`; `ReturnType<typeof fn>` is what a function returns, and `Awaited<...>` unwraps a promise.",
   [("ok.ts", "typescript", r'''
interface Todo {
  id: number;
  title: string;
  done: boolean;
  due?: string;
}

// the id can never change, everything else can
function update(todo: Todo, changes: Partial<Omit<Todo, "id">>): Todo {
  return { ...todo, ...changes };
}

type TodoPreview = Pick<Todo, "id" | "title">;
const labels: Record<"low" | "high", string> = { low: "Low priority", high: "High priority" };

function makeTodo(title: string) {
  return { id: 1, title, done: false };
}
type Made = ReturnType<typeof makeTodo>;            // { id: number; title: string; done: boolean }

async function loadIds() {
  return [1, 2, 3];
}
type Ids = Awaited<ReturnType<typeof loadIds>>;     // number[]

const todo: Made = makeTodo("write tests");
const preview: TodoPreview = { id: todo.id, title: todo.title };
const ids: Ids = await loadIds();
console.log(update(todo, { done: true }), preview, labels.high, ids.length);
'''),
    ("bad.ts", "typescript", r'''
interface Todo {
  id: number;
  title: string;
  done: boolean;
}

function update(todo: Todo, changes: Partial<Omit<Todo, "id">>): Todo {
  return { ...todo, ...changes };
}

const todo: Readonly<Todo> = { id: 1, title: "x", done: false };
update(todo, { id: 2 });                            // id was removed from the changes
todo.done = true;                                   // Readonly
const labels: Record<"low" | "high", string> = { low: "Low" };   // a key is missing
''')],
   [TSC, ("node", ["ok.ts"])],
   "Each error shows one utility type doing its job, and the messages repeat the computed type, so you can read what `Partial<Omit<Todo, \"id\">>` came out as. `ReturnType<typeof makeTodo>` is the practical one: the type follows the function, so when `makeTodo` gets a new field, `Made` gets it too and nothing else needs a change. Two cautions. `Readonly` is checked only by the compiler and does not freeze the object at runtime (use `Object.freeze` for that), and `Partial` is often the wrong tool for a function that takes options, where a small interface with optional properties and defaults is easier to read.")

# 9 ---------------------------------------------------------------------------------------------
ex("How should I type errors and async code in TypeScript? What type is the error in a catch block?",
   "In a `catch` block the error is `unknown` (with `strict`), because in JavaScript you can throw anything, a string or a number as well as an `Error`. So you check before you use it: `err instanceof Error` for ordinary errors, and `instanceof` your own class for the ones you care about. Define your own error classes for the cases that the caller handles differently (here an HTTP status). For async code the types follow the promise: `Promise.all` keeps the type of each position in the array, and `Promise.allSettled` returns a list of results that you must check one by one.",
   [("ok.ts", "typescript", r'''
class HttpError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "HttpError";
    this.status = status;
  }
}

async function getItem(id: number): Promise<string> {
  if (id < 0) throw new HttpError(404, `no item ${id}`);
  await null;                                       // pretend to wait for something
  return `item ${id}`;
}

const [a, b] = await Promise.all([getItem(1), getItem(2)]);   // [string, string]
console.log(a, b);

try {
  await getItem(-1);
} catch (err) {
  if (err instanceof HttpError) {
    console.log("http error", err.status, err.message);
  } else {
    throw err;                                      // not ours: do not hide it
  }
}

const results = await Promise.allSettled([getItem(3), getItem(-3)]);
for (const result of results) {
  console.log(result.status === "fulfilled" ? result.value : `failed: ${(result.reason as Error).message}`);
}
'''),
    ("bad.ts", "typescript", r'''
async function getItem(id: number): Promise<string> {
  return `item ${id}`;
}

try {
  await getItem(1);
} catch (err) {
  console.log(err.message);                         // err is unknown
}

const [first] = await Promise.all([getItem(1)]);
console.log(first.toFixed(2));                      // first is a string
const pending: string = getItem(2);                 // forgot await: this is a Promise
''')],
   [TSC, ("node", ["ok.ts"])],
   "Three typical mistakes are in `bad.ts`. Using `err.message` directly is refused because `err` is `unknown`. `first.toFixed` is refused because `Promise.all` kept the exact type of the first position. And the missing `await` in the last line is refused because a `Promise<string>` is not a `string`. That last one is the most common async bug, and the compiler finds it only when the result is assigned to something with a type, so write the return types of async functions down. In `ok.ts`, the `else { throw err }` matters: a `catch` that swallows everything it does not recognize hides real bugs. `this.name = \"HttpError\"` makes the class name show up in logs and stack traces, and the class has an ordinary field `status` instead of the shorthand `constructor(private status)`, because the shorthand is not erasable syntax and Node's type stripping would reject it.")

# 10 --------------------------------------------------------------------------------------------
ex("What do 'as const' and 'satisfies' do in TypeScript, and when are they better than a normal type annotation?",
   "A normal annotation (`const x: Type = ...`) **replaces** what TypeScript worked out from the value with the type you wrote, so information is lost: a list typed as `string | number[]` is no longer known to be a list. `as const` freezes the type of a literal to its exact, read-only form (`\"/users/:id\"`, not just `string`). `satisfies` checks that a value matches a type, **without changing** the type of the value, so you get the check and keep the detail. Together they are the right way to write tables of configuration.",
   [("ok.ts", "typescript", r'''
const ROUTES = {
  home: "/",
  user: "/users/:id",
} as const;

type RouteName = keyof typeof ROUTES;                // "home" | "user"
type RoutePath = (typeof ROUTES)[RouteName];         // "/" | "/users/:id"

function link(name: RouteName, params: Record<string, string | number> = {}): RoutePath | string {
  return ROUTES[name].replace(/:(\w+)/g, (_, key: string) => String(params[key]));
}

const palette = {
  red: [255, 0, 0],
  green: "#00ff00",
} satisfies Record<string, string | number[]>;

console.log(link("home"), link("user", { id: 42 }));
console.log(palette.red.map((v) => v / 255), palette.green.toUpperCase());   // the exact types are kept
'''),
    ("bad.ts", "typescript", r'''
const ROUTES = { home: "/" } as const;
ROUTES.home = "/start";                              // as const makes it read-only

const typo = { red: true } satisfies Record<string, string | number[]>;   // checked at once

const annotated: Record<string, string | number[]> = { red: [255, 0, 0] };
annotated.red.map((v) => v);                         // an annotation forgot that red is a list
''')],
   [TSC, ("node", ["ok.ts"])],
   "The last three errors all come from the one annotated line, and they show what an annotation costs: `annotated.red` is only `string | number[]` (and possibly missing, because the type is a `Record<string, ...>`), so `map` is not available, while with `satisfies` the same data in `ok.ts` still has its precise type, and `palette.red.map(...)` and `palette.green.toUpperCase()` both work. The `satisfies` line in `bad.ts` also shows the other half, the check: a value of the wrong type is reported at the place where you wrote it. From `ROUTES` you got a type for the names and a type for the paths for free, with no second list to keep in step, and that is the main reason to put the data in one `as const` object and derive the types from it.")

# ------------------------------------------------------------------------------ write
text = ""
for q, a in EXAMPLES:
    assert len(q) + len(a) < 39000, (q, len(a))
    text += f"@@@ USER\n{q}\n@@@ ASSISTANT\n{a}\n@@@ END\n\n"
OUT.write_text(text, encoding="utf-8", newline="\n")
print("wrote", OUT, len(EXAMPLES), "examples", len(text), "chars")

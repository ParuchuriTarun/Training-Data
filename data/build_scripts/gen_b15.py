"""Build data/staging/claude_js_patterns_15.txt. Every JavaScript program is RUN with Node and the real
output is pasted into the answer."""
import subprocess
import sys
import tempfile
from pathlib import Path

F = "`" * 3
OUT = Path(r"C:\Projects\Mavo\Coding 1 2B\data\staging\claude_js_patterns_15.txt")


def run_js(code):
    d = Path(tempfile.mkdtemp())
    (d / "m.js").write_text(code.strip() + "\n", encoding="utf-8", newline="\n")
    p = subprocess.run(["node", "m.js"], cwd=d, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True, encoding="utf-8", timeout=30)
    if p.returncode:
        print("NODE FAILED:\n", p.stdout[:1500])
        sys.exit(1)
    return p.stdout.replace("\r", "").rstrip("\n")


EXAMPLES = []


def ex(question, intro, code, after):
    out = run_js(code)
    ans = f"{intro}\n\n{F}js\n{code.strip()}\n{F}\n\nOutput:\n\n{F}\n{out}\n{F}\n\n{after.strip()}"
    EXAMPLES.append((question, ans))


# 1 ---------------------------------------------------------------------------------------------
ex("How do I write debounce and throttle functions in JavaScript, and what is the difference?",
   "Debounce waits until the calls have **stopped** for a while and then runs once. Throttle runs at most once per time window while the calls keep coming. Here are both, with a simulated typing session.",
   r'''
function debounce(fn, waitMs) {
  let timer = null;
  const debounced = (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      timer = null;
      fn(...args);
    }, waitMs);
  };
  debounced.cancel = () => {
    clearTimeout(timer);
    timer = null;
  };
  return debounced;
}

function throttle(fn, intervalMs) {
  let last = -Infinity;
  return (...args) => {
    const now = Date.now();
    if (now - last >= intervalMs) {
      last = now;
      fn(...args);
    }
  };
}

// Debounce: the user types quickly, then pauses.
const search = debounce((q) => console.log('searching for:', q), 60);
['j', 'ja', 'jav', 'java'].forEach((text, i) =>
  setTimeout(() => {
    console.log('keystroke:', text);
    search(text);
  }, i * 15)
);

// Typing again, but the search is cancelled before the 60 ms wait is over.
setTimeout(() => { console.log('keystroke: javas'); search('javas'); }, 300);
setTimeout(() => { search.cancel(); console.log('cancelled'); }, 320);

// Throttle: ten calls in the same instant, only the first one runs.
let runs = 0;
const onScroll = throttle(() => { runs++; }, 100);
for (let i = 0; i < 10; i++) onScroll();
console.log('throttled handler ran', runs, 'time(s) for 10 calls');
''',
   """
When to use which:
- **Debounce** fits "react after the user stops": search-as-you-type, auto-save, validating a form field, resizing a layout once the window stops changing. Only `java` is searched, not `j`, `ja` and `jav`.
- **Throttle** fits "react regularly while it keeps happening": scroll position, mouse move, drag, window resize when you need live feedback. It protects the page from running expensive code hundreds of times per second.
- The returned function keeps its state (`timer`, `last`) in a **closure**, so every debounced function has its own private timer.
- `debounced.cancel()` is worth adding. In a component you should cancel on unmount so that the callback does not run after the page part is gone.
- This throttle runs on the leading edge only (the first call runs immediately and calls inside the window are dropped). Libraries such as Lodash also offer a trailing call, so the last event is not lost. In the output the throttle line comes first because that loop runs immediately, while the debounce demo has to wait for its timers.""")

# 2 ---------------------------------------------------------------------------------------------
ex("Write a small event emitter class in JavaScript with on, off, once and emit.",
   "An emitter is a map from event name to a list of handlers. `once` wraps the handler so that it removes itself after the first call, and `emit` copies the list first so that handlers can safely add or remove listeners while running.",
   r'''
class Emitter {
  #handlers = new Map();

  on(event, handler) {
    if (!this.#handlers.has(event)) this.#handlers.set(event, []);
    this.#handlers.get(event).push(handler);
    return () => this.off(event, handler); // unsubscribe function
  }

  off(event, handler) {
    const list = this.#handlers.get(event);
    if (!list) return;
    const rest = list.filter((h) => h !== handler && h.original !== handler);
    if (rest.length) this.#handlers.set(event, rest);
    else this.#handlers.delete(event);
  }

  once(event, handler) {
    const wrapper = (...args) => {
      this.off(event, wrapper);
      handler(...args);
    };
    wrapper.original = handler;
    return this.on(event, wrapper);
  }

  emit(event, ...args) {
    const list = this.#handlers.get(event) ?? [];
    for (const handler of [...list]) handler(...args);
    return list.length > 0;
  }
}

const bus = new Emitter();

const onLogin = (user) => console.log('welcome,', user);
bus.on('login', onLogin);
bus.once('login', (user) => console.log('first login of the session by', user));
const stop = bus.on('login', (user) => console.log('audit log:', user));

console.log('handled:', bus.emit('login', 'asha'));
console.log('handled:', bus.emit('login', 'ben'));

stop();
bus.off('login', onLogin);
console.log('handled after removing everything:', bus.emit('login', 'cara'));
console.log('unknown event handled:', bus.emit('logout'));
''',
   """
Design points:
- `#handlers` is a **private field** (the `#` is part of the name). Code outside the class cannot read or change it, so every change has to go through `on` and `off`.
- `on` returns a function that unsubscribes. That is easier to use than remembering the handler: `const stop = bus.on(...)`, then `stop()`.
- In `once`, the wrapper removes itself **before** calling the handler. If the handler throws, it will still not run a second time. Storing `wrapper.original` lets `off(event, handler)` also remove a handler that was registered with `once`.
- `[...list]` copies the array before the loop. Without the copy, a `once` handler that removes itself while `emit` is looping would shift the array and make the loop skip the next handler.
- `emit` returns whether anything handled the event, which is the same convention as Node's `EventEmitter`. In Node you can simply `import { EventEmitter } from 'node:events'`, and in the browser `EventTarget` and `CustomEvent` give you something similar.""")

# 3 ---------------------------------------------------------------------------------------------
ex("What is the difference between Promise.all, allSettled, race and any in JavaScript?",
   "They all take a list of promises and return one promise. They differ in what counts as \"done\" and in what happens when one of the promises fails. Here every combinator runs on the same tasks with fixed delays.",
   r'''
const task = (ms, value, fails = false) =>
  new Promise((resolve, reject) =>
    setTimeout(() => (fails ? reject(new Error(value)) : resolve(value)), ms)
  );

async function main() {
  console.log('all        :', await Promise.all([task(30, 'a'), task(10, 'b'), task(20, 'c')]));

  try {
    await Promise.all([task(30, 'a'), task(10, 'boom', true), task(20, 'c')]);
  } catch (e) {
    console.log('all (fail) : rejected with', e.message);
  }

  const settled = await Promise.allSettled([task(30, 'a'), task(10, 'boom', true), task(20, 'c')]);
  console.log('allSettled :', settled.map((r) => (r.status === 'fulfilled' ? 'ok:' + r.value : 'err:' + r.reason.message)));

  console.log('race       :', await Promise.race([task(30, 'slow'), task(10, 'fast')]));

  try {
    await Promise.race([task(30, 'slow'), task(10, 'quick failure', true)]);
  } catch (e) {
    console.log('race (fail): rejected with', e.message);
  }

  console.log('any        :', await Promise.any([task(10, 'e1', true), task(30, 'winner'), task(20, 'e2', true)]));

  try {
    await Promise.any([task(10, 'e1', true), task(20, 'e2', true)]);
  } catch (e) {
    console.log('any (fail) :', e.constructor.name, e.errors.map((x) => x.message));
  }
}
main();
''',
   """
Cheat sheet:
- `Promise.all` waits for **all** to succeed and keeps the order of the input array (`a, b, c`), not the order of finishing. If one rejects, the result rejects immediately with that error; the other promises still run, but their results are ignored.
- `Promise.allSettled` never rejects. It waits for everything and gives `{status, value | reason}` for each one. Use it when partial success is acceptable, for example loading several independent widgets.
- `Promise.race` settles as soon as the **first** promise settles, whether it succeeds or fails. The usual use is a timeout: race the real request against a promise that rejects after N milliseconds.
- `Promise.any` resolves with the first **success** and ignores failures. Only when all fail does it reject, with an `AggregateError` whose `errors` array holds every reason. Use it for mirrors or fallbacks.
- None of them cancels the work that lost. To really stop a `fetch`, pass an `AbortSignal` (see `AbortController`).
- Inside `async` functions, `await Promise.all([...])` is how you run independent requests **in parallel**. Two `await`s one after another run them one after the other.""")

# 4 ---------------------------------------------------------------------------------------------
ex("How do I make a fetch wrapper in JavaScript that retries failed requests with exponential backoff and a timeout?",
   "Retry only when it can help: network errors, timeouts and 5xx responses. A 404 or 400 will give the same answer again. The wrapper below takes the `fetch` function as a parameter so it can be tested with a fake one, as the demo does (no real network is used).",
   r'''
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function fetchJson(url, { fetchImpl = fetch, retries = 3, baseDelayMs = 10, timeoutMs = 1000 } = {}) {
  let lastError;
  for (let attempt = 1; attempt <= retries + 1; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await fetchImpl(url, { signal: controller.signal });
      if (!res.ok) {
        const err = new Error(`HTTP ${res.status}`);
        err.retryable = res.status >= 500; // a 404 will not fix itself
        throw err;
      }
      return await res.json();
    } catch (err) {
      lastError = err;
      const retryable = err.retryable ?? true; // network errors and aborts
      console.log(`attempt ${attempt} failed: ${err.message}${retryable ? '' : ' (not retrying)'}`);
      if (!retryable || attempt > retries) break;
      await sleep(baseDelayMs * 2 ** (attempt - 1)); // 10, 20, 40, ...
    } finally {
      clearTimeout(timer);
    }
  }
  throw lastError;
}

// A fake fetch that returns the given responses one by one (an Error means a network failure).
function fakeFetch(responses) {
  let i = 0;
  return async () => {
    const r = responses[Math.min(i++, responses.length - 1)];
    if (r instanceof Error) throw r;
    return { ok: r.status >= 200 && r.status < 300, status: r.status, json: async () => r.body };
  };
}

async function main() {
  const flaky = fakeFetch([new TypeError('network down'), { status: 503 }, { status: 200, body: { id: 7 } }]);
  console.log('result:', await fetchJson('/api/item', { fetchImpl: flaky }));

  try {
    await fetchJson('/api/none', { fetchImpl: fakeFetch([{ status: 404 }]) });
  } catch (e) {
    console.log('gave up:', e.message);
  }

  try {
    await fetchJson('/api/x', { fetchImpl: fakeFetch([new TypeError('network down')]), retries: 2 });
  } catch (e) {
    console.log('gave up:', e.message);
  }
}
main();
''',
   """
Why it is built this way:
- `fetch` only rejects on network problems. A `404` or `500` is a **resolved** promise with `res.ok === false`, so you must check `res.ok` yourself, as the wrapper does.
- Exponential backoff (`baseDelay * 2 ** (attempt - 1)`) gives an overloaded server more and more room to recover. In production add some random jitter, so that many clients do not all retry at the same instant.
- `AbortController` implements the timeout. Calling `controller.abort()` makes the pending `fetch` reject, which counts as a retryable failure. The `finally` block always clears the timer so that no stray timers stay alive.
- Only retry requests that are safe to repeat. Repeating a `GET` is harmless. Repeating a `POST` that creates an order may create two, unless the server supports an idempotency key.
- With `retries = 2` there are three attempts in total, which is why the last demo prints three failures before giving up.""")

# 5 ---------------------------------------------------------------------------------------------
ex("How do I group and summarise an array of objects in JavaScript (group by, sum, sort, format as currency)?",
   "Modern JavaScript has `Object.groupBy` and `Map.groupBy` (Node 21+ and current browsers). For older environments the same result comes from `reduce`. Then `map`, `sort` and `Intl.NumberFormat` produce the report.",
   r'''
const orders = [
  { id: 1, customer: 'Asha', total: 120.5, status: 'paid' },
  { id: 2, customer: 'Ben', total: 80, status: 'paid' },
  { id: 3, customer: 'Asha', total: 45.25, status: 'refunded' },
  { id: 4, customer: 'Cara', total: 300, status: 'paid' },
  { id: 5, customer: 'Ben', total: 19.99, status: 'paid' },
];

const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });

// 1) Built-in grouping.
const byStatus = Object.groupBy(orders, (o) => o.status);
console.log(Object.keys(byStatus), byStatus.paid.length);

// 2) The same grouping with reduce, for older runtimes.
const byCustomer = orders.reduce((groups, o) => {
  (groups[o.customer] ??= []).push(o);
  return groups;
}, {});

// 3) Sum per customer (paid orders only), sorted by total, largest first.
const report = Object.entries(byCustomer)
  .map(([customer, list]) => ({
    customer,
    orders: list.length,
    paid: list.filter((o) => o.status === 'paid').reduce((sum, o) => sum + o.total, 0),
  }))
  .sort((a, b) => b.paid - a.paid || a.customer.localeCompare(b.customer));

for (const row of report) {
  console.log(row.customer.padEnd(5), String(row.orders).padStart(2), money.format(row.paid).padStart(10));
}

const grand = report.reduce((sum, r) => sum + r.paid, 0);
console.log('total'.padEnd(5), ' ', money.format(grand).padStart(10));
''',
   """
Key points:
- `(groups[o.customer] ??= []).push(o)` uses the logical assignment operator: create the array only if the key is missing, then push into it. Before this syntax existed it was written as `groups[k] = groups[k] || []`.
- `reduce(fn, initialValue)`: always give the starting value. Without it, `reduce` on an empty array throws, and on a non-empty array it uses the first element as the start.
- The comparator `b.paid - a.paid || a.customer.localeCompare(b.customer)` sorts by the amount first, and the `||` runs the name comparison only when the difference is `0`.
- Never calculate with currency using floating point and then compare for exact equality. Sums of decimal fractions can print with a long tail of digits (`0.1 + 0.2` gives `0.30000000000000004`), which is one reason the report formats the numbers with `Intl.NumberFormat` before showing them. For real accounting store amounts in **cents** as integers.
- `padEnd` and `padStart` align the plain-text table. In the browser you would build a `<table>` instead and use the same data.""")

# 6 ---------------------------------------------------------------------------------------------
ex("How does a Redux-style state store work? Show me a minimal one in JavaScript without any library.",
   "A store holds one state object, changes it only through `dispatch(action)`, and calls the subscribers afterwards. The reducer is a pure function `(state, action) => newState` that never changes the old state.",
   r'''
function createStore(reducer, initialState) {
  let state = initialState;
  const listeners = new Set();
  return {
    getState: () => state,
    dispatch(action) {
      state = reducer(state, action);
      listeners.forEach((listener) => listener(state));
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}

function todos(state, action) {
  switch (action.type) {
    case 'add':
      return { ...state, items: [...state.items, { id: state.nextId, text: action.text, done: false }], nextId: state.nextId + 1 };
    case 'toggle':
      return { ...state, items: state.items.map((t) => (t.id === action.id ? { ...t, done: !t.done } : t)) };
    case 'remove':
      return { ...state, items: state.items.filter((t) => t.id !== action.id) };
    default:
      return state;
  }
}

const store = createStore(todos, { items: [], nextId: 1 });
const summary = (s) => s.items.map((t) => `${t.done ? '[x]' : '[ ]'} ${t.text}`).join(' | ') || '(no todos)';

const unsubscribe = store.subscribe((s) => console.log('changed ->', summary(s)));

store.dispatch({ type: 'add', text: 'buy milk' });
store.dispatch({ type: 'add', text: 'write code' });
const before = store.getState();
store.dispatch({ type: 'toggle', id: 1 });
console.log('old state object untouched:', before.items[0].done === false);
console.log('new state is a different object:', before !== store.getState());

unsubscribe();
store.dispatch({ type: 'remove', id: 2 });
console.log('silent change ->', summary(store.getState()));
''',
   """
Why this pattern is useful:
- All changes go through one function, so you can log every action, replay them, or undo, and a bug can only come from the reducer.
- A reducer must be **pure**: no `Date.now()`, no random numbers, no network calls, and no changing of the `state` argument. It builds new objects with spread (`{ ...state, ... }`) and with `map` and `filter`, which is why the old state (`before`) is still intact and the subscribers can compare old and new objects by reference.
- Spread is a **shallow** copy. In the `toggle` case only the changed todo and the arrays on the path to it are new, and the other todos are shared with the old state. That is cheap and safe as long as nobody mutates them.
- `subscribe` returns an unsubscribe function, as in the emitter example, and the last `dispatch` shows that an unsubscribed listener is not called any more.
- In real applications use Redux Toolkit, Zustand or the state tools of your framework. They add things this sketch lacks: middleware, selectors that avoid needless updates, and developer tools.""")

# 7 ---------------------------------------------------------------------------------------------
ex("How do I use regular expressions in JavaScript to parse a log line? Show named groups, matchAll and replace with a function.",
   "Named capture groups `(?<name>...)` make the result readable, `matchAll` iterates over every match, and `replace` accepts a function when the replacement has to be computed.",
   r'''
const line = '2026-11-12 09:41:07 ERROR [auth] user=asha ip=203.0.113.5 msg="token expired"';

const pattern = /^(?<date>\d{4}-\d{2}-\d{2}) (?<time>[\d:]{8}) (?<level>[A-Z]+) \[(?<module>\w+)\]/;
const { date, time, level, module } = line.match(pattern).groups;
console.log({ date, time, level, module });

// Every key=value pair, with quoted values allowed.
const pairs = {};
for (const m of line.matchAll(/(?<key>\w+)=(?:"(?<quoted>[^"]*)"|(?<plain>\S+))/g)) {
  pairs[m.groups.key] = m.groups.quoted ?? m.groups.plain;
}
console.log(pairs);

// replace with a function: mask the last octet of every IPv4 address.
const masked = line.replace(/\b(\d{1,3}\.\d{1,3}\.\d{1,3})\.\d{1,3}\b/g, (_, first3) => `${first3}.xxx`);
console.log(masked.slice(masked.indexOf('ip=')));

// Reuse the date with replace and $<name> to turn 2026-11-12 into 12/11/2026.
console.log(date.replace(/(?<y>\d{4})-(?<m>\d{2})-(?<d>\d{2})/, '$<d>/$<m>/$<y>'));

// test() with a global regex keeps state in lastIndex. A common trap.
const g = /error/g;
console.log(g.test('error one'), g.test('error one'), g.lastIndex);
''',
   """
Things to remember:
- `str.match(regex)` without the `g` flag returns one match object with `.groups`. With `g` it returns only the matched strings and no groups, which is why `matchAll` exists. `matchAll` requires the `g` flag and returns an iterator.
- `(?:...)` is a non-capturing group. It groups without creating a result slot. In the key=value pattern, `quoted` is `undefined` when the plain alternative matched, so `??` falls back to `plain`.
- In a replacement string `$<name>` inserts a named group, and `$1` a numbered one. A function replacement receives the whole match, then each group, so `(_, first3)` ignores the first argument.
- The last line shows the classic trap: a regex with the `g` (or `y`) flag remembers `lastIndex`, so the second `test` on the same string starts after the first match and returns `false`. Do not store global regexes in a shared variable when you use `test`; create it where you need it or leave the flag out.
- For parsing complicated formats (HTML, CSV with quotes, JSON) use a real parser. Regular expressions are fine for simple, well-defined line formats like this one.""")

# 8 ---------------------------------------------------------------------------------------------
ex("How do JavaScript classes work in modern syntax? Show private fields, getters, static members and inheritance.",
   "Here is a small bank-account example that uses everything: private state, a getter, validation, a static factory, a subclass and `toString`.",
   r'''
class Account {
  #balance = 0;
  static count = 0;

  constructor(owner, opening = 0) {
    this.owner = owner;
    if (opening > 0) this.deposit(opening);
    Account.count++;
  }

  get balance() {
    return this.#balance;
  }

  deposit(amount) {
    if (!Number.isFinite(amount) || amount <= 0) throw new RangeError('deposit must be a positive number');
    this.#balance += amount;
    return this;
  }

  withdraw(amount) {
    if (amount > this.#balance) throw new Error(`insufficient funds: balance ${this.#balance}, requested ${amount}`);
    this.#balance -= amount;
    return this;
  }

  static from(obj) {
    return new this(obj.owner, obj.balance);
  }

  toString() {
    return `${this.constructor.name}(${this.owner}: ${this.#balance})`;
  }
}

class Savings extends Account {
  constructor(owner, opening, rate) {
    super(owner, opening);
    this.rate = rate;
  }

  addInterest() {
    return this.deposit(this.balance * this.rate);
  }

  withdraw(amount) {
    if (amount > 500) throw new Error('savings withdrawals are limited to 500');
    return super.withdraw(amount);
  }
}

const a = new Account('Asha', 100).deposit(50).withdraw(30);
console.log(String(a), a.balance);

try { a.withdraw(1000); } catch (e) { console.log(e.message); }
try { a.deposit(-5); } catch (e) { console.log(e.name + ':', e.message); }

a.balance = 1_000_000;            // a getter without a setter: ignored (an error in strict mode)
console.log('after assignment:', a.balance);
console.log('has private field?', Object.keys(a), JSON.stringify(a));

const s = new Savings('Ben', 1000, 0.05).addInterest();
console.log(`${s}`, s instanceof Account);
try { s.withdraw(600); } catch (e) { console.log(e.message); }

const copy = Savings.from({ owner: 'Cara', balance: 20 });
console.log(String(copy), 'accounts created:', Account.count);
''',
   """
Notes:
- `#balance` is truly private: it is not in `Object.keys` or `JSON.stringify`, and outside code gets a `SyntaxError` if it writes `a.#balance`. A leading underscore (`_balance`) is only a convention that anything can ignore.
- A getter without a setter makes the property read-only. In a module or a class body (strict mode) the assignment `a.balance = ...` throws a `TypeError`; this demo file is a plain script, so it is silently ignored. Either way the balance cannot be changed from outside.
- `static` members belong to the class, not to the instances: `Account.count`. In a static method, `this` is the class that it was called on, which is why `new this(...)` in `from` creates a `Savings` when you call `Savings.from`.
- In a subclass constructor you must call `super(...)` before you use `this`. `super.withdraw(amount)` calls the parent's version, so the subclass can add a rule and reuse the rest.
- `return this` in `deposit` and `withdraw` allows chaining. `Number.isFinite` rejects `NaN` and `Infinity`, which `amount <= 0` alone would let through (`NaN <= 0` is `false`).
- Money in floating point has rounding errors, so a real application stores integer cents.""")

# 9 ---------------------------------------------------------------------------------------------
ex("How do I loop over a paginated API with async iterators in JavaScript?",
   "An async generator (`async function*`) hides the paging loop. The consumer simply writes `for await (const item of ...)` and can stop early with `break`, and the generator stops fetching new pages when it does.",
   r'''
// A fake API: 7 items, 3 per page.
const DATA = Array.from({ length: 7 }, (_, i) => ({ id: i + 1, name: `item-${i + 1}` }));
let requests = 0;
async function fetchPage(page, size = 3) {
  requests++;
  const start = (page - 1) * size;
  return { items: DATA.slice(start, start + size), hasMore: start + size < DATA.length };
}

async function* allItems() {
  let page = 1;
  while (true) {
    const { items, hasMore } = await fetchPage(page++);
    yield* items;
    if (!hasMore) return;
  }
}

async function main() {
  const ids = [];
  for await (const item of allItems()) ids.push(item.id);
  console.log('all ids:', ids, 'requests:', requests);

  requests = 0;
  const firstFour = [];
  for await (const item of allItems()) {
    firstFour.push(item.name);
    if (firstFour.length === 4) break; // the generator is closed, no further pages are fetched
  }
  console.log('first four:', firstFour, 'requests:', requests);

  // A reusable helper built on top of an async iterator.
  async function* take(iterable, n) {
    if (n <= 0) return;
    let i = 0;
    for await (const x of iterable) {
      yield x;
      if (++i >= n) return;
    }
  }
  requests = 0;
  const two = [];
  for await (const item of take(allItems(), 2)) two.push(item.id);
  console.log('take 2:', two, 'requests:', requests);
}
main();
''',
   """
Why async generators are nice for this:
- The paging details (page number, `hasMore`) stay inside the generator. The caller sees a plain stream of items and the same `for await` works for 7 or 7 million of them.
- Pages are fetched **lazily**. The next page is requested only when the loop asks for another item. That is why stopping after four items needed just two requests, and `take(allItems(), 2)` needed one.
- `yield* items` hands over every element of an array (or any iterable), one at a time.
- Leaving the loop with `break`, `return` or an exception calls the generator's `return()` method, so `finally` blocks inside the generator run and resources are released.
- Real APIs often return a cursor or a `next` URL instead of page numbers. The loop then keeps `let cursor = null` and ends when the response has no cursor.
- Node's `Readable` streams and the browser's `ReadableStream` are also async iterable, so the same `for await` loop reads a response body in chunks.""")

# 10 --------------------------------------------------------------------------------------------
ex("What are the most common JavaScript gotchas that surprise beginners? Show real examples.",
   "These are the cases that cause most real bugs. Every line below prints the actual result, so you do not have to trust my explanation.",
   r'''
console.log('1) typeof null:', typeof null, '| typeof [] :', typeof [], '| Array.isArray([]):', Array.isArray([]));
console.log('2) == vs ===  :', 0 == '', '0' == false, null == undefined, '| strict:', 0 === '', null === undefined);
console.log('3) 0.1 + 0.2  :', 0.1 + 0.2, '| equal to 0.3?', 0.1 + 0.2 === 0.3, '| close enough?', Math.abs(0.1 + 0.2 - 0.3) < Number.EPSILON);
console.log('4) default sort:', [10, 9, 1, 100].sort(), '| numeric:', [10, 9, 1, 100].sort((a, b) => a - b));
console.log('5) map(parseInt):', ['1', '2', '3'].map(parseInt), '| fixed:', ['1', '2', '3'].map(Number));
console.log('6) NaN        :', NaN === NaN, Number.isNaN(NaN), '| typeof NaN:', typeof NaN);
console.log('7) falsy 0    :', 0 || 'default', '| ??:', 0 ?? 'default', '| empty string ??:', JSON.stringify('' ?? 'default'));

var fns = [];
for (var i = 0; i < 3; i++) fns.push(() => i);
let fns2 = [];
for (let j = 0; j < 3; j++) fns2.push(() => j);
console.log('8) closures   : var ->', fns.map((f) => f()), '| let ->', fns2.map((f) => f()));

const original = { name: 'x', tags: ['a'], when: new Date(0), nothing: undefined };
const viaJson = JSON.parse(JSON.stringify(original));
const viaClone = structuredClone(original);
console.log('9) JSON clone :', viaJson);
console.log('   structuredClone keeps Date:', viaClone.when instanceof Date, '| JSON clone Date is a', typeof viaJson.when);

const copy = [...original.tags];
const shallow = { ...original };
shallow.tags.push('b');
console.log('10) shallow copy shares nested arrays:', original.tags, copy);

console.log('11) this lost  :', (() => { const o = { n: 1, get() { return this?.n; } }; const f = o.get; return [o.get(), f()]; })());
''',
   """
What each line teaches:
1. `typeof null` is `"object"`, an old mistake that was never fixed. Arrays are also `"object"`, so use `Array.isArray` and an explicit `x === null` check.
2. `==` converts types and gives strange results (`0 == ''` is `true`). Use `===` everywhere. The single useful exception is `x == null`, which is true for both `null` and `undefined`.
3. Binary floating point cannot store 0.1 exactly. Compare with a tolerance, and keep money in integer cents.
4. `sort()` without a comparator sorts **as strings**, so `100` comes before `9`. Always pass `(a, b) => a - b` for numbers. Also note that `sort` changes the array in place; use `toSorted()` (new in recent engines) or `[...arr].sort()` for a copy.
5. `map` passes `(value, index, array)` and `parseInt(value, radix)` takes the index as the radix, so `'2'` is parsed in base 1 (`NaN`) and `'3'` in base 2 (`NaN`).
6. `NaN` is not equal to itself. Use `Number.isNaN`, which, unlike the global `isNaN`, does not convert its argument first.
7. `||` replaces every falsy value (`0`, `''`, `false`), while `??` replaces only `null` and `undefined`. Use `??` for defaults when `0` or an empty string is a valid value.
8. `var` has one variable for the whole function, so all three closures see the final `3`. `let` creates a new variable for each iteration.
9. A JSON round trip drops `undefined` values and turns a `Date` into a string. `structuredClone` copies dates, maps, sets and nested objects correctly, but it cannot copy functions.
10. Spread (`{ ...obj }`) and `slice` copy only one level. The nested array is still shared, so a push through the copy shows up in the original.
11. A method pulled off its object loses `this`. Call it as `o.get()`, bind it (`o.get.bind(o)`) or use an arrow function inside the class.""")


def block(q, a):
    return f"@@@ USER\n{q}\n@@@ ASSISTANT\n{a}\n@@@ END\n\n"


OUT.write_text("".join(block(q, a) for q, a in EXAMPLES), encoding="utf-8")
print("wrote", OUT, len(EXAMPLES), "examples", OUT.stat().st_size, "bytes")

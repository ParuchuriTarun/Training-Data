"""Build data/staging/claude_longhorizon_expenses_17.txt from the REAL project files in proj/exp/ and the
REAL outputs in proj/exp/results.json (see exp_src.py)."""
import json
import re
from pathlib import Path

ROOT = Path(r"C:\Projects\Mavo\Coding 1 2B\data\staging\proj\exp")
OUT = Path(r"C:\Projects\Mavo\Coding 1 2B\data\staging\claude_longhorizon_expenses_17.txt")
F = "`" * 3
R = json.loads((ROOT / "results.json").read_text(encoding="utf-8"))


def rd(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def chunk(text, start, end, include_end=True):
    i = text.index(start)
    j = text.index(end, i)
    return text[i : j + (len(end) if include_end else 0)]


def code(lang, text):
    text = text.strip("\n")
    assert F not in text, "nested fence"
    return f"{F}{lang}\n{text}\n{F}"


def out(text):
    return code("", text)


def tests_view(text, keep_failures=False):
    """Test reporter output without the noisy assertion internals."""
    lines = []
    for line in text.splitlines():
        if re.match(r"\s+(generatedMessage|code|actual|expected|operator|diff):", line) or line.strip() == "}":
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def page_view(text):
    return "\n".join(l for l in text.splitlines() if not l.startswith("INFO csv"))


# ------------------------------------------------------------------------------ pieces from real files
v1_js, v1_test = rd("v1/expenses.js"), rd("v1/expenses.test.js")
v2_html, v2_css, v2_app = rd("v2/index.html"), rd("v2/style.css"), rd("v2/app.js")
v3_js, v3_test, v3_html, v3_app = rd("v3/expenses.js"), rd("v3/expenses.test.js"), rd("v3/index.html"), rd("v3/app.js")
v4_js, v4_test, v4_app = rd("v4/expenses.js"), rd("v4/expenses.test.js"), rd("v4/app.js")
v5_js, v5_test, v5_html, v5_app = rd("v5/expenses.js"), rd("v5/expenses.test.js"), rd("v5/index.html"), rd("v5/app.js")

v3_css_extra = chunk(rd("v3/style.css"), ".filter {", "}\n.sr-only {", include_end=False) + chunk(rd("v3/style.css"), ".sr-only {", "}\n")
v3_funcs = chunk(v3_js, "  function removeExpense", "  }\n\n  function sortNewestFirst") + chunk(v3_js, "  function sortNewestFirst", "  }\n")
v3_new_tests = v3_test[v3_test.index("test('removeExpense"):]
v3_return = chunk(v3_js, "  return {", "};")
NL = chr(10)
_css = rd("v3/style.css")
v3_css_extra = _css[_css.index(".filter {"):]
v3_funcs = v3_js[v3_js.index("  function removeExpense"):v3_js.index(NL + "  return {")].rstrip()
v3_html_filter = chunk(v3_html, '      <label class="filter">', "</label>\n")
v3_html_thead = chunk(v3_html, "        <thead>", "</thead>")

v4_valid = chunk(v4_js, "  // Data read back from storage", "\n  }\n")
v4_new_test = v4_test[v4_test.index("test('isValidExpense"):]
v4_return = chunk(v4_js, "  return {", "};")
v4_loader = chunk(v4_app, "  function backup(raw)", "  let expenses = loaded.list;\n")
v4_save = chunk(v4_app, "  function save() {", "\n  }\n")
v4_init = chunk(v4_app, "  showError(loaded.notice);", "  render();\n")

v5_csv = chunk(v5_js, "  function plainAmount", "\n  }\n\n  // Quote cells") + "\n" + chunk(v5_js, "  // Quote cells", "\n  }\n\n  function toCsv") + "\n\n" + chunk(v5_js, "  function toCsv", "\n  }\n")
v5_csv_naive = chunk(rd("v5a_naive_csv/expenses.js"), "  function toCsv", "\n  }\n")
v5_new_tests = v5_test[v5_test.index("const sample"):]
v5_return = chunk(v5_js, "  return {", "};")
v5_plain = chunk(v5_js, "  function plainAmount", NL + "  }" + NL)
v5_csv = v5_js[v5_js.index("  // Quote cells"):v5_js.index(NL + "  return {")].rstrip()
v5_button = chunk(v5_html, '      <button type="button" id="export">', "</button>\n")
v5_handler = chunk(v5_app, "  document.getElementById('export')", "  });\n")

# ------------------------------------------------------------------------------ the conversation
turns = []


def user(text):
    turns.append(("USER", text.strip()))


def assistant(*parts):
    turns.append(("ASSISTANT", "\n\n".join(p.strip("\n") for p in parts)))


# ---- turn 1 -------------------------------------------------------------------------------------
user("I want to build a small expense tracker web app with plain HTML, CSS and JavaScript. No framework and no build step, and I want it to be easy to test. Where do I start?")

assistant(
    """
Start with the part that has the rules, not with the page. A tracker is mostly rules: what is a valid amount, how are totals computed. If those live in plain functions with no DOM and no storage, you can test them in seconds with Node, and the page later becomes a thin layer on top.

The plan, in three layers:
1. **Logic** (`expenses.js`): pure functions that take data and return new data. Built and tested first.
2. **Page** (`index.html`, `style.css`, `app.js`): reads the form, calls the logic, draws the result.
3. **Storage**: saving to the browser. Added after the page works.

Two decisions that save pain later:
- **Money is stored as whole cents** (`1250` for $12.50). Floating point cannot represent 0.1 exactly, and sums of decimals drift (`0.1 + 0.2` is `0.30000000000000004`). With integers, totals are exact. Only `formatMoney` ever turns cents into text.
- **Functions never change their input.** `addExpense` returns a *new* list. That makes the code easy to reason about and easy to test, and the page can simply replace its list.

Step 1 is these two files. The file starts with a small wrapper so the same code works as a `<script>` in the browser (it creates `window.Expenses`) and with `require` in Node, so you never need a bundler.

`expenses.js`:""",
    code("js", v1_js),
    """
How the pieces work:
- `parseAmount` accepts `12.5` and `12,50` (some people type a decimal comma) and rejects `abc`, `-5`, `0`, `1.234` (three decimals) and `1e3`. It returns `null` for bad input instead of throwing, because bad user input is normal and not exceptional.
- `isRealDate` does not trust the regex alone: `2026-02-30` matches the pattern, but building a `Date` and converting back to text shows that it is not a real day.
- `addExpense` validates everything and throws an `Error` with a message that can be shown to the user. The new `id` is the highest existing id plus one.
- `totalsByCategory` relies on `addExpense` having refused unknown categories, so it needs no checks of its own.

Now the tests, using the test runner that is built into Node (no install needed). They are the specification of the rules above. `expenses.test.js`:""",
    code("js", v1_test),
    "Run them from the folder with both files:",
    code("bash", "node --test --test-reporter=spec expenses.test.js"),
    "I ran exactly that, and this is the output:",
    out(tests_view(R["v1_tests"])),
    """
All 7 pass. Notice the test `cents add up exactly where floats do not`: it first asserts that `0.1 + 0.2 !== 0.3` in JavaScript, so the reason for the design is checked by the test suite itself.

Next step, when you are ready: the page, with a form, a list and the totals per category.""",
)

# ---- turn 2 -------------------------------------------------------------------------------------
user("The tests pass, all 7. Now build the page: a form to add an expense, a list of the expenses, and totals per category.")

assistant(
    """
Here is the page. It has three files, and `expenses.js` stays exactly as it is. Put all of them in one folder.

`index.html` is the structure. The form has `novalidate` because the validation comes from `Expenses.addExpense`, so the rules live in one place and the messages are consistent:""",
    code("html", v2_html),
    "`style.css` is small and uses CSS variables so that the colours are easy to change. The form is a grid that wraps by itself on a narrow phone screen:",
    code("css", v2_css),
    """
`app.js` connects the logic to the page. It keeps the list in one variable, and `render()` redraws everything from that list:""",
    code("js", v2_app),
    """
Decisions worth knowing about:
- **`textContent`, never `innerHTML`.** The description is text that the user typed. Putting it in `innerHTML` would let someone enter `<img src=x onerror=...>` and run code. `textContent` shows it as plain text.
- **One source of truth.** The page never edits rows in place. Every change goes through `expenses = Expenses.addExpense(...)` and then `render()`. That is the main reason this stays simple as features are added.
- **`toLocaleDateString('en-CA')` for today's date.** That locale writes `2026-11-14`, the format the date input needs, and it uses your *local* date. The tempting `new Date().toISOString().slice(0, 10)` uses UTC, which gives yesterday's date late in the evening in a time zone east of Greenwich, such as India.
- **Errors go in the `#error` paragraph** (with `role="alert"` so screen readers announce it) and the list stays unchanged.

To use it, double-click `index.html`. You can't see my screen, so I tested it in headless Chrome with a script that fills in the form like a user and checks what ends up in the page. These are the results:""",
    out(page_view(R["v2_page"])),
    """
That includes the two checks that matter most for safety: the description `<img src=x onerror="window.__pwned=1">` is displayed as text, and no script ran.

Not yet done: the list disappears when you reload the page, and there is no way to remove an entry.""",
)

# ---- turn 3 -------------------------------------------------------------------------------------
user("Nice, it works. Now it should remember my expenses after I close the tab, let me delete an entry, and let me filter by month.")

assistant(
    """
Three features, and again the rules go into the logic file first. These pure functions are added to `expenses.js`, after `totalsByCategory`:""",
    code("js", v3_funcs),
    "and the returned object at the end of the file gets the new names:",
    code("js", v3_return),
    "Tests for them, appended to `expenses.test.js`:",
    code("js", v3_new_tests),
    "Test run:",
    out(tests_view(R["v3_tests"])),
    """
Now the page. In `index.html` add the month filter above the table, and a header cell for the delete buttons (the `sr-only` class hides the text visually but screen readers still read it):""",
    code("html", v3_html_filter + v3_html_thead),
    "Add this to the end of `style.css`:",
    code("css", v3_css_extra),
    "`app.js` is easier to read as a whole, so here is the complete new file:",
    code("js", v3_app),
    """
What changed and why:
- **Saving.** The list is stored as JSON in `localStorage` under one key (`expense-tracker:v1`). It is loaded once at startup and saved after every change. The `:v1` in the key leaves room to change the format later.
- **Delete uses one click listener on the table body** (event delegation). Each button carries `data-id`, and `event.target.closest('button[data-id]')` finds it, including buttons in rows that were added after the page loaded. This is better than attaching a listener to every row.
- **Filtering and sorting happen in `render()`**, not in the stored list. The stored list always contains everything, and the totals follow the filter because they are computed from the visible rows.
- `aria-label` on each button (`Delete Lunch`) lets screen-reader users tell the buttons apart.

I tested it in headless Chrome with data seeded in `localStorage`, as if from an earlier visit, then filtered, added and deleted entries:""",
    out(page_view(R["v3_page"])),
    "Everything is checked, including that the saved data changes when you add or delete.",
)

# ---- turn 4 -------------------------------------------------------------------------------------
user("Something broke. I was looking at Application > Local Storage in devtools and I edited the saved value by mistake. Now the list stays empty, and when I press Add the page just reloads and the fields end up in the address bar. When I put the value back by hand it works again, but a normal user could end up in the same situation some other way. Can you fix it properly?")

assistant(
    """
You found a real weakness, and your two symptoms point at the exact cause. Before changing anything I reproduced it. I seeded `localStorage` with three kinds of damaged data and ran the current page:
- `{oops` (not JSON at all),
- `{"a":1}` (valid JSON, but not a list),
- a list with one good record and two damaged ones (`cents` is the text `"abc"`, and a category called `__proto__`).

Results with the current code:""",
    code("", "garbage: {oops\n" + page_view(R["v3_bug_garbage"]) + "\n\nwrong shape: {\"a\":1}\n" + page_view(R["v3_bug_wrongshape"]) + "\n\ndamaged rows\n" + page_view(R["v3_bug_badrow"])),
    """
Why each one happens:
- **Not JSON.** `JSON.parse` throws while `app.js` is still running its first lines. An uncaught exception stops the whole script, so the submit listener is **never attached**. Without a listener, the browser does what forms do by default: it navigates to the same page with the fields in the address bar. That is exactly your symptom, and the list stays empty because `render()` never ran.
- **Wrong shape.** The JSON is valid, so `expenses` becomes the object `{a: 1}`, and the first call that expects a list (`list.reduce`, spread) fails. You see strange errors like `list.reduce is not a function` in the error box.
- **Damaged rows.** Nothing throws, but the page trusts the data and shows `$NaN.NaN` for the total.

The principle: **data read from storage is untrusted input**, just like text from a form. It can be edited, left over from an older version, or cut off when storage is full. So the rule is to check it at the boundary, and the app code after that can stay simple. Also, never silently destroy what you could not read, because it may be the user's only copy.

The fix has four parts.

**1. A validator in `expenses.js`** (with its test). The category check against the known list also blocks the `__proto__` trick:""",
    code("js", v4_valid),
    "Add it to the returned object:",
    code("js", v4_return),
    "Test, appended to `expenses.test.js`:",
    code("js", v4_new_test),
    "**2. A careful loader in `app.js`.** Replace the line `let expenses = JSON.parse(localStorage.getItem(STORAGE_KEY)) ?? [];` with this block:",
    code("js", v4_loader),
    "**3. A safer `save()`**, because writing can also fail (storage full, or blocked in private mode). Replace the old `save` with:",
    code("js", v4_save),
    "**4. Show the notice at startup.** At the end of `app.js`, where the file had only `render();`:",
    code("js", v4_init),
    """
How the loader behaves:
- Any failure (not JSON, not a list, even `localStorage` itself being blocked) ends in the `catch`, and the app starts with an empty list instead of crashing.
- Before anything can be overwritten, the raw text is copied to a second key (`expense-tracker:v1:backup`). Otherwise the next successful save would erase the only copy of the damaged data. A person (or a later feature) can still recover it.
- Rows that fail `isValidExpense` are skipped individually. The good ones are kept, and the notice says how many were dropped.
- The backup helper has its own `try/catch`, because the backup write can fail too, and an error inside a `catch` block would bring back the original crash.

Verification. Unit tests:""",
    out(tests_view(R["v4_tests"])),
    "The same three damaged-data cases with the fixed code:",
    code("", "garbage: {oops\n" + page_view(R["v4_fixed_garbage"]) + "\n\nwrong shape: {\"a\":1}\n" + page_view(R["v4_fixed_wrongshape"]) + "\n\ndamaged rows\n" + page_view(R["v4_fixed_badrow"])),
    "And the earlier page checks again, to make sure nothing else broke (this is why I keep these scripts):",
    out(page_view(R["v4_regression"])),
    """
For the `damaged rows` case the page shows the one good expense, the total is `$12.50`, and the notice appears. In every case the form works afterwards.""",
)

# ---- turn 5 -------------------------------------------------------------------------------------
user("Great, that feels solid now. Last thing for today: a button that downloads the expenses I am looking at as a CSV file, so I can open it in Excel.")

assistant(
    """
CSV looks trivial, and that is why it has two classic traps. I will write the tests first, to pin down what correct output is, and then show that the obvious first attempt fails them.

These tests go at the end of `expenses.test.js`. The sample data contains a comma, quotes, a line break and a formula, which are the awkward cases:""",
    code("js", v5_new_tests),
    "The obvious first attempt, which joins the fields with commas (it needs the small `plainAmount` helper that turns `1250` into `12.50` without floating point):",
    code("js", v5_plain.rstrip() + NL + NL + v5_csv_naive.rstrip()),
    "Run against it:",
    out(tests_view(R["v5_naive_tests"])),
    """
The two failures show the two traps:
1. **Quoting.** A description like `Coffee, "large"` contains a comma, so the row would have five columns instead of four. The CSV rule: wrap any cell that contains a comma, a quote or a line break in double quotes, and double every quote inside it (`""" + '"Coffee, ""large"""' + """`).
2. **Formula injection.** A cell that starts with `=`, `+`, `-` or `@` is run as a formula by Excel and similar programs. If someone gets text like `=HYPERLINK(...)` into a description, opening the export would execute it on your computer. The standard defence is to put a `'` in front of such cells so they are treated as text.

The fixed version (this replaces the naive `toCsv`, and the helper stays):""",
    code("js", v5_csv),
    "Add `toCsv` to the returned object:",
    code("js", v5_return),
    "Test run:",
    out(tests_view(R["v5_tests"])),
    """
Now the button. In `index.html`, next to the month filter:""",
    code("html", v5_button),
    "In `app.js`, after the `monthInput.addEventListener('input', render);` line:",
    code("js", v5_handler),
    """
It exports exactly what is visible, because it uses the same filter and sort as `render()`, and the file name includes the month when one is selected. The `Blob` and a temporary link make the browser download the file without a server. `URL.revokeObjectURL` frees the memory afterwards.

I tested the button in headless Chrome by replacing `URL.createObjectURL` to capture the file, with seeded data that included the awkward descriptions:""",
    out(page_view(R["v5_page"])),
    "And the earlier checks once more:",
    out(page_view(R["v5_regression"])),
    """
Where the project stands now:
- `expenses.js` has all rules and is covered by 14 tests. `app.js` only connects them to the page.
- Each feature was added the same way: pure function and test first, then the page, then a check in a real browser. When a bug appeared (damaged storage), I reproduced it first, then fixed it, and kept the check.

Possible next steps: editing an existing expense, a monthly summary by category, importing the CSV or a JSON backup, and a small chart. One note for the CSV: if you ever use non-English characters and Excel shows garbled text, start the file with the byte order mark (`'\\uFEFF'`), which helps Excel recognise UTF-8.""",
)

# ------------------------------------------------------------------------------ write
text = ""
for role, body in turns:
    text += f"@@@ {role}\n{body}\n"
text += "@@@ END\n\n"
OUT.write_text(text, encoding="utf-8")
print("wrote", OUT, len(turns), "turns", len(text), "chars")

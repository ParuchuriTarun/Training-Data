"""Expense tracker project: writes v1..v5 sources into proj/exp/, runs the Node tests and the headless-Chrome
page harnesses for every version, and stores the REAL outputs in proj/exp/results.json."""
import html
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(r"C:\Projects\Mavo\Coding 1 2B\data\staging\proj\exp")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
KEY = "expense-tracker:v1"


def put(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.lstrip("\n"), encoding="utf-8", newline="\n")


# =============================================================================== expenses.js
HEAD = r'''
// expenses.js - pure functions for the expense tracker. No DOM and no storage in here.
// Money is kept as whole cents, so 0.1 + 0.2 can never turn into 0.30000000000000004.
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.Expenses = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const CATEGORIES = ['food', 'transport', 'home', 'fun', 'other'];

  // "12.5" -> 1250, "12,50" -> 1250. Anything that is not a positive amount with at most 2 decimals -> null.
  function parseAmount(text) {
    const clean = String(text).trim().replace(',', '.');
    if (!/^\d+(\.\d{1,2})?$/.test(clean)) return null;
    const [whole, fraction = ''] = clean.split('.');
    const cents = Number(whole) * 100 + Number(fraction.padEnd(2, '0'));
    return cents > 0 ? cents : null;
  }

  function formatMoney(cents) {
    const sign = cents < 0 ? '-' : '';
    const abs = Math.abs(cents);
    const dollars = Math.floor(abs / 100).toLocaleString('en-US');
    return `${sign}$${dollars}.${String(abs % 100).padStart(2, '0')}`;
  }

  function isRealDate(text) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) return false;
    const d = new Date(text + 'T00:00:00Z');
    return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === text;
  }

  function addExpense(list, input) {
    const description = String(input.description ?? '').trim();
    if (!description) throw new Error('description is required');
    const cents = parseAmount(input.amount);
    if (cents === null) throw new Error('amount must be a positive number with at most 2 decimals');
    if (!CATEGORIES.includes(input.category)) throw new Error('unknown category: ' + input.category);
    if (!isRealDate(input.date)) throw new Error('date must be a real date like 2026-11-14');
    const id = list.reduce((max, e) => Math.max(max, e.id), 0) + 1;
    return [...list, { id, description, cents, category: input.category, date: input.date }];
  }

  function total(list) {
    return list.reduce((sum, e) => sum + e.cents, 0);
  }

  function totalsByCategory(list) {
    const totals = {};
    for (const e of list) totals[e.category] = (totals[e.category] ?? 0) + e.cents;
    return totals;
  }
'''

V3_FUNCS = r'''
  function removeExpense(list, id) {
    return list.filter((e) => e.id !== id);
  }

  // month looks like "2026-11"; an empty month means "everything".
  function filterByMonth(list, month) {
    return month ? list.filter((e) => e.date.startsWith(month)) : list;
  }

  function sortNewestFirst(list) {
    return [...list].sort((a, b) => b.date.localeCompare(a.date) || b.id - a.id);
  }
'''

V4_FUNCS = r'''
  // Data read back from storage is untrusted: check every field before the app uses it.
  function isValidExpense(e) {
    return (
      e !== null &&
      typeof e === 'object' &&
      Number.isInteger(e.id) && e.id > 0 &&
      typeof e.description === 'string' && e.description.trim() !== '' &&
      Number.isInteger(e.cents) && e.cents > 0 &&
      CATEGORIES.includes(e.category) &&
      isRealDate(e.date)
    );
  }
'''

CSV_NAIVE = r'''
  function toCsv(list) {
    const rows = list.map((e) => [e.date, e.description, e.category, plainAmount(e.cents)].join(','));
    return ['date,description,category,amount', ...rows].join('\r\n') + '\r\n';
  }
'''

CSV_FIXED = r'''
  // Quote cells that contain a comma, quote or line break, and defuse spreadsheet formulas.
  function csvCell(value) {
    let text = String(value);
    if (/^[=+\-@\t\r]/.test(text)) text = "'" + text;
    return /[",\r\n]/.test(text) ? '"' + text.replace(/"/g, '""') + '"' : text;
  }

  function toCsv(list) {
    const header = ['date', 'description', 'category', 'amount'];
    const rows = list.map((e) => [e.date, e.description, e.category, plainAmount(e.cents)].map(csvCell));
    return [header, ...rows].map((row) => row.join(',')).join('\r\n') + '\r\n';
  }
'''

PLAIN = r'''
  function plainAmount(cents) {
    return Math.floor(cents / 100) + '.' + String(cents % 100).padStart(2, '0');
  }
'''


def expenses_js(version, csv="none"):
    body = HEAD
    exports = ["CATEGORIES", "parseAmount", "formatMoney", "addExpense", "total", "totalsByCategory"]
    if version >= 3:
        body += V3_FUNCS
        exports += ["removeExpense", "filterByMonth", "sortNewestFirst"]
    if version >= 4:
        body += V4_FUNCS
        exports += ["isValidExpense"]
    if csv != "none":
        body += PLAIN + (CSV_NAIVE if csv == "naive" else CSV_FIXED)
        exports += ["toCsv"]
    body += "\n  return { " + ", ".join(exports) + " };\n});\n"
    return body


# =============================================================================== tests
TEST_HEAD = r'''
const test = require('node:test');
const assert = require('node:assert/strict');
const E = require('./expenses.js');

const base = { description: 'Lunch', amount: '12.50', category: 'food', date: '2026-11-10' };
'''

TEST_V1 = r'''
test('parseAmount accepts normal amounts and comma decimals', () => {
  assert.equal(E.parseAmount('12.5'), 1250);
  assert.equal(E.parseAmount('12,50'), 1250);
  assert.equal(E.parseAmount(' 7 '), 700);
  assert.equal(E.parseAmount('0.05'), 5);
});

test('parseAmount rejects everything else', () => {
  for (const bad of ['', 'abc', '-5', '0', '0.00', '1.234', '1e3', '12.', '.5']) {
    assert.equal(E.parseAmount(bad), null, `should reject ${JSON.stringify(bad)}`);
  }
});

test('cents add up exactly where floats do not', () => {
  assert.notEqual(0.1 + 0.2, 0.3);
  assert.equal(E.parseAmount('0.1') + E.parseAmount('0.2'), E.parseAmount('0.3'));
});

test('formatMoney', () => {
  assert.equal(E.formatMoney(1250), '$12.50');
  assert.equal(E.formatMoney(5), '$0.05');
  assert.equal(E.formatMoney(123456789), '$1,234,567.89');
});

test('addExpense returns a new list and numbers the ids', () => {
  const one = E.addExpense([], base);
  const two = E.addExpense(one, { ...base, description: 'Bus' });
  assert.equal(one.length, 1);
  assert.deepEqual(two.map((e) => e.id), [1, 2]);
  assert.equal(two[0].cents, 1250);
});

test('addExpense rejects bad input with clear messages', () => {
  assert.throws(() => E.addExpense([], { ...base, description: '   ' }), /description is required/);
  assert.throws(() => E.addExpense([], { ...base, amount: 'abc' }), /amount must be/);
  assert.throws(() => E.addExpense([], { ...base, category: 'boats' }), /unknown category: boats/);
  assert.throws(() => E.addExpense([], { ...base, date: '2026-02-30' }), /real date/);
  assert.throws(() => E.addExpense([], { ...base, date: '10/11/2026' }), /real date/);
});

test('total and totalsByCategory', () => {
  let list = E.addExpense([], base);
  list = E.addExpense(list, { ...base, amount: '3,40', category: 'transport' });
  list = E.addExpense(list, { ...base, amount: '8.60' });
  assert.equal(E.total(list), 2450);
  assert.deepEqual(E.totalsByCategory(list), { food: 2110, transport: 340 });
});
'''

TEST_V3 = r'''
test('removeExpense returns a new list without that id', () => {
  const list = E.addExpense(E.addExpense([], base), base);
  const next = E.removeExpense(list, 1);
  assert.deepEqual(next.map((e) => e.id), [2]);
  assert.equal(list.length, 2);
});

test('filterByMonth keeps one month, and an empty month keeps everything', () => {
  let list = E.addExpense([], base);
  list = E.addExpense(list, { ...base, date: '2026-10-30' });
  assert.deepEqual(E.filterByMonth(list, '2026-11').map((e) => e.date), ['2026-11-10']);
  assert.equal(E.filterByMonth(list, '').length, 2);
});

test('sortNewestFirst orders by date, then id, and leaves the input alone', () => {
  let list = E.addExpense([], { ...base, date: '2026-11-01' });
  list = E.addExpense(list, { ...base, date: '2026-11-09' });
  list = E.addExpense(list, { ...base, date: '2026-11-09' });
  assert.deepEqual(E.sortNewestFirst(list).map((e) => e.id), [3, 2, 1]);
  assert.deepEqual(list.map((e) => e.id), [1, 2, 3]);
});
'''

TEST_V4 = r'''
test('isValidExpense accepts a good record and rejects damaged ones', () => {
  const good = { id: 1, description: 'Lunch', cents: 1250, category: 'food', date: '2026-11-10' };
  assert.equal(E.isValidExpense(good), true);
  const bad = [
    null, [], {}, 'text', 5,
    { ...good, id: 0 },
    { ...good, description: '  ' },
    { ...good, cents: '1250' },
    { ...good, cents: 0 },
    { ...good, cents: 12.5 },
    { ...good, category: '__proto__' },
    { ...good, date: '2026-02-30' },
  ];
  for (const record of bad) {
    assert.equal(E.isValidExpense(record), false, `should reject ${JSON.stringify(record)}`);
  }
});
'''

TEST_V5 = r'''
const sample = [
  { id: 1, description: 'Lunch', cents: 1250, category: 'food', date: '2026-11-10' },
  { id: 2, description: 'Coffee, "large"', cents: 405, category: 'food', date: '2026-11-11' },
  { id: 3, description: '=HYPERLINK("http://evil.example","click")', cents: 100, category: 'other', date: '2026-11-12' },
  { id: 4, description: 'Two\nlines', cents: 7, category: 'home', date: '2026-11-13' },
];

test('toCsv writes a header, plain amounts and CRLF line ends', () => {
  const csv = E.toCsv(sample.slice(0, 1));
  assert.equal(csv, 'date,description,category,amount\r\n2026-11-10,Lunch,food,12.50\r\n');
});

test('toCsv quotes commas, quotes and line breaks', () => {
  const lines = E.toCsv(sample).split('\r\n');
  assert.equal(lines[2], '2026-11-11,"Coffee, ""large""",food,4.05');
  assert.ok(E.toCsv(sample).includes('"Two\nlines"'));
});

test('toCsv defuses cells that a spreadsheet would run as a formula', () => {
  const line = E.toCsv(sample).split('\r\n')[3];
  assert.ok(line.startsWith("2026-11-12,\"'=HYPERLINK("), line);
});
'''


def test_js(version, with_csv):
    t = TEST_HEAD + TEST_V1
    if version >= 3:
        t += TEST_V3
    if version >= 4:
        t += TEST_V4
    if with_csv:
        t += TEST_V5
    return t


# =============================================================================== page
def index_html(filter_ui=False, export_ui=False):
    filt = ""
    if filter_ui:
        filt = '      <label class="filter">Month <input type="month" id="month-filter"></label>\n'
    exp = ""
    if export_ui:
        exp = '      <button type="button" id="export">Download CSV</button>\n'
    actions_th = '<th><span class="sr-only">Actions</span></th>' if filter_ui else ""
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Expense tracker</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <main>
    <h1>Expense tracker</h1>

    <form id="expense-form" novalidate>
      <label>Description <input name="description" autocomplete="off" required></label>
      <label>Amount <input name="amount" inputmode="decimal" placeholder="12.50" required></label>
      <label>Category <select name="category"></select></label>
      <label>Date <input name="date" type="date" required></label>
      <button type="submit">Add</button>
    </form>
    <p id="error" role="alert" hidden></p>

    <section aria-labelledby="list-title">
      <h2 id="list-title">Expenses</h2>
{filt}{exp}      <table>
        <thead><tr><th>Date</th><th>Description</th><th>Category</th><th class="num">Amount</th>{actions_th}</tr></thead>
        <tbody id="list"></tbody>
      </table>
      <p id="empty">No expenses yet.</p>
    </section>

    <section aria-labelledby="totals-title">
      <h2 id="totals-title">Totals</h2>
      <ul id="totals"></ul>
      <p>Total: <strong id="grand-total">$0.00</strong></p>
    </section>
  </main>
  <script src="expenses.js"></script>
  <script src="app.js"></script>
</body>
</html>
'''


STYLE_V2 = r'''
:root {
  --bg: #f6f7f9;
  --card: #ffffff;
  --text: #1c2430;
  --muted: #5b6676;
  --line: #dde2ea;
  --accent: #2459d6;
  --error: #b3261e;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font: 16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif;
}

main {
  max-width: 44rem;
  margin: 0 auto;
  padding: 1.5rem 1rem 3rem;
}

h1 { margin: 0 0 1rem; font-size: 1.6rem; }
h2 { margin: 2rem 0 0.5rem; font-size: 1.1rem; color: var(--muted); }

form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
  gap: 0.75rem;
  align-items: end;
  padding: 1rem;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 0.5rem;
}

label { display: grid; gap: 0.25rem; font-size: 0.85rem; color: var(--muted); }

input, select, button {
  font: inherit;
  padding: 0.5rem 0.6rem;
  border: 1px solid var(--line);
  border-radius: 0.4rem;
}

button {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
  cursor: pointer;
}

#error { color: var(--error); margin: 0.5rem 0 0; }

table { width: 100%; border-collapse: collapse; background: var(--card); }
th, td { padding: 0.5rem 0.6rem; border-bottom: 1px solid var(--line); text-align: left; }
th { font-size: 0.8rem; color: var(--muted); font-weight: 600; }
.num { text-align: right; font-variant-numeric: tabular-nums; }

#totals { margin: 0 0 0.5rem; padding-left: 1.2rem; }
'''

STYLE_V3_EXTRA = r'''
.filter { display: inline-grid; margin-bottom: 0.5rem; }
td button { background: transparent; color: var(--error); border-color: var(--line); padding: 0.2rem 0.5rem; }
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}
'''

APP_V2 = r'''
(function () {
  const form = document.getElementById('expense-form');
  const errorBox = document.getElementById('error');
  const listBody = document.getElementById('list');
  const emptyNote = document.getElementById('empty');
  const totalsList = document.getElementById('totals');
  const grandTotal = document.getElementById('grand-total');

  let expenses = [];

  for (const name of Expenses.CATEGORIES) {
    form.elements.category.append(new Option(name, name));
  }
  // The local date, not toISOString(): that one is UTC and shows yesterday late in the evening east of Greenwich.
  form.elements.date.value = new Date().toLocaleDateString('en-CA');

  function cell(text, className) {
    const td = document.createElement('td');
    td.textContent = text; // textContent, never innerHTML: what the user typed must stay text
    if (className) td.className = className;
    return td;
  }

  function render() {
    const rows = expenses.map((e) => {
      const tr = document.createElement('tr');
      tr.append(cell(e.date), cell(e.description), cell(e.category), cell(Expenses.formatMoney(e.cents), 'num'));
      return tr;
    });
    listBody.replaceChildren(...rows);
    emptyNote.hidden = expenses.length > 0;

    const totals = Object.entries(Expenses.totalsByCategory(expenses)).sort((a, b) => b[1] - a[1]);
    totalsList.replaceChildren(
      ...totals.map(([category, cents]) => {
        const li = document.createElement('li');
        li.textContent = `${category}: ${Expenses.formatMoney(cents)}`;
        return li;
      })
    );
    grandTotal.textContent = Expenses.formatMoney(Expenses.total(expenses));
  }

  function showError(message) {
    errorBox.textContent = message;
    errorBox.hidden = !message;
  }

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    try {
      expenses = Expenses.addExpense(expenses, Object.fromEntries(new FormData(form)));
    } catch (err) {
      showError(err.message);
      return;
    }
    showError('');
    form.elements.description.value = '';
    form.elements.amount.value = '';
    form.elements.description.focus();
    render();
  });

  render();
})();
'''

APP_V3 = r'''
(function () {
  const STORAGE_KEY = 'expense-tracker:v1';

  const form = document.getElementById('expense-form');
  const errorBox = document.getElementById('error');
  const listBody = document.getElementById('list');
  const emptyNote = document.getElementById('empty');
  const totalsList = document.getElementById('totals');
  const grandTotal = document.getElementById('grand-total');
  const monthInput = document.getElementById('month-filter');

  let expenses = JSON.parse(localStorage.getItem(STORAGE_KEY)) ?? [];

  for (const name of Expenses.CATEGORIES) {
    form.elements.category.append(new Option(name, name));
  }
  form.elements.date.value = new Date().toLocaleDateString('en-CA');

  function save() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(expenses));
  }

  function cell(text, className) {
    const td = document.createElement('td');
    td.textContent = text;
    if (className) td.className = className;
    return td;
  }

  function rowFor(e) {
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.dataset.id = String(e.id);
    remove.textContent = 'Delete';
    remove.setAttribute('aria-label', `Delete ${e.description}`);
    const actions = document.createElement('td');
    actions.append(remove);

    const tr = document.createElement('tr');
    tr.append(cell(e.date), cell(e.description), cell(e.category), cell(Expenses.formatMoney(e.cents), 'num'), actions);
    return tr;
  }

  function render() {
    const visible = Expenses.sortNewestFirst(Expenses.filterByMonth(expenses, monthInput.value));
    listBody.replaceChildren(...visible.map(rowFor));
    emptyNote.hidden = visible.length > 0;
    emptyNote.textContent = expenses.length === 0 ? 'No expenses yet.' : 'Nothing in this month.';

    const totals = Object.entries(Expenses.totalsByCategory(visible)).sort((a, b) => b[1] - a[1]);
    totalsList.replaceChildren(
      ...totals.map(([category, cents]) => {
        const li = document.createElement('li');
        li.textContent = `${category}: ${Expenses.formatMoney(cents)}`;
        return li;
      })
    );
    grandTotal.textContent = Expenses.formatMoney(Expenses.total(visible));
  }

  function showError(message) {
    errorBox.textContent = message;
    errorBox.hidden = !message;
  }

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    try {
      expenses = Expenses.addExpense(expenses, Object.fromEntries(new FormData(form)));
    } catch (err) {
      showError(err.message);
      return;
    }
    showError('');
    form.elements.description.value = '';
    form.elements.amount.value = '';
    form.elements.description.focus();
    save();
    render();
  });

  // One listener on the table body handles every Delete button, including rows added later.
  listBody.addEventListener('click', (event) => {
    const button = event.target.closest('button[data-id]');
    if (!button) return;
    expenses = Expenses.removeExpense(expenses, Number(button.dataset.id));
    save();
    render();
  });

  monthInput.addEventListener('input', render);

  render();
})();
'''

LOAD_NAIVE = "  let expenses = JSON.parse(localStorage.getItem(STORAGE_KEY)) ?? [];\n"

LOAD_FIXED = r'''  function backup(raw) {
    try {
      localStorage.setItem(STORAGE_KEY + ':backup', raw);
    } catch {
      /* storage is full or blocked: nothing more we can do */
    }
  }

  function loadExpenses() {
    let raw = null;
    try {
      raw = localStorage.getItem(STORAGE_KEY);
      if (raw === null) return { list: [], notice: '' };
      const data = JSON.parse(raw);
      if (!Array.isArray(data)) throw new Error('saved data is not a list');
      const list = data.filter(Expenses.isValidExpense);
      const skipped = data.length - list.length;
      if (skipped > 0) backup(raw);
      return { list, notice: skipped > 0 ? `${skipped} damaged expense(s) in the saved data were skipped.` : '' };
    } catch {
      if (raw !== null) backup(raw);
      return { list: [], notice: 'The saved data could not be read, so the list starts empty. The old text was kept as a backup in this browser.' };
    }
  }

  const loaded = loadExpenses();
  let expenses = loaded.list;
'''

SAVE_NAIVE = r'''  function save() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(expenses));
  }
'''

SAVE_FIXED = r'''  function save() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(expenses));
    } catch {
      showError('Could not save in this browser (storage is full or blocked). The list will be lost when you close the page.');
    }
  }
'''

EXPORT_JS = r'''
  document.getElementById('export').addEventListener('click', () => {
    const visible = Expenses.sortNewestFirst(Expenses.filterByMonth(expenses, monthInput.value));
    const blob = new Blob([Expenses.toCsv(visible)], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = monthInput.value ? `expenses-${monthInput.value}.csv` : 'expenses.csv';
    link.click();
    URL.revokeObjectURL(url);
  });

'''


def app_v4():
    s = APP_V3.replace(LOAD_NAIVE, LOAD_FIXED).replace(SAVE_NAIVE, SAVE_FIXED)
    assert LOAD_FIXED in s and SAVE_FIXED in s
    # show the notice from loading once the helpers exist
    s = s.replace("  monthInput.addEventListener('input', render);\n\n  render();\n",
                  "  monthInput.addEventListener('input', render);\n\n  showError(loaded.notice);\n  render();\n")
    assert "showError(loaded.notice);" in s
    return s


def app_v5():
    s = app_v4()
    marker = "  monthInput.addEventListener('input', render);\n"
    assert marker in s
    return s.replace(marker, marker + EXPORT_JS.rstrip("\n") + "\n")


# =============================================================================== harness
COMMON = r'''
(function () {
  const lines = [];
  window.check = function (name, ok, detail) {
    lines.push((ok ? 'PASS ' : 'FAIL ') + name + (!ok && detail ? '  [' + detail + ']' : ''));
  };
  window.info = function (text) { lines.push('INFO ' + text); };
  window.finish = function () { document.getElementById('out').textContent = lines.join('\n'); };
})();
'''

H2 = r'''
const form = document.getElementById('expense-form');
const rows = () => [...document.querySelectorAll('#list tr')].map((tr) => [...tr.children].map((td) => td.textContent).slice(0, 4));
const fill = (v) => { for (const [k, x] of Object.entries(v)) form.elements[k].value = x; };
const add = (v) => { fill(v); form.requestSubmit(); };
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

check('starts empty and shows the note', rows().length === 0 && !document.getElementById('empty').hidden);
check('date field starts on a real date', /^\d{4}-\d{2}-\d{2}$/.test(form.elements.date.value), form.elements.date.value);

add({ description: 'Lunch', amount: '12.5', category: 'food', date: '2026-11-10' });
check('adds a row', same(rows(), [['2026-11-10', 'Lunch', 'food', '$12.50']]), JSON.stringify(rows()));
check('hides the empty note', document.getElementById('empty').hidden);
check('clears description and amount', form.elements.description.value === '' && form.elements.amount.value === '');

add({ description: 'Bus', amount: '3,40', category: 'transport', date: '2026-11-11' });
add({ description: 'Pizza', amount: '8.60', category: 'food', date: '2026-11-12' });
const totals = [...document.querySelectorAll('#totals li')].map((li) => li.textContent);
check('totals per category, biggest first', same(totals, ['food: $21.10', 'transport: $3.40']), JSON.stringify(totals));
check('grand total', document.getElementById('grand-total').textContent === '$24.50', document.getElementById('grand-total').textContent);

add({ description: 'Oops', amount: 'abc', category: 'food', date: '2026-11-12' });
const err = document.getElementById('error');
check('a bad amount shows an error and adds no row', !err.hidden && /amount/.test(err.textContent) && rows().length === 3, err.textContent);

add({ description: '<img src=x onerror="window.__pwned=1">', amount: '1', category: 'other', date: '2026-11-12' });
check('the error disappears after a good entry', err.hidden);
check('HTML in a description stays plain text', document.querySelectorAll('#list img').length === 0 && rows().some((r) => r[1].startsWith('<img')));
check('no script ran from that text', window.__pwned === undefined);
check('no page errors', window.__errors.length === 0, window.__errors.join('; '));
finish();
'''

SEED_VALID = [
    {"id": 1, "description": "Lunch", "cents": 1250, "category": "food", "date": "2026-11-10"},
    {"id": 2, "description": "Taxi", "cents": 800, "category": "transport", "date": "2026-10-30"},
    {"id": 3, "description": "Pizza", "cents": 860, "category": "food", "date": "2026-11-12"},
]

H3 = r'''
const form = document.getElementById('expense-form');
const month = document.getElementById('month-filter');
const rows = () => [...document.querySelectorAll('#list tr')].map((tr) => [...tr.children].map((td) => td.textContent).slice(0, 4));
const stored = () => JSON.parse(localStorage.getItem('expense-tracker:v1') || 'null');
const fill = (v) => { for (const [k, x] of Object.entries(v)) form.elements[k].value = x; };
const add = (v) => { fill(v); form.requestSubmit(); };
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const names = () => rows().map((r) => r[1]);

check('saved data from an earlier visit is shown, newest first', same(names(), ['Pizza', 'Lunch', 'Taxi']), JSON.stringify(names()));
check('grand total covers everything', document.getElementById('grand-total').textContent === '$29.10', document.getElementById('grand-total').textContent);

month.value = '2026-11';
month.dispatchEvent(new Event('input', { bubbles: true }));
check('month filter keeps November only', same(names(), ['Pizza', 'Lunch']), JSON.stringify(names()));
check('totals follow the filter', document.getElementById('grand-total').textContent === '$21.10', document.getElementById('grand-total').textContent);

month.value = '2026-09';
month.dispatchEvent(new Event('input', { bubbles: true }));
check('an empty month shows a different note', !document.getElementById('empty').hidden && /Nothing in this month/.test(document.getElementById('empty').textContent), document.getElementById('empty').textContent);

month.value = '';
month.dispatchEvent(new Event('input', { bubbles: true }));
add({ description: 'Movie', amount: '15', category: 'fun', date: '2026-11-13' });
check('a new expense goes to the top', names()[0] === 'Movie' && rows().length === 4, JSON.stringify(names()));
check('and is saved', stored().length === 4 && stored()[3].cents === 1500, JSON.stringify(stored()));

const lunchButton = [...document.querySelectorAll('#list tr')].find((tr) => tr.children[1].textContent === 'Lunch').querySelector('button');
lunchButton.click();
check('Delete removes exactly that row', same(names(), ['Movie', 'Pizza', 'Taxi']), JSON.stringify(names()));
check('and updates what is saved', same(stored().map((e) => e.description).sort(), ['Movie', 'Pizza', 'Taxi']), JSON.stringify(stored()));
check('no page errors', window.__errors.length === 0, window.__errors.join('; '));
finish();
'''

H4 = r'''
const form = document.getElementById('expense-form');
const rows = () => [...document.querySelectorAll('#list tr')].map((tr) => tr.children[1].textContent);
const expect = window.__expect;
const error = document.getElementById('error');

// If nothing in the app handles the submit, the browser would reload the page with the fields in the URL.
let pageWouldReload = false;
document.addEventListener('submit', (e) => { if (!e.defaultPrevented) { pageWouldReload = true; e.preventDefault(); } });

check('no page errors', window.__errors.length === 0, window.__errors.join('; '));
check('shows ' + expect.rows + ' saved row(s)', rows().length === expect.rows, 'found ' + rows().length);
check('total is ' + expect.total, document.getElementById('grand-total').textContent === expect.total, document.getElementById('grand-total').textContent);
check('a notice is ' + (expect.notice ? 'shown' : 'not shown'), (!error.hidden) === expect.notice, 'hidden=' + error.hidden);
check('the old text is ' + (expect.backup ? 'kept as a backup' : 'not copied'), (localStorage.getItem('expense-tracker:v1:backup') !== null) === expect.backup);

form.elements.description.value = 'New one';
form.elements.amount.value = '5';
form.elements.category.value = 'home';
form.elements.date.value = '2026-11-14';
form.requestSubmit();
check('the form still works afterwards', rows().includes('New one') && !pageWouldReload, pageWouldReload ? 'Add reloads the page instead' : JSON.stringify(rows()));
if (!error.hidden) info('notice text: ' + error.textContent);
finish();
'''

H5 = r'''
const captured = { blobs: [], names: [] };
URL.createObjectURL = (blob) => { captured.blobs.push(blob); return 'blob:fake'; };
URL.revokeObjectURL = () => {};
HTMLAnchorElement.prototype.click = function () { captured.names.push(this.download); };

const month = document.getElementById('month-filter');
document.getElementById('export').click();

(async () => {
  const csv = await captured.blobs[0].text();
  check('one file was offered, named expenses.csv', captured.names.length === 1 && captured.names[0] === 'expenses.csv', JSON.stringify(captured.names));
  const lines = csv.split('\r\n');
  check('header line', lines[0] === 'date,description,category,amount', lines[0]);
  check('newest expense first', lines[1].startsWith('2026-11-13,'), lines[1]);
  check('comma and quotes are escaped', csv.includes('"Coffee, ""large"""'));
  check('formula is defused', csv.includes('"\'=HYPERLINK('), JSON.stringify(csv));
  check('ends with a line break', csv.endsWith('\r\n'));

  month.value = '2026-10';
  month.dispatchEvent(new Event('input', { bubbles: true }));
  document.getElementById('export').click();
  const octoberCsv = await captured.blobs[1].text();
  check('the month filter applies to the export and the file name', captured.names[1] === 'expenses-2026-10.csv' && octoberCsv.split('\r\n').length === 3, JSON.stringify(captured.names[1]) + ' ' + JSON.stringify(octoberCsv));
  check('no page errors', window.__errors.length === 0, window.__errors.join('; '));
  info('csv: ' + JSON.stringify(csv));
  finish();
})();
'''

SEED_EXPORT = SEED_VALID + [
    {"id": 4, "description": 'Coffee, "large"', "cents": 405, "category": "food", "date": "2026-11-13"},
    {"id": 5, "description": '=HYPERLINK("http://evil.example","click")', "cents": 100, "category": "other", "date": "2026-11-11"},
]

SEED_BADROW = [
    {"id": 1, "description": "Lunch", "cents": 1250, "category": "food", "date": "2026-11-10"},
    {"id": 2, "description": "Broken", "cents": "abc", "category": "food", "date": "2026-11-11"},
    {"id": 3, "description": "Sneaky", "cents": 500, "category": "__proto__", "date": "2026-11-12"},
]


def make_page(vdir, name, harness_js, seed=None, expect=None):
    page = (vdir / "index.html").read_text(encoding="utf-8")
    pre = '<script>window.__errors=[];window.addEventListener("error",function(e){window.__errors.push(e.message)});'
    if seed is not None:
        pre += f'localStorage.setItem("{KEY}", {json.dumps(seed)});'
    if expect is not None:
        pre += f"window.__expect={json.dumps(expect)};"
    pre += "</script>\n  "
    page = page.replace('<script src="expenses.js"></script>', pre + '<script src="expenses.js"></script>')
    page = page.replace("</body>", f'<pre id="out"></pre>\n  <script src="harness_common.js"></script>\n  <script src="{name}.js"></script>\n</body>')
    put(vdir / f"{name}.html", page)
    put(vdir / f"{name}.js", harness_js)
    put(vdir / "harness_common.js", COMMON)
    return vdir / f"{name}.html"


def chrome(page):
    ud = tempfile.mkdtemp()
    proc = subprocess.Popen(
        [CHROME, "--headless=new", "--disable-gpu", "--no-first-run", "--allow-file-access-from-files",
         f"--user-data-dir={ud}", "--virtual-time-budget=4000", "--dump-dom", page.as_uri()],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
    try:
        stdout, stderr = proc.communicate(timeout=45)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
        stdout, stderr = proc.communicate()
        stdout = "TIMEOUT " + (stdout or "")
    m = re.search(r'<pre id="out">(.*?)</pre>', stdout, re.S)
    shutil.rmtree(ud, ignore_errors=True)
    return html.unescape(m.group(1)) if m else "NO OUTPUT: " + stdout[:300] + (stderr or "")[:300]


def node_tests(vdir):
    p = subprocess.run(["node", "--test", "--test-reporter=spec", "expenses.test.js"], cwd=vdir,
                       capture_output=True, text=True, encoding="utf-8", timeout=90)
    out = (p.stdout + p.stderr).replace("\r", "")
    out = re.sub(r"\s*\(\d+(\.\d+)?ms\)", "", out)
    keep = []
    for line in out.splitlines():
        if re.match(r"ℹ (cancelled|skipped|todo|duration_ms)", line):
            continue
        if re.match(r"\s+at ", line) or str(vdir) in line:
            continue
        keep.append(line)
    return "\n".join(keep).strip()


def main():
    if ROOT.exists():
        shutil.rmtree(ROOT)
    res = {}

    v1, v2, v3, v4, v5, v5a = (ROOT / n for n in ("v1", "v2", "v3", "v4", "v5", "v5a_naive_csv"))

    put(v1 / "expenses.js", expenses_js(1))
    put(v1 / "expenses.test.js", test_js(1, False))
    res["v1_tests"] = node_tests(v1)

    put(v2 / "expenses.js", expenses_js(1))
    put(v2 / "index.html", index_html())
    put(v2 / "style.css", STYLE_V2)
    put(v2 / "app.js", APP_V2)
    res["v2_page"] = chrome(make_page(v2, "harness2", H2))

    put(v3 / "expenses.js", expenses_js(3))
    put(v3 / "expenses.test.js", test_js(3, False))
    put(v3 / "index.html", index_html(filter_ui=True))
    put(v3 / "style.css", STYLE_V2 + STYLE_V3_EXTRA)
    put(v3 / "app.js", APP_V3)
    res["v3_tests"] = node_tests(v3)
    res["v3_page"] = chrome(make_page(v3, "harness3", H3, seed=json.dumps(SEED_VALID)))

    # the same seeds against the naive loader (v3) and the fixed loader (v4)
    cases = {
        "garbage": ("{oops", dict(rows=0, total="$0.00", notice=True, backup=True)),
        "wrongshape": ('{"a":1}', dict(rows=0, total="$0.00", notice=True, backup=True)),
        "badrow": (json.dumps(SEED_BADROW), dict(rows=1, total="$12.50", notice=True, backup=True)),
    }
    for name, (seed, exp) in cases.items():
        res[f"v3_bug_{name}"] = chrome(make_page(v3, f"harness4_{name}", H4, seed=seed, expect=exp))

    put(v4 / "expenses.js", expenses_js(4))
    put(v4 / "expenses.test.js", test_js(4, False))
    put(v4 / "index.html", index_html(filter_ui=True))
    put(v4 / "style.css", STYLE_V2 + STYLE_V3_EXTRA)
    put(v4 / "app.js", app_v4())
    res["v4_tests"] = node_tests(v4)
    for name, (seed, exp) in cases.items():
        res[f"v4_fixed_{name}"] = chrome(make_page(v4, f"harness4_{name}", H4, seed=seed, expect=exp))
    res["v4_regression"] = chrome(make_page(v4, "harness3", H3, seed=json.dumps(SEED_VALID)))

    # CSV: first the naive version (tests must fail), then the fixed one
    put(v5a / "expenses.js", expenses_js(4, csv="naive"))
    put(v5a / "expenses.test.js", test_js(4, True))
    res["v5_naive_tests"] = node_tests(v5a)

    put(v5 / "expenses.js", expenses_js(4, csv="fixed"))
    put(v5 / "expenses.test.js", test_js(4, True))
    put(v5 / "index.html", index_html(filter_ui=True, export_ui=True))
    put(v5 / "style.css", STYLE_V2 + STYLE_V3_EXTRA)
    put(v5 / "app.js", app_v5())
    res["v5_tests"] = node_tests(v5)
    res["v5_page"] = chrome(make_page(v5, "harness5", H5, seed=json.dumps(SEED_EXPORT)))
    res["v5_regression"] = chrome(make_page(v5, "harness3", H3, seed=json.dumps(SEED_VALID)))

    (ROOT / "results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    for k, v in res.items():
        print(f"===== {k}\n{v}\n")


main()

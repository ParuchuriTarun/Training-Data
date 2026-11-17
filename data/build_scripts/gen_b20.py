"""Build data/staging/claude_html_css_20.txt. Every page is loaded in headless Chrome, a hidden probe script measures
the real layout / DOM / computed styles, and those real numbers are pasted into the answer."""
import html as htmllib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

F = "`" * 3
OUT = Path(r"C:\Projects\Mavo\Coding 1 2B\data\staging\claude_html_css_20.txt")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
EXAMPLES = []
VERSION = []

HELPERS = "var r = function (x) { return Math.round(x * 10) / 10; };\n"


def chrome_probe(page, probe_js, width):
    d = Path(tempfile.mkdtemp())
    wrapped = page.replace(
        "</body>",
        "<script>window.addEventListener('load', function () { setTimeout(function () {\n"
        "var out; try { out = (function () {\n" + HELPERS + probe_js + "\n})(); } catch (e) { out = { error: String(e) }; }\n"
        "var pre = document.createElement('pre'); pre.id = '__probe'; pre.textContent = JSON.stringify(out);\n"
        "document.documentElement.appendChild(pre);\n"
        "}, 100); });</script></body>",
    )
    assert wrapped != page, "page needs a </body>"
    f = d / "page.html"
    f.write_text(wrapped, encoding="utf-8")
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-first-run", "--allow-file-access-from-files",
           f"--user-data-dir={d / 'profile'}", f"--window-size={width},700", "--virtual-time-budget=4000",
           "--dump-dom", f.as_uri()]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
    try:
        out, _ = p.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
        print("CHROME TIMEOUT"); sys.exit(1)
    m = re.search(r'<pre id="__probe">(.*?)</pre>', out, re.S)
    if not m:
        print("NO PROBE RESULT\n", out[-800:]); sys.exit(1)
    data = json.loads(htmllib.unescape(m.group(1)))
    if "error" in data:
        print("PROBE ERROR", data); sys.exit(1)
    return data


def fmt(data):
    return "\n".join(f"{k}: {json.dumps(v) if not isinstance(v, (int, float, str)) else v}" for k, v in data.items())


def ex(question, intro, variants, probe_js, after, widths=(800,), note=None):
    """variants: list of (label or None, html)."""
    parts = [intro.strip()]
    log = []
    for label, page in variants:
        code = page.strip()
        assert F not in code
        parts.append((f"**{label}**\n\n" if label else "") + f"{F}html\n{code}\n{F}")
        blocks = []
        for w in widths:
            res = chrome_probe(page, probe_js, w)
            head = f"[window {res.get('innerWidth', w)} px wide]" if len(widths) > 1 else ""
            blocks.append((head + "\n" if head else "") + fmt({k: v for k, v in res.items() if k != "innerWidth"}))
        shown = "\n\n".join(blocks)
        what = (note or "I loaded the page in headless Chrome and measured it") + (f" ({label})" if label else "")
        parts.append(f"{what}:\n\n{F}\n{shown}\n{F}")
        log.append(shown)
    parts.append(after.strip())
    EXAMPLES.append((question, "\n\n".join(parts)))
    print(f"---- example {len(EXAMPLES)} ----\n" + "\n\n".join(log) + "\n")


HEAD = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
{css}
</style>
</head>
<body>
{body}
</body>
</html>'''


def page(title, css, body):
    return HEAD.format(title=title, css=css.strip("\n"), body=body.strip("\n"))


# 1 ---------------------------------------------------------------------------------------------
CENTER_CSS_GRID = '''
  * { box-sizing: border-box; }
  body {
    margin: 0;
    min-height: 100vh;
    display: grid;
    place-items: center;
    font-family: system-ui, sans-serif;
    background: #f3f4f6;
  }
  .card { width: 320px; padding: 24px; background: white; border-radius: 12px; }
'''
CENTER_CSS_FLEX = '''
  * { box-sizing: border-box; }
  body {
    margin: 0;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: system-ui, sans-serif;
    background: #f3f4f6;
  }
  .card { width: 320px; padding: 24px; background: white; border-radius: 12px; }
'''
CARD = '<div class="card"><h1>Hello</h1><p>This card is centered.</p></div>'
ex("How do I center a card both horizontally and vertically in the middle of the page with CSS?",
   "Make the `body` a full-height grid (or flex) container and let it center its child. The grid version needs two lines, `display: grid` and `place-items: center`. The key detail is `min-height: 100vh`: without a height, the body is only as tall as its content and there is nothing to center in vertically. Both versions are below.",
   [("Grid", page("Centered card", CENTER_CSS_GRID, CARD)), ("Flexbox", page("Centered card", CENTER_CSS_FLEX, CARD))],
   '''
   var c = document.querySelector('.card').getBoundingClientRect();
   return {
     innerWidth: innerWidth,
     "card width": r(c.width),
     "card height": r(c.height),
     "distance from the left edge": r(c.left),
     "distance from the right edge": r(innerWidth - c.right),
     "distance from the top": r(c.top),
     "distance from the bottom": r(innerHeight - c.bottom)
   };
   ''',
   "In both layouts the distances on opposite sides are equal, so the card is centered in both directions. Use grid when there is exactly one thing to center, and flexbox when you also want to lay out several children in a row or column. Do not use `height: 100vh` on mobile if the content can be taller than the screen; `min-height` lets the page grow instead of cutting the content. Newer browsers also have `100dvh`, which follows the visible area when the address bar shows or hides.")

# 2 ---------------------------------------------------------------------------------------------
TILES = "\n".join(f'  <div class="tile">Tile {i}</div>' for i in range(1, 7))
GRID_CSS = '''
  * { box-sizing: border-box; }
  body { margin: 0; padding: 16px; font-family: system-ui, sans-serif; }
  .grid {
    display: grid;
    gap: 16px;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  }
  .tile { background: #dbeafe; padding: 24px; border-radius: 8px; text-align: center; }
'''
ex("How do I make a responsive card grid that changes the number of columns by itself, without media queries?",
   "Use `repeat(auto-fit, minmax(160px, 1fr))` for `grid-template-columns`. It means: make as many columns as fit, each at least 160 px wide, and share the leftover space equally (`1fr`). When the window gets narrower, columns drop out and the tiles wrap to the next row.",
   [(None, page("Responsive grid", GRID_CSS, '<div class="grid">\n' + TILES + '\n</div>'))],
   '''
   var tiles = Array.prototype.slice.call(document.querySelectorAll('.tile'));
   var lefts = {}, tops = {};
   tiles.forEach(function (t) { var b = t.getBoundingClientRect(); lefts[Math.round(b.left)] = 1; tops[Math.round(b.top)] = 1; });
   return {
     innerWidth: innerWidth,
     columns: Object.keys(lefts).length,
     rows: Object.keys(tops).length,
     "first tile width": r(tiles[0].getBoundingClientRect().width)
   };
   ''',
   "The same CSS gives 2 columns in the narrow window and 4 in the wide one (the available width is the window minus 32 px of padding), and the tile width always stays at least 160 px. `auto-fit` collapses empty columns, so with few tiles they stretch to fill the row; use `auto-fill` instead when you want the empty columns to stay and the tiles to keep a fixed maximum size (combine it with a `max-width` in `minmax` such as `minmax(160px, 220px)`). The `gap` replaces the old trick of margins on every tile.",
   widths=(400, 900),
   note="I loaded the page in headless Chrome at two window widths and counted the columns")

# 3 ---------------------------------------------------------------------------------------------
STICKY_BASE = '''
  * { box-sizing: border-box; }
  body { margin: 0; font-family: system-ui, sans-serif; }
  .site-header { position: sticky; top: 0; background: #1e293b; color: white; padding: 16px; }
  .content { height: 2000px; padding: 16px; }
'''
STICKY_BODY = '''
<header class="site-header">My site</header>
<main class="content">Long content</main>
'''
STICKY_WRAP_BODY = '''
<div class="page">
  <header class="site-header">My site</header>
  <main class="content">Long content</main>
</div>
'''
ex("My position: sticky header does not stick. It scrolls away with the page. What is wrong?",
   "`position: sticky` sticks to the nearest ancestor that scrolls. If any ancestor has `overflow: hidden`, `auto` or `scroll` (including `overflow-x: hidden`, which people add to stop sideways scrolling), that ancestor becomes the scroll container, it does not actually scroll, and the header never sticks. Three versions, each scrolled down by 500 px with `window.scrollTo(0, 500)`, and the distance of the header from the top of the window measured afterwards:",
   [("1. Header directly in the page", page("Sticky", STICKY_BASE, STICKY_BODY)),
    ("2. Header inside a wrapper with overflow-x: hidden", page("Sticky", STICKY_BASE + "  .page { overflow-x: hidden; }", STICKY_WRAP_BODY)),
    ("3. The same wrapper with overflow-x: clip", page("Sticky", STICKY_BASE + "  .page { overflow-x: clip; }", STICKY_WRAP_BODY))],
   '''
   window.scrollTo(0, 500);
   var h = document.querySelector('.site-header').getBoundingClientRect();
   return { innerWidth: innerWidth, "scrolled by": window.scrollY, "header top after scrolling": r(h.top) };
   ''',
   "In version 2 the header scrolled out of view (negative top). `overflow-x: clip` hides the overflow in the same way but, unlike `hidden`, does not create a scroll container, so sticky works again (version 3). If you cannot use `clip`, remove the `overflow` from the ancestors that contain the sticky element, and put it on a different element that does not contain it. Also remember that a sticky element needs a `top`, `bottom`, `left` or `right` value to know where to stick.",
   note="Measured in headless Chrome")

# 4 ---------------------------------------------------------------------------------------------
ELL_CSS = '''
  * { box-sizing: border-box; }
  body { margin: 16px; font-family: system-ui, sans-serif; }
  .row {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 300px;
    padding: 8px;
    border: 1px solid #cbd5e1;
    margin-bottom: 12px;
  }
  .title {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .badge { flex: none; background: #16a34a; color: white; padding: 2px 8px; border-radius: 999px; }
'''
ELL_BODY = '''
<div class="row" id="broken">
  <div class="col"><div class="title">A very long file name that does not fit into the row.txt</div></div>
  <span class="badge">new</span>
</div>
'''
ex("My long text with text-overflow: ellipsis inside a flex row does not get cut off. It pushes the other items out of the box. How do I fix it?",
   "A flex item has `min-width: auto`, which means it will not shrink below the width of its content. When the ellipsis is on a child, the flex item around it (`.col` here) keeps the full text width, so the row overflows and the ellipsis never appears. Fix it with `min-width: 0` on that flex item. The measurements below compare the broken row with the fixed one.",
   [("Broken", page("Ellipsis in flex", ELL_CSS, ELL_BODY)),
    ("Fixed with min-width: 0 on .col", page("Ellipsis in flex", ELL_CSS + "  .col { min-width: 0; }", ELL_BODY))],
   '''
   var row = document.querySelector('.row'), col = document.querySelector('.col'), title = document.querySelector('.title'), badge = document.querySelector('.badge');
   var rb = row.getBoundingClientRect(), bb = badge.getBoundingClientRect();
   return {
     innerWidth: innerWidth,
     "row width": r(rb.width),
     "col width": r(col.getBoundingClientRect().width),
     "title is cut off (scrollWidth > clientWidth)": title.scrollWidth > title.clientWidth,
     "badge right edge minus row right edge": r(bb.right - rb.right)
   };
   ''',
   "In the broken version the `col` is as wide as the whole text, the title is not cut, and the badge sits far outside the row (a large positive number). With `min-width: 0` the column shrinks to the space that is left, the text is cut with an ellipsis, and the badge stays inside the row (the last number is -9: its right edge is 9 px inside the row's outer edge, which is the 8 px padding plus the 1 px border). The same rule applies to grid items (`min-width: 0` or `minmax(0, 1fr)` for the columns). A flex item that itself has `overflow: hidden` does not have this problem, because its automatic minimum size is 0.",
   note="Measured in headless Chrome")

# 5 ---------------------------------------------------------------------------------------------
THEME_PAGE = page("Theme switch", '''
  :root { --bg: #ffffff; --fg: #111827; --accent: #2563eb; }
  [data-theme="dark"] { --bg: #0f172a; --fg: #e2e8f0; --accent: #60a5fa; }
  body { margin: 0; padding: 24px; background: var(--bg); color: var(--fg); font-family: system-ui, sans-serif; }
  button { background: var(--accent); color: var(--bg); border: 0; padding: 8px 16px; border-radius: 6px; cursor: pointer; }
''', '''
<h1>Theme demo</h1>
<button id="toggle" type="button" aria-pressed="false">Dark mode</button>
<script>
  var root = document.documentElement;
  var button = document.getElementById('toggle');

  function apply(theme) {
    root.dataset.theme = theme;
    button.setAttribute('aria-pressed', String(theme === 'dark'));
  }

  var saved = null;
  try { saved = localStorage.getItem('theme'); } catch (e) {}
  apply(saved || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));

  button.addEventListener('click', function () {
    var next = root.dataset.theme === 'dark' ? 'light' : 'dark';
    apply(next);
    try { localStorage.setItem('theme', next); } catch (e) {}
  });
</script>
''')
ex("How do I build a light/dark theme switch with CSS variables that remembers the choice?",
   "Put every color in CSS custom properties on `:root`, override them under `[data-theme=\"dark\"]`, and use `var(--name)` everywhere else. The switch then only changes one attribute on `<html>`. The script chooses the starting theme from the saved value, or from the system setting (`prefers-color-scheme`) when nothing is saved, and the `try/catch` keeps the page working when `localStorage` is blocked.",
   [(None, THEME_PAGE)],
   '''
   var btn = document.getElementById('toggle');
   var bg = function () { return getComputedStyle(document.body).backgroundColor; };
   var before = bg(), attrBefore = btn.getAttribute('aria-pressed');
   btn.click();
   var after = bg(), attrAfter = btn.getAttribute('aria-pressed'), savedTheme = localStorage.getItem('theme');
   btn.click();
   return {
     innerWidth: innerWidth,
     "system prefers dark": matchMedia('(prefers-color-scheme: dark)').matches,
     "background at start": before,
     "aria-pressed at start": attrBefore,
     "background after one click": after,
     "aria-pressed after one click": attrAfter,
     "saved theme after one click": savedTheme,
     "background after a second click": bg()
   };
   ''',
   "The page starts in the theme that matches the system setting (the first line shows that this system prefers dark, so the page started dark). The first click switches to the other theme, flips `aria-pressed` and stores the choice; the second click switches back. Using `aria-pressed` tells screen readers that the button is a toggle and in which state it is. To avoid a flash of the wrong theme when the page loads, keep the small `apply(...)` script in the `<head>` (before the body is painted) instead of at the end. When you start from `prefers-color-scheme`, you can also listen to its `change` event so the page follows the system setting while the user has not chosen a theme.",
   note="I loaded the page in headless Chrome, simulated two clicks on the button and read the computed background color")

# 6 ---------------------------------------------------------------------------------------------
BOX_CSS = '''
  body { margin: 16px; font-family: system-ui, sans-serif; }
  .container { width: 300px; background: #e2e8f0; margin-bottom: 12px; }
  input { width: 100%; padding: 20px; border: 2px solid #475569; display: block; }
'''
BOX_BODY = '''
<div class="container"><input id="field" value="width: 100%"></div>
'''
ex("Why is my input with width: 100% wider than its container?",
   "By default (`box-sizing: content-box`) `width` is only the width of the content. Padding and border are added on top, so `width: 100%` plus 20 px padding and a 2 px border on each side is wider than 100%. Set `box-sizing: border-box` so that `width` includes the padding and the border. Most projects set it once for every element.",
   [("Default box model", page("Box model", BOX_CSS, BOX_BODY)),
    ("With box-sizing: border-box", page("Box model", "  *, *::before, *::after { box-sizing: border-box; }\n" + BOX_CSS, BOX_BODY))],
   '''
   var c = document.querySelector('.container').getBoundingClientRect();
   var i = document.getElementById('field').getBoundingClientRect();
   return {
     innerWidth: innerWidth,
     "container width": r(c.width),
     "input width": r(i.width),
     "input sticks out on the right by": r(i.right - c.right)
   };
   ''',
   "With the default box model the input is 344 px wide in a 300 px container: 300 content + 2 × 20 padding + 2 × 2 border. With `border-box` it is exactly 300. The `*, *::before, *::after` selector also covers the generated content, which `*` alone does not.",
   note="Measured in headless Chrome")

# 7 ---------------------------------------------------------------------------------------------
FORM_PAGE = page("Sign-up form", '''
  * { box-sizing: border-box; }
  body { font-family: system-ui, sans-serif; padding: 24px; max-width: 360px; }
  label { display: block; margin-top: 12px; font-weight: 600; }
  input { width: 100%; padding: 8px; border: 2px solid #94a3b8; border-radius: 6px; }
  .was-validated input:invalid { border-color: #dc2626; }
  .was-validated input:valid { border-color: #16a34a; }
  #status { margin-top: 12px; min-height: 1.5em; }
''', '''
<form id="signup" novalidate>
  <label for="email">Email</label>
  <input id="email" name="email" type="email" required autocomplete="email">
  <label for="password">Password (at least 8 characters)</label>
  <input id="password" name="password" type="password" required minlength="8" autocomplete="new-password">
  <button type="submit">Create account</button>
  <p id="status" role="status"></p>
</form>
<script>
  var form = document.getElementById('signup');
  var statusEl = document.getElementById('status');

  form.addEventListener('submit', function (event) {
    event.preventDefault();                       // we handle the submit ourselves
    form.classList.add('was-validated');
    if (!form.checkValidity()) {
      var first = form.querySelector(':invalid');
      statusEl.textContent = first.validationMessage;
      first.focus();
      return;
    }
    statusEl.textContent = 'Account created for ' + form.email.value;
  });
</script>
''')
ex("How do I validate a sign-up form with the browser's built-in validation, show red and green borders, and focus the first wrong field?",
   "Use the HTML attributes (`type=\"email\"`, `required`, `minlength`) and let the browser do the checking. Add `novalidate` to the form so that the browser does not show its own pop-up and your script controls the timing: on submit, call `form.checkValidity()`, add a class to the form, and style `:invalid` and `:valid` only below that class, so the fields do not turn red before the user has tried to submit. `validationMessage` gives you a ready-made, translated error text.",
   [(None, FORM_PAGE)],
   '''
   var form = document.getElementById('signup');
   var email = form.email, pw = form.password, st = document.getElementById('status');
   var border = function (el) { return getComputedStyle(el).borderTopColor; };
   var out = { innerWidth: innerWidth, "border before submit": border(email) };
   email.value = 'anna.example.com'; pw.value = '';
   form.requestSubmit();
   out["after a bad submit: email border"] = border(email);
   out["after a bad submit: focused field"] = document.activeElement.id;
   out["after a bad submit: message"] = st.textContent;
   email.value = 'anna@example.com';
   form.requestSubmit();
   out["after the email is fixed: focused field"] = document.activeElement.id;
   out["after the email is fixed: message"] = st.textContent;
   pw.value = 'long-enough-1';
   form.requestSubmit();
   out["after both are fixed: password border"] = border(pw);
   out["after both are fixed: message"] = st.textContent;
   return out;
   ''',
   "The messages come from the browser, so they follow the user's language. A detail I met while testing this page: `minlength` is only checked for values that the user typed; a value set from a script (like in my test) skips that check, which is why the test leaves the password empty to trigger `required` instead. Remember that this is only a convenience for the user: the server must check the data again, because anyone can send a request without your form. If you want your own wording, read `email.validity.typeMismatch`, `valueMissing` or `tooShort` and write the text yourself. In the script the variable is called `statusEl` because a global `var status` collides with `window.status`, which only stores strings (my first version silently did nothing for that reason). Keep the `<label for=...>` connected to each input so that clicking the label focuses the field and screen readers announce it.",
   note="I loaded the page in headless Chrome and submitted the form three times from a script: first with bad values, then with one field fixed, then with both fixed")

# 8 ---------------------------------------------------------------------------------------------
SVG = ("data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='400'%3E"
       "%3Crect width='400' height='400' fill='%2338bdf8'/%3E%3Ccircle cx='200' cy='200' r='120' fill='%230369a1'/%3E%3C/svg%3E")
RATIO_PAGE = page("Aspect ratio", '''
  * { box-sizing: border-box; }
  body { margin: 16px; font-family: system-ui, sans-serif; }
  .video { width: 320px; aspect-ratio: 16 / 9; background: #0f172a; margin-bottom: 12px; }
  .thumb { width: 200px; height: 100px; object-fit: cover; display: block; }
''', f'''
<div class="video"></div>
<img class="thumb" alt="Blue circle" src="{SVG}">
''')
ex("How do I keep a box in a 16:9 shape, and how do I put a square image into a wide box without stretching it?",
   "`aspect-ratio: 16 / 9` lets the browser compute the height from the width, so you do not need the old padding-top hack. For images, `object-fit: cover` fills the box and crops the overflow, while the default (`fill`) stretches the image. Here a 400 × 400 image is shown in a 200 × 100 box.",
   [(None, RATIO_PAGE)],
   '''
   var v = document.querySelector('.video').getBoundingClientRect();
   var img = document.querySelector('.thumb'), ib = img.getBoundingClientRect();
   var out = {
     innerWidth: innerWidth,
     "video box": r(v.width) + " x " + r(v.height),
     "image file size": img.naturalWidth + " x " + img.naturalHeight,
     "image box": r(ib.width) + " x " + r(ib.height),
     "object-fit": getComputedStyle(img).objectFit
   };
   img.style.objectFit = 'fill';
   out["with object-fit: fill the image box is still"] = r(img.getBoundingClientRect().width) + " x " + r(img.getBoundingClientRect().height);
   return out;
   ''',
   "The video box is 320 × 180, which is exactly 16:9. The image box stays 200 × 100 in both cases; `object-fit` does not change the box, it changes how the picture is placed inside it. With `cover` the picture is scaled to 200 × 200 and only the middle 100 px of its height are shown; with `fill` the whole square is squeezed into the wide box and looks distorted. Use `contain` when nothing may be cropped, and `object-position` to choose which part stays visible with `cover`. Always give `<img>` a `width` and `height` or an `aspect-ratio`, so the page does not jump when the image loads.",
   note="Measured in headless Chrome")

# 9 ---------------------------------------------------------------------------------------------
STACK_CSS = '''
  * { box-sizing: border-box; }
  body { margin: 0; font-family: system-ui, sans-serif; }
  .nav { position: relative; height: 50px; background: #1e293b; color: white; padding: 12px; }
  .menu { position: absolute; top: 50px; left: 0; width: 200px; height: 100px; z-index: 9999; background: #f59e0b; }
  .hero { position: relative; z-index: 1; height: 300px; background: #bae6fd; }
'''
STACK_BODY = '''
<nav class="nav" id="nav">Nav<div class="menu" id="menu">Menu</div></nav>
<section class="hero" id="hero">Hero</section>
'''
ex("My dropdown menu has z-index: 9999 but it still appears behind the next section. Why?",
   "`z-index` only competes with other elements inside the same stacking context. Some properties create a new stacking context on an element: `opacity` below 1, `transform`, `filter`, `position` with a `z-index` value, and more. Everything inside it is then ranked as one group, so the 9999 of the menu counts only inside its parent. To see what is really on top, the script asks the browser which element is at one point of the overlap with `document.elementFromPoint`. Three versions:",
   [("1. Normal: the menu is on top", page("Stacking", STACK_CSS, STACK_BODY)),
    ("2. The nav has opacity: 0.99, which creates a stacking context", page("Stacking", STACK_CSS + "  .nav { opacity: 0.99; }", STACK_BODY)),
    ("3. Fix: give the nav its own z-index above the hero", page("Stacking", STACK_CSS + "  .nav { opacity: 0.99; z-index: 2; }", STACK_BODY))],
   '''
   var el = document.elementFromPoint(100, 100);   // inside the menu area and inside the hero
   return { innerWidth: innerWidth, "element on top at point (100, 100)": el.id };
   ''',
   "In version 2 the hero (`z-index: 1`) is above the whole nav, including its menu, because the nav with `opacity` and no `z-index` is ranked at level 0 as one block. In version 3 the nav forms a stacking context of level 2, which is higher than the hero's 1, so its menu is on top again, and the 9999 is not needed at all. When a z-index does not work, look at the ancestors of the element for `opacity`, `transform`, `filter`, `will-change`, `position: fixed` or `sticky`, and `isolation: isolate`. A small z-index scale (1, 10, 100) kept in CSS variables avoids the 9999 race.",
   note="Measured in headless Chrome")

# ------------------------------------------------------------------------------ write
text = ""
for q, a in EXAMPLES:
    text += f"@@@ USER\n{q}\n@@@ ASSISTANT\n{a}\n@@@ END\n\n"
OUT.write_text(text, encoding="utf-8")
print("wrote", OUT, len(EXAMPLES), "examples", len(text), "chars")

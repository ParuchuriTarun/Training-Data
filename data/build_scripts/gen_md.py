"""Builds claude_longhorizon_markdown_12.txt from the tested pieces in md_pieces.py."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import md_pieces as P  # noqa: E402

F = "`" * 3
v1, v2, v3, v4 = (P.assemble(P.VERSIONS[k]) for k in ("v1", "v2", "v3", "v4"))


def code(lang, text):
    import re
    longest = max([len(m) for m in re.findall(r"`+", text)] + [0])
    fence = "`" * max(3, longest + 1)  # a block that contains ``` needs a longer fence around it
    return f"{fence}{lang}\n{text.rstrip()}\n{fence}"


def tests_block(text):
    return "#[cfg(test)]\nmod tests {\n    use super::*;\n\n" + text.rstrip("\n") + "\n}"


def check(snippet, source):
    assert snippet.strip() in source, "snippet is not part of the tested source:\n" + snippet[:200]
    return snippet


def indent_free(s):
    return s.strip("\n")


# ---------------------------------------------------------------- snippets for step 4 (checked against v4)
OPENS = check('''/// True when the marker of `len` characters at `at` may open emphasis: text must follow it directly.
fn opens_emphasis(chars: &[char], at: usize, len: usize) -> bool {
    chars.get(at + len).map_or(false, |c| !c.is_whitespace())
}

/// Index of the marker that closes emphasis: it must not follow a space, the text must not be empty,
/// and a single `*` must not be part of a `**` pair.
fn find_closing(chars: &[char], from: usize, pat: &str) -> Option<usize> {
    let mut start = from;
    while let Some(pos) = find_seq(chars, start, pat) {
        let in_pair = pat == "*" && (chars.get(pos + 1) == Some(&'*') || chars[pos - 1] == '*');
        if pos > from && !chars[pos - 1].is_whitespace() && !in_pair {
            return Some(pos);
        }
        start = pos + 1;
    }
    None
}''', v4)

BRANCHES = check('''        if c == '*' && chars.get(i + 1) == Some(&'*') && opens_emphasis(&chars, i, 2) {
            if let Some(end) = find_closing(&chars, i + 2, "**") {
                let inner: String = chars[i + 2..end].iter().collect();
                out.push_str(&format!("<strong>{}</strong>", render_inline(&inner)));
                i = end + 2;
                continue;
            }
        }

        if c == '*' && chars.get(i + 1) != Some(&'*') && opens_emphasis(&chars, i, 1) {
            if let Some(end) = find_closing(&chars, i + 1, "*") {
                let inner: String = chars[i + 1..end].iter().collect();
                out.push_str(&format!("<em>{}</em>", render_inline(&inner)));
                i = end + 1;
                continue;
            }
        }''', v4)

RENDER_ARMS = check('''            Block::List(items) => render_list(&mut out, "ul", items),
            Block::Ordered(items) => render_list(&mut out, "ol", items),
            Block::Quote(text) => {
                out.push_str(&format!("<blockquote>\\n  <p>{}</p>\\n</blockquote>\\n", render_inline(text)));
            }''', v4)

RENDER_FN = check('''fn render_list(out: &mut String, tag: &str, items: &[String]) {
    out.push_str(&format!("<{}>\\n", tag));
    for item in items {
        out.push_str(&format!("  <li>{}</li>\\n", render_inline(item)));
    }
    out.push_str(&format!("</{}>\\n", tag));
}''', v4)

t = []

# ---------------------------------------------------------------- turn 1
t.append("""@@@ USER
I want to write a small Markdown to HTML converter in Rust, standard library only, as a command-line tool. It needs headings, paragraphs, bullet lists, code blocks, bold, italic, inline code and links. Plan the steps and do only step 1.
@@@ ASSISTANT
Plan:

1. **Block parser**: split the text into blocks (headings, paragraphs, lists, code blocks, rules). Tests first, no HTML yet.
2. **Inline formatting**: `**bold**`, `*italic*`, `` `code` ``, links, and escaping of HTML characters.
3. **HTML output and the command line**: render the blocks, read a file or standard input, build the tool.
4. **Review**: whatever breaks when you use it on real files.

Separating the steps matters. The parser decides *what* a line is; the renderer decides *how* it looks in HTML. Each can be tested alone.

Step 1: everything goes into one file, `md.rs`.

""" + code("rust", P.HEADER + P.BLOCKS_V1) + """

And at the bottom of the same file, the tests:

""" + code("rust", tests_block(P.TESTS_BLOCKS_V1)) + """

Compile and run the tests (on Linux or macOS run `./md_test`):

""" + code("", "rustc --edition 2021 --test md.rs -o md_test.exe\nmd_test.exe") + """

Result:

""" + code("", "running 9 tests\n...\ntest result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out") + """

Decisions in this step:
- `parse_blocks` goes through the input **line by line** and keeps small buffers (`paragraph`, `list`). A blank line, a heading, a rule or a code fence **flushes** the buffers into finished blocks. That is the whole algorithm.
- The three backticks of a fence are written in the Rust source as `\x60\x60\x60` (constant `FENCE`). Backtick is character 0x60. This keeps the source file free of a literal fence, so the file can be pasted into a Markdown code block, and the tests can build input with `format!`.
- A code fence is handled first and the lines inside it are copied without any interpretation. That is why `# not a heading` inside a code block stays text, which one of the tests checks.
- `#rust` is not a heading: Markdown needs a space after the hashes. `&line[hashes..]` is safe because `#` is exactly one byte long; I wrote that in a comment because slicing a `&str` at a wrong byte position is the classic way to get a panic in Rust.
- `Block` derives `PartialEq` and `Debug` only so that `assert_eq!` can compare and print blocks in the tests.
- Known simplification: `a` followed by `---` is a rule here. In full Markdown that line pair would be a heading.

Tell me when the 9 tests pass and I will write step 2.
""")

# ---------------------------------------------------------------- turn 2
t.append("""@@@ USER
9 tests pass. Step 2.
@@@ ASSISTANT
Step 2 adds the inline part. It is independent of the parser, so `parse_blocks` does not change. Add this code to `md.rs` below the block parser:

""" + code("rust", P.INLINE_V2) + """

and these tests inside the existing `mod tests { ... }`:

""" + code("rust", P.TESTS_INLINE_V2) + """

Run the same two commands as before. Result:

""" + code("", "running 17 tests\n...\ntest result: ok. 17 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out") + """

Decisions:
- **Escaping is the security rule of the whole tool**: every character that is not part of a recognised pattern goes through `escape_html`. That is why `<script>` in the input arrives as harmless text, and why the content of an inline code span is escaped too.
- The text is turned into a `Vec<char>` first. Indexing a `Vec<char>` by position is always valid, and it avoids slicing a `&str` in the middle of a multi-byte character (the test `non_ascii_text_is_safe` covers this).
- Each pattern looks for its closing marker. If there is none (`` `x `` or `[no link](oops`), nothing matches and the character is written as plain text. The test `unclosed_markers_stay_text` checks that no input is lost.
- Formatting is **recursive**: the inside of `**...**` goes through `render_inline` again, so `**bold `code`**` works. The inside of a code span does not, on purpose.
- **Links use a deny-by-default rule.** `safe_url` only accepts `http`, `https`, `mailto` and links without a scheme. `[click](javascript:alert(1))` becomes plain text. A list of dangerous schemes would always miss one; a list of allowed ones cannot. `find_paren_end` counts brackets so that addresses like `Rust_(language)` work.
- The rules are simplified compared with the full CommonMark specification. Mixed cases such as `**bold and *italic***` are not handled correctly. Tell me what you find when you use it.

Ready for step 3 (HTML output and the command line)?
""")

# ---------------------------------------------------------------- turn 3
t.append("""@@@ USER
17 pass. Yes, step 3.
@@@ ASSISTANT
Step 3 connects everything. Add the renderer and `main` to `md.rs`:

""" + code("rust", P.RENDER_V3) + "\n" + code("rust", P.MAIN_V3) + """

and these tests:

""" + code("rust", P.TESTS_RENDER_V3) + """

Tests again, then build the real tool:

""" + code("", "md_test.exe\nrustc --edition 2021 -O md.rs -o md.exe") + """

Result of the tests: `21 passed`.

Try it on a file or on standard input. With this input in `notes.md`:

""" + code("markdown", """# Release notes

The tool is *fast*, and `md --page` makes a **full page**.
See [the docs](https://example.com/docs) or [bad](javascript:alert(1)).

- converts headings
- converts lists

```rust
fn main() { println!("<hi>"); }
```""") + """

`md.exe notes.md` prints (the real output of this code):

""" + code("html", """<h1>Release notes</h1>
<p>The tool is <em>fast</em>, and <code>md --page</code> makes a <strong>full page</strong>. See <a href="https://example.com/docs">the docs</a> or bad.</p>
<ul>
  <li>converts headings</li>
  <li>converts lists</li>
</ul>
<pre><code class="language-rust">fn main() { println!(&quot;&lt;hi&gt;&quot;); }</code></pre>""") + """

`md.exe --page notes.md > notes.html` wraps the same body in a complete page with `<title>Release notes</title>`. Errors go to standard error with an exit code, so scripts can react:

""" + code("", """md.exe nope.md      ->  md: cannot read nope.md: The system cannot find the file specified. (os error 2)   (exit code 1)
md.exe --zzz        ->  md: unknown option --zzz                                                         (exit code 2)""") + """

Decisions:
- `convert(markdown) -> String` is the one function other code needs. The command line is a thin layer around it, so the logic stays testable without files.
- `fail` returns `!` (the "never returns" type), so `unwrap_or_else(|e| fail(...))` has the right type in both branches.
- Output is a **fragment** by default and a full page only with `--page`, because most people want to paste the HTML into something else. The page title is the first level-1 heading, escaped.
- `print!` instead of `println!` for the result, because every block already ends with a newline.

Use it on some real files and tell me what looks wrong.
""")

# ---------------------------------------------------------------- turn 4
t.append("""@@@ USER
It works. Two problems on my own notes. First, a line like "Total: 5 * 3 * 2 = 30" comes out as "5 <em> 3 </em> 2". Second, I need numbered lists and quotes. Also I want to be sure the converter cannot crash on strange input.
@@@ ASSISTANT
The first one is a real bug in my rules, so I reproduced it before changing anything:

""" + code("", """echo Total: 5 * 3 * 2 = 30 | md.exe
<p>Total: 5 <em> 3 </em> 2 = 30</p>""") + """

**Cause:** my italic rule treats any `*` as an opening marker and the next `*` as its end. In Markdown, an opening marker must be followed directly by text, and a closing marker must not follow a space. `5 * 3 * 2` has spaces on both sides, so it is plain text.

**Fix**, in `render_inline`. Two helper functions are new. Add them above `safe_url`:

""" + code("rust", OPENS) + """

and replace the bold and italic branches inside `render_inline` with these two:

""" + code("rust", BRANCHES) + """

Two details: a single `*` does not open italic when another `*` follows (that is the start of `**`), and `find_closing` skips a `*` that is part of a `**` pair. Without this, `a ** b ** c` came out as `a <em>* b *</em> c` in my first attempt: one of the new tests caught it. The empty-text check `if !inner.is_empty()` is no longer needed, because `find_closing` already requires at least one character.

**Numbered lists and quotes** need two new block kinds. The two loose buffers in `parse_blocks` are getting crowded, so I moved them into a small struct. Replace the `Block` enum, `flush` and `parse_blocks` with this (the helper functions `heading`, `is_rule` and `bullet` stay, `ordered_item` is new):

""" + code("rust", P.BLOCKS_V4) + """

In the renderer add the new arms (replace the `Block::List` arm) and one helper function:

""" + code("rust", RENDER_ARMS) + "\n" + code("rust", RENDER_FN) + """

**New tests** (add them to `mod tests`):

""" + code("rust", P.TESTS_V4_NEW_BLOCKS + P.TESTS_V4_NEW_INLINE + P.TESTS_V4_NEW_RENDER) + """

The last test is the answer to your crash question. It builds 3,000 random strings from an alphabet made of the nasty characters (`*`, `` ` ``, `[`, `(`, `#`, `>`, digits, newlines, tabs, accents, an emoji) and checks that `convert` never panics. It uses a tiny pseudo random generator with a fixed seed instead of a crate, so it is reproducible: if it ever fails, it fails every time.

Run everything:

""" + code("", "rustc --edition 2021 --test md.rs -o md_test.exe\nmd_test.exe") + """

Result:

""" + code("", "running 30 tests\n...\ntest result: ok. 30 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out") + """

And the two things you asked for, with the rebuilt tool:

""" + code("", """echo Total: 5 * 3 * 2 = 30 | md.exe
<p>Total: 5 * 3 * 2 = 30</p>

(input: "> Quote *here*", a blank line, "1. first", "2. second")
<blockquote>
  <p>Quote <em>here</em></p>
</blockquote>
<ol>
  <li>first</li>
  <li>second</li>
</ol>""") + """

What this converter still does not do: nested lists, tables, images, reference-style links, `_underscore_` emphasis, hard line breaks, backslash escapes (`\\*`), and raw HTML (which is escaped on purpose). A random-input test shows that it does not panic; it does not show that the output follows the CommonMark rules in every case. If you need full compatibility, use the `pulldown-cmark` crate, and keep this program as a way to understand how such a converter works.
@@@ END
""")

out = HERE.parent / "claude_longhorizon_markdown_12.txt"
out.write_text("\n".join(t), encoding="utf-8")
print("written", out, sum(len(x) for x in t), "chars")

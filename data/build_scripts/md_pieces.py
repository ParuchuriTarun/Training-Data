"""Source pieces of the Markdown converter project (used for testing and for building the data file)."""

HEADER = "// md.rs: a small Markdown to HTML converter. Standard library only.\n\n"

# ------------------------------------------------------------------ step 1: blocks
BLOCKS_V1 = r'''/// One block of a Markdown document.
#[derive(Debug, PartialEq)]
pub enum Block {
    Heading { level: u8, text: String },
    Paragraph(String),
    List(Vec<String>),
    Code { lang: String, text: String },
    Rule,
}

/// Splits Markdown text into blocks. It never panics, whatever the input.
pub fn parse_blocks(input: &str) -> Vec<Block> {
    let mut blocks = Vec::new();
    let mut paragraph: Vec<&str> = Vec::new();
    let mut list: Vec<String> = Vec::new();
    let mut lines = input.lines();

    while let Some(line) = lines.next() {
        let trimmed = line.trim();
        if let Some(rest) = trimmed.strip_prefix("```") {
            flush(&mut blocks, &mut paragraph, &mut list);
            let mut code = Vec::new();
            for inner in lines.by_ref() {
                if inner.trim() == "```" {
                    break; // an unclosed fence simply runs to the end of the input
                }
                code.push(inner);
            }
            blocks.push(Block::Code { lang: rest.trim().to_string(), text: code.join("\n") });
        } else if trimmed.is_empty() {
            flush(&mut blocks, &mut paragraph, &mut list);
        } else if is_rule(trimmed) {
            flush(&mut blocks, &mut paragraph, &mut list);
            blocks.push(Block::Rule);
        } else if let Some((level, text)) = heading(trimmed) {
            flush(&mut blocks, &mut paragraph, &mut list);
            blocks.push(Block::Heading { level, text: text.to_string() });
        } else if let Some(item) = bullet(trimmed) {
            if !paragraph.is_empty() {
                flush(&mut blocks, &mut paragraph, &mut list);
            }
            list.push(item.to_string());
        } else {
            if !list.is_empty() {
                flush(&mut blocks, &mut paragraph, &mut list);
            }
            paragraph.push(trimmed);
        }
    }
    flush(&mut blocks, &mut paragraph, &mut list);
    blocks
}

fn flush(blocks: &mut Vec<Block>, paragraph: &mut Vec<&str>, list: &mut Vec<String>) {
    if !paragraph.is_empty() {
        blocks.push(Block::Paragraph(paragraph.join(" ")));
        paragraph.clear();
    }
    if !list.is_empty() {
        blocks.push(Block::List(std::mem::take(list)));
    }
}

/// "### Title" -> (3, "Title"). "#rust" is not a heading: a space must follow the hashes.
fn heading(line: &str) -> Option<(u8, &str)> {
    let hashes = line.chars().take_while(|&c| c == '#').count();
    if (1..=6).contains(&hashes) {
        let rest = &line[hashes..]; // '#' is one byte, so this index is always valid
        if rest.starts_with(' ') {
            return Some((hashes as u8, rest.trim()));
        }
    }
    None
}

fn is_rule(line: &str) -> bool {
    let first = line.chars().next();
    matches!(first, Some('-') | Some('*') | Some('_'))
        && line.len() >= 3
        && line.chars().all(|c| Some(c) == first)
}

fn bullet(line: &str) -> Option<&str> {
    line.strip_prefix("- ").or_else(|| line.strip_prefix("* ")).map(str::trim)
}
'''

TESTS_BLOCKS_V1 = r'''    fn p(s: &str) -> Block {
        Block::Paragraph(s.to_string())
    }

    #[test]
    fn headings() {
        assert_eq!(
            parse_blocks("# Title\n### Sub"),
            vec![
                Block::Heading { level: 1, text: "Title".into() },
                Block::Heading { level: 3, text: "Sub".into() },
            ]
        );
    }

    #[test]
    fn a_hashtag_is_not_a_heading() {
        assert_eq!(parse_blocks("#rust"), vec![p("#rust")]);
        assert_eq!(parse_blocks("####### seven"), vec![p("####### seven")]);
    }

    #[test]
    fn paragraph_lines_are_joined() {
        assert_eq!(parse_blocks("one\ntwo\n\nthree"), vec![p("one two"), p("three")]);
    }

    #[test]
    fn list_items_are_grouped() {
        let expected = vec![Block::List(vec!["a".into(), "b".into(), "c".into()])];
        assert_eq!(parse_blocks("- a\n- b\n* c"), expected);
    }

    #[test]
    fn a_list_ends_when_text_follows() {
        assert_eq!(
            parse_blocks("- a\ntext"),
            vec![Block::List(vec!["a".into()]), p("text")]
        );
    }

    #[test]
    fn code_block_keeps_its_content_untouched() {
        let md = "```rust\nlet x = 1;\n\n# not a heading\n```\nafter";
        assert_eq!(
            parse_blocks(md),
            vec![
                Block::Code { lang: "rust".into(), text: "let x = 1;\n\n# not a heading".into() },
                p("after"),
            ]
        );
    }

    #[test]
    fn unclosed_code_block_runs_to_the_end() {
        assert_eq!(
            parse_blocks("```\nabc"),
            vec![Block::Code { lang: "".into(), text: "abc".into() }]
        );
    }

    #[test]
    fn rules_split_paragraphs() {
        assert_eq!(parse_blocks("a\n---\nb"), vec![p("a"), Block::Rule, p("b")]);
    }

    #[test]
    fn empty_input_gives_no_blocks() {
        assert!(parse_blocks("").is_empty());
        assert!(parse_blocks("\n\n   \n").is_empty());
    }
'''

# ------------------------------------------------------------------ step 2: inline text
INLINE_V2 = r'''/// Replaces the five characters that can change the meaning of HTML.
pub fn escape_html(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    for c in text.chars() {
        match c {
            '&' => out.push_str("&amp;"),
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            '"' => out.push_str("&quot;"),
            '\'' => out.push_str("&#39;"),
            _ => out.push(c),
        }
    }
    out
}

/// Index of the first occurrence of `pat` in `chars` at or after `from`.
fn find_seq(chars: &[char], from: usize, pat: &str) -> Option<usize> {
    let pat: Vec<char> = pat.chars().collect();
    if pat.is_empty() || chars.len() < pat.len() {
        return None;
    }
    (from..=chars.len() - pat.len()).find(|&i| chars[i..i + pat.len()] == pat[..])
}

/// Index of the ')' that closes a link target; inner pairs like (1) are skipped.
fn find_paren_end(chars: &[char], from: usize) -> Option<usize> {
    let mut depth = 0;
    for (i, &c) in chars.iter().enumerate().skip(from) {
        match c {
            '(' => depth += 1,
            ')' if depth == 0 => return Some(i),
            ')' => depth -= 1,
            _ => {}
        }
    }
    None
}

/// Only these links become clickable; "javascript:" and every other scheme is refused.
fn safe_url(url: &str) -> bool {
    let url = url.trim().to_ascii_lowercase();
    match url.split_once(':') {
        None => true, // relative link such as "docs/intro.md" or "#top"
        Some((scheme, _)) => matches!(scheme, "http" | "https" | "mailto"),
    }
}

/// Turns `code`, **bold**, *italic* and [text](url) into HTML. Everything else is escaped.
pub fn render_inline(text: &str) -> String {
    let chars: Vec<char> = text.chars().collect();
    let mut out = String::new();
    let mut i = 0;
    while i < chars.len() {
        let c = chars[i];

        if c == '`' {
            if let Some(end) = find_seq(&chars, i + 1, "`") {
                let code: String = chars[i + 1..end].iter().collect();
                out.push_str(&format!("<code>{}</code>", escape_html(&code)));
                i = end + 1;
                continue;
            }
        }

        if c == '*' && chars.get(i + 1) == Some(&'*') {
            if let Some(end) = find_seq(&chars, i + 2, "**") {
                let inner: String = chars[i + 2..end].iter().collect();
                if !inner.is_empty() {
                    out.push_str(&format!("<strong>{}</strong>", render_inline(&inner)));
                    i = end + 2;
                    continue;
                }
            }
        }

        if c == '*' {
            if let Some(end) = find_seq(&chars, i + 1, "*") {
                let inner: String = chars[i + 1..end].iter().collect();
                if !inner.is_empty() {
                    out.push_str(&format!("<em>{}</em>", render_inline(&inner)));
                    i = end + 1;
                    continue;
                }
            }
        }

        if c == '[' {
            if let Some(close) = find_seq(&chars, i + 1, "](") {
                if let Some(end) = find_paren_end(&chars, close + 2) {
                    let label: String = chars[i + 1..close].iter().collect();
                    let url: String = chars[close + 2..end].iter().collect();
                    if safe_url(&url) {
                        out.push_str(&format!(
                            "<a href=\"{}\">{}</a>",
                            escape_html(url.trim()),
                            render_inline(&label)
                        ));
                    } else {
                        out.push_str(&render_inline(&label)); // keep the text, drop the link
                    }
                    i = end + 1;
                    continue;
                }
            }
        }

        out.push_str(&escape_html(&c.to_string()));
        i += 1;
    }
    out
}
'''

TESTS_INLINE_V2 = r'''
    #[test]
    fn html_characters_are_escaped() {
        assert_eq!(render_inline("a <b> & \"c\""), "a &lt;b&gt; &amp; &quot;c&quot;");
    }

    #[test]
    fn bold_italic_and_code() {
        assert_eq!(
            render_inline("**b** *i* `c`"),
            "<strong>b</strong> <em>i</em> <code>c</code>"
        );
    }

    #[test]
    fn code_is_escaped_but_not_formatted() {
        assert_eq!(render_inline("`a *b* <c>`"), "<code>a *b* &lt;c&gt;</code>");
    }

    #[test]
    fn formatting_can_be_nested() {
        assert_eq!(
            render_inline("**bold `code`**"),
            "<strong>bold <code>code</code></strong>"
        );
    }

    #[test]
    fn links() {
        assert_eq!(
            render_inline("see [the docs](https://example.com/a?b=1&c=2)!"),
            "see <a href=\"https://example.com/a?b=1&amp;c=2\">the docs</a>!"
        );
        assert_eq!(
            render_inline("[wiki](https://en.wikipedia.org/wiki/Rust_(language))"),
            "<a href=\"https://en.wikipedia.org/wiki/Rust_(language)\">wiki</a>"
        );
        assert_eq!(render_inline("[next](docs/next.md)"), "<a href=\"docs/next.md\">next</a>");
    }

    #[test]
    fn dangerous_links_become_plain_text() {
        assert_eq!(render_inline("[click](javascript:alert(1))"), "click");
        assert_eq!(render_inline("[click](JaVaScRiPt:alert(1))"), "click");
        assert_eq!(render_inline("[x](data:text/html;base64,AAAA)"), "x");
    }

    #[test]
    fn unclosed_markers_stay_text() {
        assert_eq!(render_inline("2 ** 3 and a_b `x"), "2 ** 3 and a_b `x");
        assert_eq!(render_inline("[no link](oops"), "[no link](oops");
    }

    #[test]
    fn non_ascii_text_is_safe() {
        assert_eq!(render_inline("**é** `ü` 日本"), "<strong>é</strong> <code>ü</code> 日本");
    }
'''

# ------------------------------------------------------------------ step 3: HTML and command line
RENDER_V3 = r'''/// Renders blocks as HTML, one block per line (lists and code blocks keep their own lines).
pub fn render_html(blocks: &[Block]) -> String {
    let mut out = String::new();
    for block in blocks {
        match block {
            Block::Heading { level, text } => {
                out.push_str(&format!("<h{0}>{1}</h{0}>\n", level, render_inline(text)));
            }
            Block::Paragraph(text) => {
                out.push_str(&format!("<p>{}</p>\n", render_inline(text)));
            }
            Block::List(items) => {
                out.push_str("<ul>\n");
                for item in items {
                    out.push_str(&format!("  <li>{}</li>\n", render_inline(item)));
                }
                out.push_str("</ul>\n");
            }
            Block::Code { lang, text } => {
                let class = if lang.is_empty() {
                    String::new()
                } else {
                    format!(" class=\"language-{}\"", escape_html(lang))
                };
                out.push_str(&format!("<pre><code{}>{}</code></pre>\n", class, escape_html(text)));
            }
            Block::Rule => out.push_str("<hr>\n"),
        }
    }
    out
}

/// The whole job in one call: Markdown text in, HTML text out.
pub fn convert(markdown: &str) -> String {
    render_html(&parse_blocks(markdown))
}
'''

MAIN_V3 = r'''use std::io::Read;
use std::{env, fs, io, process};

fn page_title(blocks: &[Block]) -> String {
    for block in blocks {
        if let Block::Heading { level: 1, text } = block {
            return text.clone();
        }
    }
    "Document".to_string()
}

fn wrap_page(title: &str, body: &str) -> String {
    format!(
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n<title>{}</title>\n</head>\n<body>\n{}</body>\n</html>\n",
        escape_html(title),
        body
    )
}

fn fail(message: &str) -> ! {
    eprintln!("md: {}", message);
    process::exit(1)
}

fn main() {
    let mut full_page = false;
    let mut path: Option<String> = None;
    for arg in env::args().skip(1) {
        match arg.as_str() {
            "-h" | "--help" => {
                println!("usage: md [--page] [file.md]\nReads standard input when no file is given.");
                return;
            }
            "--page" => full_page = true,
            _ if arg.starts_with('-') => {
                eprintln!("md: unknown option {}", arg);
                process::exit(2);
            }
            _ => path = Some(arg),
        }
    }

    let input = match &path {
        Some(p) => fs::read_to_string(p).unwrap_or_else(|e| fail(&format!("cannot read {}: {}", p, e))),
        None => {
            let mut text = String::new();
            io::stdin()
                .read_to_string(&mut text)
                .unwrap_or_else(|e| fail(&format!("cannot read input: {}", e)));
            text
        }
    };

    let blocks = parse_blocks(&input);
    let body = render_html(&blocks);
    if full_page {
        print!("{}", wrap_page(&page_title(&blocks), &body));
    } else {
        print!("{}", body);
    }
}
'''

TESTS_RENDER_V3 = r'''
    #[test]
    fn converts_a_small_document() {
        let md = "# Hello\n\nSome *text* with `code`.\n\n- one\n- **two**\n\n```rust\nfn main() {}\n```\n\n---\n";
        let expected = "<h1>Hello</h1>\n<p>Some <em>text</em> with <code>code</code>.</p>\n<ul>\n  <li>one</li>\n  <li><strong>two</strong></li>\n</ul>\n<pre><code class=\"language-rust\">fn main() {}</code></pre>\n<hr>\n";
        assert_eq!(convert(md), expected);
    }

    #[test]
    fn html_in_the_input_is_escaped() {
        assert_eq!(
            convert("<script>alert(1)</script>"),
            "<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>\n"
        );
    }

    #[test]
    fn code_blocks_are_escaped() {
        assert_eq!(
            convert("```\n<b>&</b>\n```"),
            "<pre><code>&lt;b&gt;&amp;&lt;/b&gt;</code></pre>\n"
        );
    }

    #[test]
    fn the_page_gets_the_title_of_the_first_heading() {
        let blocks = parse_blocks("intro\n\n# My <Title>\n");
        assert_eq!(page_title(&blocks), "My <Title>");
        assert!(wrap_page("My <Title>", "").contains("<title>My &lt;Title&gt;</title>"));
    }
'''

# ------------------------------------------------------------------ step 4: fixes and additions
BLOCKS_V4 = r'''/// One block of a Markdown document.
#[derive(Debug, PartialEq)]
pub enum Block {
    Heading { level: u8, text: String },
    Paragraph(String),
    List(Vec<String>),
    Ordered(Vec<String>),
    Quote(String),
    Code { lang: String, text: String },
    Rule,
}

/// Lines that are collected until the block they belong to is complete.
#[derive(Default)]
struct Pending {
    paragraph: Vec<String>,
    list: Vec<String>,
    ordered: bool, // is `list` a numbered list?
    quote: Vec<String>,
}

impl Pending {
    /// Turns whatever is collected into a block. Only one of the three is ever filled.
    fn flush(&mut self, blocks: &mut Vec<Block>) {
        if !self.paragraph.is_empty() {
            blocks.push(Block::Paragraph(self.paragraph.join(" ")));
            self.paragraph.clear();
        }
        if !self.list.is_empty() {
            let items = std::mem::take(&mut self.list);
            blocks.push(if self.ordered { Block::Ordered(items) } else { Block::List(items) });
        }
        if !self.quote.is_empty() {
            blocks.push(Block::Quote(self.quote.join(" ")));
            self.quote.clear();
        }
    }
}

/// Splits Markdown text into blocks. It never panics, whatever the input.
pub fn parse_blocks(input: &str) -> Vec<Block> {
    let mut blocks = Vec::new();
    let mut pending = Pending::default();
    let mut lines = input.lines();

    while let Some(line) = lines.next() {
        let trimmed = line.trim();
        if let Some(rest) = trimmed.strip_prefix("```") {
            pending.flush(&mut blocks);
            let mut code = Vec::new();
            for inner in lines.by_ref() {
                if inner.trim() == "```" {
                    break;
                }
                code.push(inner);
            }
            blocks.push(Block::Code { lang: rest.trim().to_string(), text: code.join("\n") });
        } else if trimmed.is_empty() {
            pending.flush(&mut blocks);
        } else if is_rule(trimmed) {
            pending.flush(&mut blocks);
            blocks.push(Block::Rule);
        } else if let Some((level, text)) = heading(trimmed) {
            pending.flush(&mut blocks);
            blocks.push(Block::Heading { level, text: text.to_string() });
        } else if let Some(text) = trimmed.strip_prefix('>') {
            if pending.quote.is_empty() {
                pending.flush(&mut blocks);
            }
            pending.quote.push(text.trim().to_string());
        } else if let Some(item) = bullet(trimmed) {
            if pending.ordered || pending.list.is_empty() {
                pending.flush(&mut blocks); // another kind of block, or another kind of list
                pending.ordered = false;
            }
            pending.list.push(item.to_string());
        } else if let Some(item) = ordered_item(trimmed) {
            if !pending.ordered || pending.list.is_empty() {
                pending.flush(&mut blocks);
                pending.ordered = true;
            }
            pending.list.push(item.to_string());
        } else {
            if pending.paragraph.is_empty() {
                pending.flush(&mut blocks); // text ends a list or a quote
            }
            pending.paragraph.push(trimmed.to_string());
        }
    }
    pending.flush(&mut blocks);
    blocks
}

/// "### Title" -> (3, "Title"). "#rust" is not a heading: a space must follow the hashes.
fn heading(line: &str) -> Option<(u8, &str)> {
    let hashes = line.chars().take_while(|&c| c == '#').count();
    if (1..=6).contains(&hashes) {
        let rest = &line[hashes..]; // '#' is one byte, so this index is always valid
        if rest.starts_with(' ') {
            return Some((hashes as u8, rest.trim()));
        }
    }
    None
}

fn is_rule(line: &str) -> bool {
    let first = line.chars().next();
    matches!(first, Some('-') | Some('*') | Some('_'))
        && line.len() >= 3
        && line.chars().all(|c| Some(c) == first)
}

fn bullet(line: &str) -> Option<&str> {
    line.strip_prefix("- ").or_else(|| line.strip_prefix("* ")).map(str::trim)
}

/// "12. text" -> "text". "2026 was long" and "1.5 is a number" are not list items.
fn ordered_item(line: &str) -> Option<&str> {
    let digits = line.chars().take_while(|c| c.is_ascii_digit()).count();
    if digits == 0 {
        return None;
    }
    line[digits..].strip_prefix(". ").map(str::trim) // digits are ASCII, so the index is valid
}
'''

# inline v4: same as v2 except for the emphasis rules
INLINE_V4 = INLINE_V2.replace(
    '''/// Only these links become clickable''',
    '''/// True when the marker of `len` characters at `at` may open emphasis: text must follow it directly.
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
}

/// Only these links become clickable''',
).replace(
    '''        if c == '*' && chars.get(i + 1) == Some(&'*') {
            if let Some(end) = find_seq(&chars, i + 2, "**") {
                let inner: String = chars[i + 2..end].iter().collect();
                if !inner.is_empty() {
                    out.push_str(&format!("<strong>{}</strong>", render_inline(&inner)));
                    i = end + 2;
                    continue;
                }
            }
        }

        if c == '*' {
            if let Some(end) = find_seq(&chars, i + 1, "*") {
                let inner: String = chars[i + 1..end].iter().collect();
                if !inner.is_empty() {
                    out.push_str(&format!("<em>{}</em>", render_inline(&inner)));
                    i = end + 1;
                    continue;
                }
            }
        }
''',
    '''        if c == '*' && chars.get(i + 1) == Some(&'*') && opens_emphasis(&chars, i, 2) {
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
        }
''',
)

RENDER_V4 = RENDER_V3.replace(
    '''            Block::List(items) => {
                out.push_str("<ul>\\n");
                for item in items {
                    out.push_str(&format!("  <li>{}</li>\\n", render_inline(item)));
                }
                out.push_str("</ul>\\n");
            }
''',
    '''            Block::List(items) => render_list(&mut out, "ul", items),
            Block::Ordered(items) => render_list(&mut out, "ol", items),
            Block::Quote(text) => {
                out.push_str(&format!("<blockquote>\\n  <p>{}</p>\\n</blockquote>\\n", render_inline(text)));
            }
''',
).replace(
    '''/// The whole job in one call''',
    '''fn render_list(out: &mut String, tag: &str, items: &[String]) {
    out.push_str(&format!("<{}>\\n", tag));
    for item in items {
        out.push_str(&format!("  <li>{}</li>\\n", render_inline(item)));
    }
    out.push_str(&format!("</{}>\\n", tag));
}

/// The whole job in one call''',
)

TESTS_V4_NEW_BLOCKS = r'''
    #[test]
    fn ordered_lists() {
        assert_eq!(
            parse_blocks("1. one\n2. two\n10. ten"),
            vec![Block::Ordered(vec!["one".into(), "two".into(), "ten".into()])]
        );
    }

    #[test]
    fn numbers_that_are_not_list_items_stay_text() {
        assert_eq!(parse_blocks("2026 was long"), vec![p("2026 was long")]);
        assert_eq!(parse_blocks("1.5 is a number"), vec![p("1.5 is a number")]);
    }

    #[test]
    fn bullet_and_numbered_lists_do_not_mix() {
        assert_eq!(
            parse_blocks("- a\n1. b\n- c"),
            vec![
                Block::List(vec!["a".into()]),
                Block::Ordered(vec!["b".into()]),
                Block::List(vec!["c".into()]),
            ]
        );
    }

    #[test]
    fn quote_lines_are_joined() {
        assert_eq!(
            parse_blocks("> one\n> two\n\nafter"),
            vec![Block::Quote("one two".into()), p("after")]
        );
    }
'''

TESTS_V4_NEW_INLINE = r'''
    #[test]
    fn stars_around_spaces_are_not_emphasis() {
        assert_eq!(render_inline("5 * 3 * 2"), "5 * 3 * 2");
        assert_eq!(render_inline("a ** b ** c"), "a ** b ** c");
        assert_eq!(render_inline("*italic* and 5 * 3"), "<em>italic</em> and 5 * 3");
        assert_eq!(render_inline("**bold** and 2 ** 3"), "<strong>bold</strong> and 2 ** 3");
    }

    #[test]
    fn emphasis_with_inner_spaces_still_works() {
        assert_eq!(render_inline("*two words*"), "<em>two words</em>");
        assert_eq!(render_inline("**two words**"), "<strong>two words</strong>");
    }

    #[test]
    fn bold_inside_italic() {
        assert_eq!(
            render_inline("*a **b** c*"),
            "<em>a <strong>b</strong> c</em>"
        );
    }
'''

TESTS_V4_NEW_RENDER = r'''
    #[test]
    fn numbered_lists_and_quotes_render() {
        assert_eq!(convert("1. a\n2. b"), "<ol>\n  <li>a</li>\n  <li>b</li>\n</ol>\n");
        assert_eq!(
            convert("> hi *there*"),
            "<blockquote>\n  <p>hi <em>there</em></p>\n</blockquote>\n"
        );
    }

    fn next(seed: &mut u64) -> u64 {
        *seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        *seed >> 33
    }

    #[test]
    fn random_input_never_panics() {
        let alphabet: Vec<char> = "ab *_`#>-1.[]()\n\t é\u{1F600}".chars().collect();
        let mut seed = 12345u64;
        for _ in 0..3000 {
            let len = (next(&mut seed) % 60) as usize;
            let text: String = (0..len)
                .map(|_| alphabet[next(&mut seed) as usize % alphabet.len()])
                .collect();
            let _ = convert(&text); // the test passes if nothing panics
        }
    }
'''


# ---- the source must not contain three backticks in a row: it is shown inside Markdown code blocks
FENCE_CONST = (
    '/// Three backticks, written as escapes so that this file can be shown inside a Markdown code block.\n'
    'const FENCE: &str = "\\x60\\x60\\x60";\n\n'
)


def _sub(text, old, new):
    assert old in text, old
    return text.replace(old, new)


BLOCKS_V1 = FENCE_CONST + _sub(_sub(BLOCKS_V1, 'strip_prefix("```")', 'strip_prefix(FENCE)'), '== "```"', '== FENCE')
BLOCKS_V4 = FENCE_CONST + _sub(_sub(BLOCKS_V4, 'strip_prefix("```")', 'strip_prefix(FENCE)'), '== "```"', '== FENCE')

TESTS_BLOCKS_V1 = _sub(
    TESTS_BLOCKS_V1,
    r'''let md = "```rust\nlet x = 1;\n\n# not a heading\n```\nafter";''',
    r'''let md = format!("{f}rust\nlet x = 1;\n\n# not a heading\n{f}\nafter", f = FENCE);''',
)
TESTS_BLOCKS_V1 = _sub(TESTS_BLOCKS_V1, 'parse_blocks(md),', 'parse_blocks(&md),')
TESTS_BLOCKS_V1 = _sub(TESTS_BLOCKS_V1, 'parse_blocks("```\\nabc")', 'parse_blocks(&format!("{}\\nabc", FENCE))')

TESTS_RENDER_V3 = _sub(
    TESTS_RENDER_V3,
    r'''let md = "# Hello\n\nSome *text* with `code`.\n\n- one\n- **two**\n\n```rust\nfn main() {}\n```\n\n---\n";''',
    r'''let md = format!(
            "# Hello\n\nSome *text* with `code`.\n\n- one\n- **two**\n\n{f}rust\nfn main() {{}}\n{f}\n\n---\n",
            f = FENCE
        );''',
)
TESTS_RENDER_V3 = _sub(TESTS_RENDER_V3, 'assert_eq!(convert(md), expected);', 'assert_eq!(convert(&md), expected);')
TESTS_RENDER_V3 = _sub(
    TESTS_RENDER_V3,
    'convert("```\\n<b>&</b>\\n```"),',
    'convert(&format!("{f}\\n<b>&</b>\\n{f}", f = FENCE)),',
)


def assemble(parts):
    """parts: list of source pieces; the last items are test pieces (wrapped in a tests module)."""
    code = HEADER + "\n".join(parts["code"])
    tests = "\n#[cfg(test)]\nmod tests {\n    use super::*;\n\n" + "\n".join(parts["tests"]).rstrip() + "\n}\n"
    return code.rstrip() + "\n" + tests


V1 = {"code": [BLOCKS_V1], "tests": [TESTS_BLOCKS_V1]}
V2 = {"code": [BLOCKS_V1, INLINE_V2], "tests": [TESTS_BLOCKS_V1, TESTS_INLINE_V2]}
V3 = {"code": [BLOCKS_V1, INLINE_V2, RENDER_V3, MAIN_V3], "tests": [TESTS_BLOCKS_V1, TESTS_INLINE_V2, TESTS_RENDER_V3]}
V4 = {
    "code": [BLOCKS_V4, INLINE_V4, RENDER_V4, MAIN_V3],
    "tests": [TESTS_BLOCKS_V1, TESTS_V4_NEW_BLOCKS, TESTS_INLINE_V2, TESTS_V4_NEW_INLINE, TESTS_RENDER_V3, TESTS_V4_NEW_RENDER],
}
VERSIONS = {"v1": V1, "v2": V2, "v3": V3, "v4": V4}

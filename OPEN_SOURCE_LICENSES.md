# Open-source material used in the training data

Collected 2026-11-12. Only sources under MIT, Apache-2.0 or CC0 were used. The full licence
text of every source is copied into `data/licenses/<repo>/`, because MIT and Apache-2.0 require
the copyright notice to travel with the material.

The converted text is in `data/external/oss_*.txt`. Converters: `data/tools/oss_convert.py` (mdBook
sources) and `data/tools/oss_convert2.py` (everything else). Post-processing: `data/tools/oss_verify_rust.py`
and `data/tools/oss_clean_webdev.py`.

## Sources used

| File in `data/external/` | Repository | Commit | Licence | Copyright holder |
|---|---|---|---|---|
| oss_rust_book.txt | https://github.com/rust-lang/book | 2771df165f09 | MIT OR Apache-2.0 | The Rust Project Developers |
| oss_rust_by_example.txt | https://github.com/rust-lang/rust-by-example | dcc14f912bf8 | MIT OR Apache-2.0 | Jorge Aparicio and contributors |
| oss_rust_api_guidelines.txt | https://github.com/rust-lang/api-guidelines | 97a0969cb07f | MIT OR Apache-2.0 | The Rust Project Developers |
| oss_rust_async_book.txt | https://github.com/rust-lang/async-book | 840327a2e8ea | MIT | Aaron Turon |
| oss_rust_cookbook.txt | https://github.com/rust-lang-nursery/rust-cookbook | 555abf48f78c | CC0 1.0 | (public-domain dedication) |
| oss_rustlings.txt | https://github.com/rust-lang/rustlings | f7b9b3c5882a | MIT | Carol (Nichols \|\| Goulding) |
| oss_algo_python.txt | https://github.com/TheAlgorithms/Python | 30507bbe41397 | MIT | TheAlgorithms and contributors |
| oss_algo_rust.txt | https://github.com/TheAlgorithms/Rust | fed66cb0c74c | MIT | The Algorithms |
| oss_js_questions.txt | https://github.com/lydiahallie/javascript-questions | a8b427b9f7f9 | MIT | Lydia Hallie |
| oss_clean_code_js.txt | https://github.com/ryanmcdermott/clean-code-javascript | 5311f64b03fc | MIT | Ryan McDermott |
| oss_bash_bible.txt | https://github.com/dylanaraps/pure-bash-bible | 8c19d0b482b0 | MIT | Dylan Araps |
| oss_webdev_beginners.txt | https://github.com/microsoft/Web-Dev-For-Beginners | 93b9967af14e | MIT | Microsoft Corporation |
| oss_tauri_docs.txt | https://github.com/tauri-apps/tauri-docs | ed0786ec8669 | MIT | Tauri Programme within the Commons Conservancy |
| oss_airbnb_js.txt | https://github.com/airbnb/javascript | 8ed19247bef1 | MIT | Airbnb |

The Rust Book, Rust By Example and the API Guidelines are dual-licensed; this project takes
them under the MIT option.

## Cloned but NOT used

| Repository | Licence | Reason |
|---|---|---|
| vuejs/docs | CC BY 4.0 (everything except images) | Attribution licence, outside the MIT / Apache / CC0 rule |
| leonardomso/33-js-concepts | MIT | The content is mostly links to other people's articles |
| trekhleb/javascript-algorithms | MIT | Not converted yet |
| emilk/egui | MIT OR Apache-2.0 | Not converted yet |
| rust-lang/reference | MIT OR Apache-2.0 | Not converted yet |

Anything under CC BY-SA, CC BY-NC, GPL or an unknown licence was left out on purpose.

## What was changed

- mdBook `{{#include}}` / `{{#rustdoc_include}}` directives were resolved and hidden `# ` lines
  removed from Rust code fences.
- Links, badges, images and navigation were stripped; pages were split at headings into chunks
  of about 7,000 characters or less.
- Each chunk got a user question written from a template, and the original text became the answer.
- In `oss_webdev_beginners.txt` emoji were removed, and examples with first-person anecdotes
  ("when I started...") or broken code fences were dropped.

## What was and was not checked

- The Rust documentation snippets (Book, Rust By Example, Cookbook, API Guidelines, Async Book)
  that are complete programs were compiled with `rustc`. Fragments that need a crate, a project
  setup or other listings were kept as they are.
- Code from the other sources (TheAlgorithms, rustlings, Tauri, egui, Airbnb, MS lessons) was
  converted as text only and **was not executed**. It is only as correct as each project's own
  tests and CI.
- Tokio, Tauri and egui snippets cannot be checked without those crates and a GUI, so they were not.
- Documentation drifts. Examples for Tauri in particular follow the version of the docs at the
  commit above.

## Attribution notice

The text and code in these files remain the work of the copyright holders listed above and stay
under their licences. Keep this file and `data/licenses/` with the data if you share it. The
trained weights are a separate question; this manifest only documents where the data came from.

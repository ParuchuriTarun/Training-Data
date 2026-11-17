# Open-source material used in the training data

Collected 2026-11-12. Only sources under MIT, Apache-2.0 or CC0 were used. The full licence
text of every source is copied into `data/licenses/<repo>/`, because MIT and Apache-2.0 require
the copyright notice to travel with the material.

The converted text is in `data/external/oss_*.txt`. Converters: `data/oss_convert.py` (mdBook
sources) and `data/oss_convert2.py` (everything else). Post-processing: `data/oss_verify_rust.py`
and `data/oss_clean_webdev.py`.

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
| oss_rust_nomicon.txt | https://github.com/rust-lang/nomicon | b0bb569883a3 | MIT OR Apache-2.0 | The Rust Project Developers (see LICENSE-MIT) |
| oss_rust_reference.txt | https://github.com/rust-lang/reference | bcd62f35e8bf | MIT OR Apache-2.0 | The Rust Project Developers (see LICENSE-MIT) |
| oss_rust_edition_guide.txt | https://github.com/rust-lang/edition-guide | ab8544aeed7b | MIT OR Apache-2.0 | The Rust Project Developers (see LICENSE-MIT) |
| oss_rust_cargo_book.txt, oss_rust_cargo_contrib.txt | https://github.com/rust-lang/cargo (doc/book, doc/contrib) | f93c676e3e7a | MIT OR Apache-2.0 | The Rust Project Developers (see LICENSE-MIT) |
| oss_rustc_dev_guide.txt | https://github.com/rust-lang/rustc-dev-guide | bc3f08932e05 | MIT OR Apache-2.0 | The Rust Project Developers (see LICENSE-MIT) |
| oss_rust_cli_book.txt | https://github.com/rust-cli/book | bfb30887e301 | MIT | rust-lang-nursery |
| oss_tokio_docs.txt | https://github.com/tokio-rs/website (content/tokio) | 71cdb3858fbb | MIT | Carl Lerche and Tokio website contributors |
| oss_node_docs.txt | https://github.com/nodejs/node (doc/api only) | 90493f098a53 | MIT | Node.js contributors |
| oss_js_algorithms.txt | https://github.com/trekhleb/javascript-algorithms (English README files only) | 85293e3e2b88 | MIT | Oleksii Trekhleb |
| oss_fastapi.txt | https://github.com/fastapi/fastapi (docs/en/docs and docs_src) | d85d47a41607 | MIT | Sebastián Ramírez |
| oss_typer.txt | https://github.com/fastapi/typer (docs and docs_src) | 695d84504ab5 | MIT | Sebastián Ramírez |
| oss_pydantic.txt | https://github.com/pydantic/pydantic (docs) | fa156283c7b3 | MIT | Pydantic Services Inc. and individual contributors |
| oss_uv_docs.txt | https://github.com/astral-sh/uv (docs) | cf9bace0e30e | MIT OR Apache-2.0 | Astral Software Inc. |
| oss_vite_docs.txt | https://github.com/vitejs/vite (docs) | 9a8d1a98922c | MIT | VoidZero Inc. and Vite contributors |
| oss_svelte_docs.txt | https://github.com/sveltejs/svelte (documentation) | 99c07450d2e0 | MIT | Svelte Contributors |
| oss_nextjs_docs.txt | https://github.com/vercel/next.js (docs) | 67c021252d40 | MIT | Vercel, Inc. |
| oss_docker_docs.txt | https://github.com/docker/docs (content, without the product-admin sections) | f081e781d06d | Apache-2.0 | Docker, Inc. |
| oss_playwright_docs.txt | https://github.com/microsoft/playwright (docs) | b4d016aadc5c | Apache-2.0 | Microsoft Corporation |
| oss_clippy_book.txt | https://github.com/rust-lang/rust-clippy (book) | c96aca17f5db | MIT OR Apache-2.0 | The Rust Project Developers (see LICENSE-MIT) |
| oss_axum_docs.txt | https://github.com/tokio-rs/axum (examples and docs) | 2449f1600c66 | MIT | axum Contributors |
| oss_rocket_guide.txt | https://github.com/rwf2/Rocket (docs/guide) | 3a54d079aef0 | MIT OR Apache-2.0 | Rocket contributors (see LICENSE-MIT) |
| oss_diesel_guide.txt | https://github.com/diesel-rs/diesel (guide drafts) | 62ea31380676 | MIT OR Apache-2.0 | Diesel contributors (see LICENSE-MIT) |
| oss_vitest_docs.txt | https://github.com/vitest-dev/vitest (docs) | efba8cbfe94b | MIT | VoidZero Inc. and Vitest contributors |
| oss_jest_docs.txt | https://github.com/jestjs/jest (docs) | aa88f7cf0bfc | MIT | Meta Platforms, Inc. and affiliates |
| oss_react_router_docs.txt | https://github.com/remix-run/react-router (docs) | a983c51daecc | MIT | React Training LLC and Remix Software Inc. |
| oss_tanstack_query.txt | https://github.com/TanStack/query (docs, React and shared pages) | d63a027c26b2 | MIT | Tanner Linsley |
| oss_sveltekit_docs.txt | https://github.com/sveltejs/kit (documentation) | 407ef8cb1257 | MIT | SvelteKit contributors |
| oss_angular_docs.txt | https://github.com/angular/angular (adev/src/content, without the API reference) | f41e1d82695d | MIT | Google LLC |
| oss_leptos_book.txt | https://github.com/leptos-rs/book | 2ec56454c7d3 | MIT | Leptos |
| oss_yew_docs.txt | https://github.com/yewstack/yew (website/docs) | bfa6c19af971 | MIT OR Apache-2.0 | Yew contributors (see LICENSE-MIT) |
| oss_cheatsheets.txt | https://github.com/LeCoupa/awesome-cheatsheets | 774445f64658 | MIT | Julien Le Coupanec |
| oss_clean_code_ts.txt | https://github.com/labs42io/clean-code-typescript | 05a25e8fb8f4 | MIT | Labs42 |
| oss_airbnb_css.txt | https://github.com/airbnb/css | c92f95c09909 | MIT | Airbnb |
| oss_pure_sh_bible.txt | https://github.com/dylanaraps/pure-sh-bible | 26bc7e8d6cfb | MIT | Dylan Araps |

The Rust Book, Rust By Example and the API Guidelines are dual-licensed; this project takes
them under the MIT option.

## Cloned but NOT used

| Repository | Licence | Reason |
|---|---|---|
| vuejs/docs | CC BY 4.0 (everything except images) | Attribution licence, outside the MIT / Apache / CC0 rule |
| leonardomso/33-js-concepts | MIT | The content is mostly links to other people's articles |
| emilk/egui | MIT OR Apache-2.0 | Not converted yet |
| google/comprehensive-rust | Apache-2.0 (code) and CC BY 4.0 (all .md text) | The course text is CC BY 4.0, outside the MIT / Apache / CC0 rule |
| clap-rs/clap | MIT OR Apache-2.0 | Its guides are rustdoc comments, nothing to convert |
| ratatui/ratatui-website | MIT | Too little text |
| oven-sh/bun | MIT, but the repository bundles LGPL code | Mixed licence in one repository, left out to be safe |
| prisma/docs | not verified | No licence file found in the docs repository |
| denysdovhan/bash-handbook | CC BY 4.0 | Attribution licence, outside the MIT / Apache / CC0 rule |

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

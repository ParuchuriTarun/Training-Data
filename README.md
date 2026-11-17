# Training-Data

Training data for **Mavo Coder 2B**, a from-scratch 2-billion-parameter coding language model (PyTorch).
The model is meant to be strong at web development, Rust application building, terminal commands,
clear English explanations, app development and long-horizon tasks.

This repository is the home of the data. New batches are added here.

## Layout

| Path | What is in it |
|---|---|
| `data/seed/` | The first hand-written examples. |
| `data/external/` | The main training files (`.txt`). One file per topic or batch, for example `claude_rust_apps_01.txt`, `claude_node_server_23.txt`, `oss_rust_book.txt`. |
| `data/generators/` | Small Python scripts (`gen_*.py`) that produce extra examples when the data is loaded. |
| `data/build_scripts/` | The scripts that wrote and verified the Claude-written examples (each one runs the code and pastes the real output into the answer). Paths inside them point to the original laptop. |
| `data/tools/` | Checkers and converters: compile-check Rust blocks, run Python/JS/SQL blocks, duplicate checks, the open-source converters. |
| `data/licenses/` | The licence text of every open-source project that was used. |
| `training_data/` | Examples collected from other AI assistants, sorted by category (`appdev`, `english`, `fundamentals`, `longhorizon`, `seed`, `webdev`). |
| `Data.txt` | One more collected file (a local user name inside it was replaced by `<user>`). |
| `OPEN_SOURCE_LICENSES.md` | Which open-source files were used, their commits, licences and copyright holders. |

## File format

Plain text. Every example is:

```
@@@ USER
the question
@@@ ASSISTANT
the answer
@@@ END
```

A multi-turn conversation alternates `@@@ USER` and `@@@ ASSISTANT` blocks before one `@@@ END`.
The training loader drops any example whose user and assistant text together are longer than
40,000 characters, so keep long conversations under that.

## Quality rules for new data

- Every code example is compiled or run before it goes in, and the real output is what the answer shows.
- No example repeats the question of another one.
- Open-source material is used only if it is MIT, Apache-2.0 or CC0, and its licence and
  copyright holder are recorded in `OPEN_SOURCE_LICENSES.md`.

## Size

About 7,500 examples and about 7.8 million training tokens (2026-11-17). A 2B model needs far more than that,
so collecting more data is the current work.

## Licence and provenance

- `data/external/oss_*.txt` are converted from the projects listed in `OPEN_SOURCE_LICENSES.md`.
  They stay under their original licences, and the notices in `data/licenses/` must stay with them.
- `claude_*.txt`, `data/seed/` and `data/generators/` were written for this project.
  The repository owner has not chosen a licence for them yet.
- `training_data/`, `Data.txt` and the `deepseek_*` / `qwen_*` / `td_*` files in `data/external/`
  come from other AI assistants. Check the terms of those services before you reuse them.

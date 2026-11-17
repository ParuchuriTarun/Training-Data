"""Build data/staging/claude_terminal_git_14.txt. Every shell script is RUN with Git Bash (GNU tools)
in a scratch directory and the real output is pasted into the answer."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

F = "`" * 3
OUT = Path(r"C:\Projects\Mavo\Coding 1 2B\data\staging\claude_terminal_git_14.txt")
BASH = r"C:\Program Files\Git\bin\bash.exe"

ENV = dict(os.environ)
ENV.update({
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_AUTHOR_DATE": "2026-01-01T12:00:00+0000",
    "GIT_COMMITTER_DATE": "2026-01-01T12:00:00+0000",
    "LC_ALL": "C",
})


def run_sh(script):
    d = Path(tempfile.mkdtemp())
    (d / "s.sh").write_text(script.strip() + "\n", encoding="utf-8", newline="\n")
    p = subprocess.run([BASH, "s.sh"], cwd=d, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                       encoding="utf-8", timeout=60)
    out = (p.stdout).replace("\r", "").rstrip("\n")
    return out


EXAMPLES = []


def ex(question, intro, script, after, lang="bash"):
    out = run_sh(script)
    ans = f"{intro}\n\n{F}{lang}\n{script.strip()}\n{F}\n\nOutput:\n\n{F}\n{out}\n{F}\n\n{after.strip()}"
    EXAMPLES.append((question, ans))


GIT_INIT = '''cd "$(mktemp -d)"
git init -q -b main .
git config user.name "Demo" && git config user.email "demo@example.com"
'''

# 1 ---------------------------------------------------------------------------------------------
ex("How do I undo my last git commit? What is the difference between reset --soft, --mixed and --hard?",
   "All three move the branch back one commit. They differ in what happens to your changes. This demo runs `--soft` and `--hard` in a scratch repository so you can see the effect.",
   GIT_INIT + r'''echo one > a.txt && git add a.txt && git commit -qm "first"
echo two >> a.txt && git commit -qam "second"

echo "--- history before"; git log --format=%s

git reset --soft HEAD~1
echo "--- after --soft: commit gone, change still staged"
git log --format=%s
git status --short

git commit -qm "second, again"
git reset --hard HEAD~1
echo "--- after --hard: commit gone, change gone"
git log --format=%s
git status --short
cat a.txt
''',
   """
Summary:
- `git reset --soft HEAD~1` removes the commit but leaves your changes **staged** (`M ` in the first column). Use it to redo the commit, for example to fix the message or to split it.
- `git reset HEAD~1` (the default, `--mixed`) removes the commit and also unstages the changes. The files keep the edits, shown as ` M`.
- `git reset --hard HEAD~1` removes the commit **and** throws the changes away. Git confirms it with the line `HEAD is now at ... first`, and `a.txt` is back to `one`.
- If you already pushed the commit, do not reset. Use `git revert HEAD`, which adds a new commit that undoes the old one and is safe for shared branches.
- A hard reset is not completely final: `git reflog` lists where `HEAD` has been, and `git reset --hard <hash from reflog>` brings the commit back for a while (typically at least 30 days, until garbage collection).""")

# 2 ---------------------------------------------------------------------------------------------
ex("I have uncommitted changes but need to switch branches quickly. How do I use git stash?",
   "`git stash` puts your uncommitted changes on a shelf and gives you a clean working directory. Give each stash a message so you can recognise it later.",
   GIT_INIT + r'''echo base > notes.txt && git add notes.txt && git commit -qm "base"
git branch hotfix

echo "half finished work" >> notes.txt
git stash push -m "wip: notes"
echo "--- stash list:"; git stash list
echo "--- status is clean:"; git status --short

git switch -q hotfix
echo "fix" > fix.txt && git add fix.txt && git commit -qm "hotfix done"
git switch -q main

git stash pop
echo "--- notes.txt:"; cat notes.txt
echo "--- stash list now:"; git stash list
''',
   """
Notes:
- `git stash push -m "message"` is the modern form of plain `git stash`. By default it stashes changes to files that git already tracks. Add `-u` to include new untracked files.
- `git stash list` shows `stash@{0}` as the newest entry. `git stash pop` applies it and removes it from the list. `git stash apply` applies it but keeps it, which is useful when you want to try the same change on two branches.
- If the pop produces a conflict, git keeps the stash and tells you; resolve the files, then drop it yourself with `git stash drop`.
- An empty `git status --short` means a clean working directory, so nothing is printed under that heading. The long status text in the output comes from `git stash pop`, which shows what it restored and then `Dropped refs/stash@{0}`.
- A stash belongs to the repository, not to a branch, so you can pop it on a different branch from where you created it.""")

# 3 ---------------------------------------------------------------------------------------------
ex("What is the difference between git restore and git restore --staged?",
   "A file can have two kinds of changes at the same time: staged (ready for the next commit) and unstaged (edited after staging). `git restore` works on one of the two, depending on the flag.",
   GIT_INIT + r'''echo "line 1" > a.txt && git add a.txt && git commit -qm "start"

echo "line 2" >> a.txt
git add a.txt
echo "line 3" >> a.txt
echo "--- status (MM = staged and also modified again):"
git status --short

git restore --staged a.txt
echo "--- after restore --staged (unstaged, edits kept):"
git status --short
cat a.txt

git restore a.txt
echo "--- after restore (edits thrown away):"
git status --short
cat a.txt
''',
   """
Remember it like this:
- `git restore --staged <file>` only changes the **index** (the staging area). Your file on disk is not touched, so nothing is lost. It is the modern replacement for `git reset HEAD <file>`.
- `git restore <file>` overwrites the **working file** with the staged version, or with the last commit if nothing is staged. Your unstaged edits are gone and cannot be recovered with git, because they were never committed.
- In the status output the first column is the index and the second is the working tree: `MM` means modified in both, ` M` means only modified in the working tree.
- To discard everything in both places, use `git restore --staged --worktree <file>`, or `git checkout HEAD -- <file>` in older versions of git.""")

# 4 ---------------------------------------------------------------------------------------------
ex("I committed a .env file and added it to .gitignore, but git still tracks it. How do I stop tracking it?",
   "`.gitignore` only affects files that git does not track yet. Once a file is committed, git keeps watching it until you remove it from the index, which `git rm --cached` does without deleting the file on disk.",
   GIT_INIT + r'''echo "API_KEY=abc" > .env
echo "print('hi')" > app.py
git add .env app.py && git commit -qm "initial (oops, .env included)"

echo ".env" > .gitignore
echo "API_KEY=changed" > .env
echo "--- .gitignore does not help yet:"
git status --short

git rm --cached -q .env
git add .gitignore
git commit -qm "Stop tracking .env"

echo "--- after rm --cached:"
git status --short
echo "--- tracked files:"; git ls-files
echo "--- file still on disk:"; cat .env
''',
   """
Important details:
- `--cached` means "remove from the index only". Without it, `git rm` also deletes the file from your disk.
- The old commit still contains the file and its contents. If it held a real secret such as a password or API key, assume it is compromised: **rotate the key**. Removing it from history needs a tool such as `git filter-repo`, and anyone who already cloned the repository still has the old data.
- Other people who pull this commit will have the file removed from their working folder. Tell them to copy their own `.env` somewhere safe first, or commit a `.env.example` instead.
- To check why a file is ignored, run `git check-ignore -v .env`; it prints the rule and the file that contains it.""")

# 5 ---------------------------------------------------------------------------------------------
ex("How do I resolve a merge conflict in git? Show me what the conflict markers mean.",
   "Git cannot merge automatically when two branches changed the same lines. It stops, marks the places in the file, and waits for you to decide the final text. This demo creates a conflict on purpose and resolves it.",
   GIT_INIT + r'''printf 'Hello\nWelcome to the app\nBye\n' > greeting.txt
git add greeting.txt && git commit -qm "base"

git switch -q -c feature
sed -i 's/Welcome to the app/Welcome to the new app/' greeting.txt
git commit -qam "feature wording"

git switch -q main
sed -i 's/Welcome to the app/Welcome to our app/' greeting.txt
git commit -qam "main wording"

git merge feature
echo "--- greeting.txt during the conflict:"; cat greeting.txt
echo "--- status:"; git status --short

# Edit the file to the final text, remove the markers, then:
printf 'Hello\nWelcome to our new app\nBye\n' > greeting.txt
git add greeting.txt
git commit -qm "Merge feature, combine wording"
echo "--- history:"; git log --format=%s
''',
   """
How to read the markers:
- Everything between `<<<<<<< HEAD` and `=======` is **your side**, the branch you are on (`main`).
- Everything between `=======` and `>>>>>>> feature` is **their side**, the branch you are merging in.
- `UU` in the status means "unmerged, changed by both". The file stays in that state until you `git add` it.

Steps in a real conflict:
1. Run `git status` to see which files conflict.
2. Open each file, choose the correct final text (one side, the other, or a mix) and delete the three marker lines completely.
3. Run the tests or at least build, because a text merge can compile but still be wrong.
4. `git add <file>` for each fixed file, then `git commit` (git has already prepared a merge message).

To abandon the merge and return to the state before it, run `git merge --abort`. To take one whole side for a file, use `git checkout --ours <file>` or `git checkout --theirs <file>`, then `git add` it.""")

# 6 ---------------------------------------------------------------------------------------------
ex("How can I find which commit added or removed a certain line or word in git?",
   "Use the pickaxe options of `git log`. `-S` finds commits where the number of occurrences of a string changed, and `-G` finds commits whose diff has a line matching a regular expression.",
   GIT_INIT + r'''printf 'host=localhost\nport=80\n' > config.txt
git add config.txt && git commit -qm "initial config"

printf 'host=localhost\nport=80\ntimeout=5\n' > config.txt
git commit -qam "add timeout"

sed -i 's/timeout=5/timeout=30/' config.txt
git commit -qam "raise timeout"

sed -i 's/port=80/port=8080/' config.txt
git commit -qam "change port"

echo "--- commits that added or removed the exact text timeout=5:"
git log -S"timeout=5" --format=%s -- config.txt

echo "--- commits whose diff has a line matching timeout=<digits>:"
git log -G"timeout=[0-9]+" --format=%s -- config.txt

echo "--- every commit that touched the file:"
git log --format=%s -- config.txt

echo "--- what the last change looked like:"
git show --format= --unified=0 HEAD
''',
   """
Which option to pick:
- `-S"text"` answers "when did this text appear or disappear?". It lists `add timeout` (the text was added) and `raise timeout` (the text was removed). It does not list `change port`, because the count of `timeout=5` did not change there.
- `-G"regex"` answers "which commits changed a line that matches this pattern?". It also catches edits where the matching line changed but the count stayed the same.
- Add `-p` to see the patch of each matching commit, or `--oneline` for short hashes with subjects.
- To follow a whole function or line range through history, use `git log -L :functionName:file.py` or `git log -L 10,20:file.py`.
- To see who last changed each line, use `git blame file.txt`; add `-w` to ignore whitespace-only changes.""")

# 7 ---------------------------------------------------------------------------------------------
ex("I forgot to add a file to my last commit and want to change its message. How do I amend a commit?",
   "`git commit --amend` replaces the last commit with a new one that includes whatever is staged now. The old commit is not edited; a new commit takes its place.",
   GIT_INIT + r'''echo "a" > a.txt && echo "b" > b.txt
git add a.txt
git commit -qm "Add feature A and B"
echo "--- b.txt was forgotten:"
git status --short

git add b.txt
git commit -q --amend --no-edit
echo "--- after amend (same message, both files):"
git show --stat --format=%s HEAD

git commit -q --amend -m "Add features A and B"
echo "--- after rewording:"
git log --format=%s
''',
   """
Rules of thumb:
- `--no-edit` keeps the old message. Without it, git opens your editor so you can change it. `-m "..."` sets a new message directly.
- Amending changes the commit's hash. That is harmless for a commit that only exists on your machine.
- **Do not amend a commit that you have already pushed** and that others may have pulled. They would then have a history that differs from yours. If you must, use `git push --force-with-lease`, which refuses to overwrite work that you have not seen.
- To change an older commit (not the last one), use `git rebase -i HEAD~3` and mark the commit with `reword` or `edit`.""")

# 8 ---------------------------------------------------------------------------------------------
ex("How do I clean up old git branches, and why does git refuse to delete some of them?",
   "`git branch --merged` lists branches whose work is already in the current branch, so they are safe to delete. Branches that are not merged need `-D`, which is the force flag, because deleting them would lose commits.",
   GIT_INIT + r'''echo base > f.txt && git add f.txt && git commit -qm "base"

git switch -q -c done-feature
echo x > x.txt && git add x.txt && git commit -qm "feature x"
git switch -q main
git merge -q done-feature

git switch -q -c wip-idea
echo y > y.txt && git add y.txt && git commit -qm "unfinished idea"
git switch -q main

echo "--- merged into main:"; git branch --merged
echo "--- not merged:"; git branch --no-merged

echo "--- try to delete both with -d:"
git branch -d done-feature
git branch -d wip-idea

echo "--- force delete the unfinished one (its commits become unreachable):"
git branch -D wip-idea
git branch
''',
   """
What to take from this:
- `-d` (lowercase) is the safe delete: it refuses when the branch has commits that no other branch contains. That refusal is protecting your work, not an error in your command.
- `-D` is the same as `--delete --force`. Use it only when you are sure you do not need those commits. The output prints the commit hash, and `git branch recovered <hash>` can bring the branch back soon afterwards.
- Deleting a local branch does not delete the branch on the remote. Use `git push origin --delete <name>`, and `git fetch --prune` to remove local references to branches that no longer exist on the remote.
- A common cleanup line is `git branch --merged main | grep -v '^\\*\\|main' | xargs -r git branch -d`, which deletes every merged branch except the current one and `main`. Read the list first before running it.""")

# 9 ---------------------------------------------------------------------------------------------
ex("How can I analyse a web server access log from the command line with awk, sort and uniq?",
   "Each log line has the same fields, so `awk` can pick out a column, and `sort | uniq -c | sort -rn` turns any column into a ranking. Here is a small log and the four questions people ask most often.",
   r'''cd "$(mktemp -d)"
cat > access.log <<'EOF'
203.0.113.5 - - [12/Nov/2026:10:00:01 +0000] "GET /index.html HTTP/1.1" 200 1024
198.51.100.7 - - [12/Nov/2026:10:00:03 +0000] "GET /about.html HTTP/1.1" 200 2048
203.0.113.5 - - [12/Nov/2026:10:00:07 +0000] "GET /missing.png HTTP/1.1" 404 150
192.0.2.44 - - [12/Nov/2026:10:01:12 +0000] "POST /api/login HTTP/1.1" 500 87
203.0.113.5 - - [12/Nov/2026:10:01:30 +0000] "GET /index.html HTTP/1.1" 200 1024
198.51.100.7 - - [12/Nov/2026:10:02:02 +0000] "GET /old-page HTTP/1.1" 404 150
192.0.2.44 - - [12/Nov/2026:10:02:15 +0000] "POST /api/login HTTP/1.1" 200 312
203.0.113.5 - - [12/Nov/2026:10:03:45 +0000] "GET /index.html HTTP/1.1" 200 1024
EOF

echo "--- requests per status code:"
awk '{print $9}' access.log | sort | uniq -c | sort -rn

echo "--- requests per client IP:"
awk '{print $1}' access.log | sort | uniq -c | sort -rn

echo "--- URLs that returned 404:"
awk '$9 == 404 {print $7}' access.log | sort -u

echo "--- total bytes sent:"
awk '{sum += $10} END {print sum}' access.log

echo "--- error rate (status >= 400):"
awk '$9 >= 400 {bad++} END {printf "%d of %d requests (%.1f%%)\n", bad, NR, 100*bad/NR}' access.log
''',
   """
How the pieces fit:
- `awk '{print $9}'` prints the 9th whitespace-separated field. In this log format `$1` is the client IP, `$7` the path, `$9` the status and `$10` the number of bytes. (Fields are counted after splitting on spaces, so the quoted request `"GET /index.html HTTP/1.1"` counts as three fields.)
- `uniq -c` counts **adjacent** identical lines, so the input must be sorted first. That is why `sort` comes before `uniq`, and the final `sort -rn` orders by that count, largest first.
- `$9 == 404 {print $7}` is an awk pattern-action pair: the action only runs for lines where the condition is true.
- `END { ... }` runs after the last line, and `NR` holds the number of lines read, which is how the error rate is computed.
- On a huge log, add `head -n 10` at the end of a ranking to see only the top entries.""")

# 10 --------------------------------------------------------------------------------------------
ex("How do I search a project for a word and count lines of code with find, grep and xargs?",
   "Combine `find` (which files), `grep` (which lines) and `xargs` (run a command on the list). Excluding build folders such as `target` or `node_modules` is the part people forget.",
   r'''cd "$(mktemp -d)"
mkdir -p proj/src proj/tests proj/target/debug
printf 'fn main() {\n    // TODO: parse arguments\n    println!("hi");\n}\n' > proj/src/main.rs
printf 'pub fn add(a: i32, b: i32) -> i32 {\n    a + b\n}\n// TODO: add subtract\n// TODO: add multiply\n' > proj/src/lib.rs
printf '#[test]\nfn it_works() {\n    assert_eq!(2 + 2, 4);\n}\n' > proj/tests/basic.rs
printf '// TODO generated, ignore\n' > proj/target/debug/build.rs
printf '# Notes\nTODO write docs\n' > proj/README.md

echo "--- all .rs files except build output:"
find proj -name '*.rs' -not -path 'proj/target/*' | sort

echo "--- every TODO in Rust sources, with file and line number:"
grep -rn "TODO" proj --include='*.rs' --exclude-dir=target | sort

echo "--- only the names of files that contain TODO (any type):"
grep -rl "TODO" proj --exclude-dir=target | sort

echo "--- TODO count per file:"
grep -rc "TODO" proj --include='*.rs' --exclude-dir=target | sort

echo "--- lines of Rust code per file:"
find proj -name '*.rs' -not -path 'proj/target/*' -print0 | sort -z | xargs -0 wc -l
''',
   """
Notes on the options:
- `-r` makes grep recurse into directories, `-n` adds line numbers, `-l` prints only file names and `-c` prints a count per file (including files with `0`).
- `--include='*.rs'` limits grep to matching file names and `--exclude-dir=target` skips a directory by name. Quote the pattern so that the shell does not expand it first.
- With `find ... -print0 | xargs -0`, file names are separated by a null byte instead of a space, so paths that contain spaces or quotes still work. Always use this pair when file names are not under your control.
- The last number in the `wc -l` output is the total for all files. For a rough count of code lines without blank lines you can use `grep -rvc '^\\s*$'` on the same file list.
- `ripgrep` (`rg TODO`) does the recursion, the ignoring of build folders listed in `.gitignore`, and the line numbers by default, and it is much faster on big trees. The commands above work everywhere without installing anything.""")

# 11 --------------------------------------------------------------------------------------------
ex("How do I write a safe bash script? What do set -euo pipefail and trap do?",
   "These three lines make a script fail loudly instead of continuing after an error. `trap` guarantees that cleanup runs no matter how the script ends. The script below has a normal run and a failing run so you can see both.",
   r'''cat > safe.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

workdir=$(mktemp -d)
cleanup() {
  rm -rf "$workdir"
  echo "cleanup: removed temporary folder"
}
trap cleanup EXIT

process() {
  local name=$1
  echo "processing '$name'"
  [[ -n "$name" ]] || { echo "empty name" >&2; return 1; }
  echo "$name" > "$workdir/$(echo "$name" | tr ' ' '_').txt"
}

process "first file"
process "second file"
ls "$workdir"
echo "count: $(ls "$workdir" | wc -l)"
process ""
echo "this line is never reached"
EOF

bash safe.sh
echo "exit code: $?"

echo "--- what pipefail changes:"
false | true; echo "without pipefail, status of 'false | true': $?"
set -o pipefail
false | true; echo "with pipefail, status of 'false | true': $?"
''',
   """
What each part does:
- `set -e` stops the script when a command fails. In the output the script stops at `process ""`, so the last `echo` is never reached, and the exit code is 1.
- `set -u` makes an unset variable an error. A typo such as `$workdr` stops the script instead of silently expanding to an empty string, which is how `rm -rf "$dir/"` turns into `rm -rf /`.
- `set -o pipefail` makes a pipeline fail if **any** command in it fails, not only the last one. The last two lines print the exit status of `false | true`: 0 without `pipefail`, 1 with it. With `set -e` active, that 1 would stop the script.
- `trap cleanup EXIT` runs `cleanup` whenever the shell exits: after success, after an error, and after `Ctrl+C`. That is why "cleanup: removed temporary folder" is printed even in the failing run.
- Quote every variable expansion (`"$name"`). Unquoted, a value with spaces is split into several arguments.
- Caveat: `set -e` has odd rules inside `if` conditions and `||` lists, so do not rely on it as the only error handling for important steps. Check the commands whose failure matters yourself.""")

# 12 --------------------------------------------------------------------------------------------
ex("How do I create, inspect and restore a tar.gz backup of a folder on the command line?",
   "`tar` has three jobs, and each one has a letter: `c` creates an archive, `t` lists it, `x` extracts it. Add `z` for gzip compression and `f` to name the file. Then verify the restore with `diff -r`.",
   r'''cd "$(mktemp -d)"
mkdir -p site/css site/img
echo "<h1>Home</h1>" > site/index.html
echo "body { margin: 0 }" > site/css/style.css
echo "not really a png" > "site/img/logo 1.png"

tar -czf site-backup.tar.gz site
echo "--- archive created, size is non-zero:"
test -s site-backup.tar.gz && echo yes

echo "--- contents of the archive:"
tar -tzf site-backup.tar.gz | sort

echo "--- restore into another folder:"
mkdir restore
tar -xzf site-backup.tar.gz -C restore
find restore -type f | sort

echo "--- compare original and restored copy:"
diff -r site restore/site && echo "identical"

echo "--- extract just one file:"
mkdir one
tar -xzf site-backup.tar.gz -C one site/css/style.css
cat one/site/css/style.css
''',
   """
Reading the flags:
- `-c` create, `-t` list, `-x` extract, `-z` gzip, `-f` the archive file name. The file name must come **right after** `f` when the flags are combined, as in `-czf name.tar.gz`.
- `-C folder` makes tar change into that folder first, so you can extract anywhere without `cd`.
- Paths are stored relative as you typed them (`site/...`). Archive `site`, not `/home/me/site`, because tar removes a leading `/` and the extraction folder then looks different from what you expect.
- `diff -r` compares two folders recursively and prints nothing when they match, so `&& echo identical` only prints on success. This is a cheap way to verify a backup before deleting the original.
- File names with spaces, such as `logo 1.png`, work because tar does not use the shell to read the list. They only need quotes when you type them yourself.
- For a very large folder, use `-J` and `.tar.xz` for a smaller archive, or `zstd` (`tar --zstd -cf ...`) for a faster one.""")


def block(q, a):
    return f"@@@ USER\n{q}\n@@@ ASSISTANT\n{a}\n@@@ END\n\n"


OUT.write_text("".join(block(q, a) for q, a in EXAMPLES), encoding="utf-8")
print("wrote", OUT, len(EXAMPLES), "examples", OUT.stat().st_size, "bytes")

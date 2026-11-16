"""Terminal-command examples: one curated table -> several question styles per task.

Every entry has the same task solved for Linux/macOS (bash) and Windows (PowerShell), plus a
plain-English explanation of what each part of the command does.
"""

TASKS = [
    {
        "task": "list all files in a folder including hidden ones, with sizes",
        "bash": "ls -lah",
        "ps": "Get-ChildItem -Force",
        "explain": [
            ("ls -lah", "`-l` long format, `-a` include hidden files, `-h` human-readable sizes (KB, MB)"),
            ("Get-ChildItem -Force", "`-Force` includes hidden and system files; the alias `ls` or `dir` works too"),
        ],
    },
    {
        "task": "create a folder and all missing parent folders",
        "bash": "mkdir -p projects/web/assets",
        "ps": "New-Item -ItemType Directory -Force -Path projects\\web\\assets",
        "explain": [
            ("mkdir -p", "`-p` creates every missing parent and does not fail if the folder already exists"),
            ("New-Item -Force", "`-Force` creates missing parents and does not fail if the folder exists"),
        ],
    },
    {
        "task": "copy a folder with all its contents",
        "bash": "cp -r source_folder backup_folder",
        "ps": "Copy-Item -Recurse source_folder backup_folder",
        "explain": [
            ("cp -r", "`-r` copies folders recursively"),
            ("Copy-Item -Recurse", "`-Recurse` includes all subfolders and files"),
        ],
    },
    {
        "task": "move or rename a file",
        "bash": "mv old_name.txt new_name.txt",
        "ps": "Move-Item old_name.txt new_name.txt",
        "explain": [
            ("mv", "moves a file; if the destination is in the same folder, it is simply a rename"),
            ("Move-Item", "does the same; `Rename-Item old_name.txt new_name.txt` is the dedicated rename command"),
        ],
    },
    {
        "task": "delete a folder and everything inside it",
        "bash": "rm -rf build",
        "ps": "Remove-Item -Recurse -Force build",
        "explain": [
            ("rm -rf", "`-r` recursive, `-f` no confirmation. There is no recycle bin, so double-check the name"),
            ("Remove-Item -Recurse -Force", "deletes the folder and its contents without asking; add `-WhatIf` first to preview"),
        ],
    },
    {
        "task": "show the first 20 lines and the last 20 lines of a file",
        "bash": "head -n 20 app.log\ntail -n 20 app.log",
        "ps": "Get-Content app.log -TotalCount 20\nGet-Content app.log -Tail 20",
        "explain": [
            ("head / tail", "`-n 20` selects the number of lines from the start or the end"),
            ("Get-Content", "`-TotalCount` reads only the first N lines, `-Tail` reads only the last N"),
        ],
    },
    {
        "task": "watch a log file live as new lines are added",
        "bash": "tail -f app.log",
        "ps": "Get-Content app.log -Wait -Tail 20",
        "explain": [
            ("tail -f", "`-f` (follow) keeps the command running and prints new lines as they appear; stop with Ctrl+C"),
            ("Get-Content -Wait", "`-Wait` keeps the command open for new lines, `-Tail 20` first shows the last 20"),
        ],
    },
    {
        "task": "count the lines in a file",
        "bash": "wc -l file.txt",
        "ps": "(Get-Content file.txt).Count",
        "explain": [
            ("wc -l", "counts newline characters, so a last line without a trailing newline is not counted"),
            ("(Get-Content file.txt).Count", "reads the file into an array of lines and counts them; for huge files use `Get-Content file.txt -ReadCount 1000`"),
        ],
    },
    {
        "task": "find files by name pattern, for example every .log file below the current folder",
        "bash": "find . -type f -name \"*.log\"",
        "ps": "Get-ChildItem -Recurse -File -Filter *.log",
        "explain": [
            ("find . -type f -name", "`.` start here, `-type f` files only, `-name` matches the pattern (keep the quotes so the shell does not expand it)"),
            ("Get-ChildItem -Recurse -File -Filter", "`-Recurse` goes into subfolders, `-Filter` is faster than `-Include`"),
        ],
    },
    {
        "task": "see which programs are using the most memory",
        "bash": "ps aux --sort=-%mem | head -n 10",
        "ps": "Get-Process | Sort-Object WorkingSet -Descending | Select-Object -First 10 Name, Id, @{n='MB';e={[int]($_.WorkingSet/1MB)}}",
        "explain": [
            ("ps aux --sort=-%mem", "lists all processes sorted by memory use, highest first; `head` keeps the top 10 (on macOS use `ps aux -m | head`)"),
            ("Get-Process | Sort-Object", "sorts by working-set memory and converts bytes to MB for readability"),
        ],
    },
    {
        "task": "check free disk space",
        "bash": "df -h",
        "ps": "Get-PSDrive -PSProvider FileSystem",
        "explain": [
            ("df -h", "shows each mounted disk with sizes in human-readable units"),
            ("Get-PSDrive -PSProvider FileSystem", "shows Used and Free space for every drive letter (values are in bytes)"),
        ],
    },
    {
        "task": "download a file from a URL",
        "bash": "curl -L -o file.zip https://example.com/file.zip",
        "ps": "Invoke-WebRequest -Uri https://example.com/file.zip -OutFile file.zip",
        "explain": [
            ("curl -L -o", "`-L` follows redirects, `-o` names the output file"),
            ("Invoke-WebRequest -OutFile", "saves the response body to a file; add `$ProgressPreference='SilentlyContinue'` first to make large downloads much faster"),
        ],
    },
    {
        "task": "set an environment variable for the current session and read it",
        "bash": "export API_URL=http://localhost:3000\necho \"$API_URL\"",
        "ps": "$env:API_URL = \"http://localhost:3000\"\n$env:API_URL",
        "explain": [
            ("export", "makes the variable available to programs started from this shell; it disappears when the terminal closes"),
            ("$env:NAME", "reads or sets a process-level environment variable; use `setx NAME value` to store it permanently for future terminals"),
        ],
    },
    {
        "task": "extract a .zip archive into a folder",
        "bash": "unzip archive.zip -d output_folder",
        "ps": "Expand-Archive -Path archive.zip -DestinationPath output_folder",
        "explain": [
            ("unzip -d", "`-d` chooses the destination folder"),
            ("Expand-Archive", "built into PowerShell 5+; add `-Force` to overwrite existing files"),
        ],
    },
    {
        "task": "create a .zip archive from a folder",
        "bash": "zip -r site.zip site_folder",
        "ps": "Compress-Archive -Path site_folder -DestinationPath site.zip",
        "explain": [
            ("zip -r", "`-r` includes subfolders"),
            ("Compress-Archive", "creates the zip; add `-Force` to overwrite an existing archive"),
        ],
    },
    {
        "task": "show the current user, computer name and operating system",
        "bash": "whoami\nhostname\nuname -a",
        "ps": "whoami\nhostname\n(Get-CimInstance Win32_OperatingSystem).Caption",
        "explain": [
            ("whoami / hostname", "print the current user and the machine name (same in both shells)"),
            ("uname -a / Win32_OperatingSystem", "show kernel details on Linux/macOS or the Windows edition name"),
        ],
    },
    {
        "task": "replace text in every .txt file of a folder",
        "bash": "sed -i 's/old/new/g' *.txt",
        "ps": "Get-ChildItem *.txt | ForEach-Object { (Get-Content $_) -replace 'old','new' | Set-Content $_ }",
        "explain": [
            ("sed -i 's/old/new/g'", "`-i` edits in place, `s/old/new/g` replaces every occurrence on each line (on macOS write `sed -i '' ...`). Make a backup or use git first"),
            ("-replace", "uses a regular expression; the file is rewritten by `Set-Content`, so test on a copy first"),
        ],
    },
    {
        "task": "run a command repeatedly for every file in a folder",
        "bash": "for f in *.png; do echo \"Processing $f\"; done",
        "ps": "Get-ChildItem *.png | ForEach-Object { Write-Host \"Processing $($_.Name)\" }",
        "explain": [
            ("for f in *.png", "the shell expands the pattern to the file list; always quote \"$f\" so names with spaces still work"),
            ("ForEach-Object", "runs the script block once per file; `$_` is the current file object"),
        ],
    },
    {
        "task": "show the 10 largest files in the current folder tree",
        "bash": "find . -type f -exec du -h {} + | sort -rh | head -n 10",
        "ps": "Get-ChildItem -Recurse -File | Sort-Object Length -Descending | Select-Object -First 10 FullName, @{n='MB';e={[math]::Round($_.Length/1MB,1)}}",
        "explain": [
            ("du -h | sort -rh | head", "`du` measures sizes, `sort -rh` orders human-readable numbers largest first, `head` keeps the top 10"),
            ("Sort-Object Length -Descending", "sorts by file size in bytes and shows MB with one decimal"),
        ],
    },
    {
        "task": "start a simple web server for the files in the current folder",
        "bash": "python3 -m http.server 8000",
        "ps": "python -m http.server 8000",
        "explain": [
            ("python -m http.server 8000", "serves the current folder at http://localhost:8000. It is only for local testing, not for production"),
            ("Ctrl+C", "stops the server"),
        ],
    },
    {
        "task": "check which version of Node, npm, Python, Rust and Git are installed",
        "bash": "node --version\nnpm --version\npython3 --version\nrustc --version\ngit --version",
        "ps": "node --version; npm --version; python --version; rustc --version; git --version",
        "explain": [
            ("--version", "every one of these tools prints its version; a \"not found\" message means it is missing or not on your PATH"),
        ],
    },
    {
        "task": "compress and decompress a .tar.gz archive",
        "bash": "tar -czf backup.tar.gz my_folder\ntar -xzf backup.tar.gz",
        "ps": "tar -czf backup.tar.gz my_folder\ntar -xzf backup.tar.gz",
        "explain": [
            ("tar -czf", "`c` create, `z` gzip-compress, `f` file name"),
            ("tar -xzf", "`x` extract; Windows 10 and later ship with a compatible `tar.exe`"),
        ],
    },
    {
        "task": "empty a file without deleting it",
        "bash": ": > file.log",
        "ps": "Clear-Content file.log",
        "explain": [
            (": > file.log", "redirecting nothing into the file truncates it to zero bytes"),
            ("Clear-Content", "removes the contents but keeps the file and its permissions"),
        ],
    },
    {
        "task": "show open network connections and listening ports",
        "bash": "ss -tulpn",
        "ps": "Get-NetTCPConnection -State Listen | Select-Object LocalAddress, LocalPort, OwningProcess",
        "explain": [
            ("ss -tulpn", "`t` TCP, `u` UDP, `l` listening, `p` process, `n` numeric ports (needs sudo to show every process name)"),
            ("Get-NetTCPConnection -State Listen", "lists listening ports with the owning process ID; look it up with `Get-Process -Id <id>`"),
        ],
    },
]

TEMPLATES_BASH = [
    "How do I {task} in bash?",
    "Linux terminal: how can I {task}?",
]
TEMPLATES_PS = [
    "How do I {task} in PowerShell?",
    "Windows terminal: how can I {task}?",
]
TEMPLATES_BOTH = [
    "Show me the command to {task} on both Linux and Windows.",
]


def _explain(items):
    return "\n".join(f"- `{k}`: {v}" if not k.startswith("(") else f"- {k}: {v}" for k, v in items)


def generate():
    out = []
    for t in TASKS:
        for tpl in TEMPLATES_BASH:
            out.append((tpl.format(task=t["task"]),
                        f"```bash\n{t['bash']}\n```\n\nHow it works:\n{_explain(t['explain'])}"))
        for tpl in TEMPLATES_PS:
            out.append((tpl.format(task=t["task"]),
                        f"```powershell\n{t['ps']}\n```\n\nHow it works:\n{_explain(t['explain'])}"))
        for tpl in TEMPLATES_BOTH:
            out.append((tpl.format(task=t["task"]),
                        f"Linux/macOS (bash):\n\n```bash\n{t['bash']}\n```\n\nWindows (PowerShell):\n\n```powershell\n{t['ps']}\n```\n\n"
                        f"What the commands do:\n{_explain(t['explain'])}"))
    return out

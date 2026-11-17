"""Build data/staging/claude_powershell_19.txt. Every script is RUN in Windows PowerShell 5.1 inside an empty
folder (C:\\work\\demo) and the real output is pasted into the answer."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

F = "`" * 3
OUT = Path(r"C:\Projects\Mavo\Coding 1 2B\data\staging\claude_powershell_19.txt")
WORK = Path(r"C:\work")
DEMO = WORK / "demo"
EXAMPLES = []


def run_ps(script):
    if DEMO.exists():
        shutil.rmtree(DEMO)
    DEMO.mkdir(parents=True)
    f = WORK / "_s.ps1"
    f.write_text(script.strip() + "\n", encoding="ascii", newline="\r\n")
    p = subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(f)],
        cwd=str(DEMO), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", timeout=120,
    )
    out = "\n".join(l.rstrip() for l in p.stdout.replace("\r", "").split("\n")).strip("\n")
    if "_s.ps1" in out:
        print("UNCAUGHT ERROR IN SCRIPT:\n", script[:400], "\n---\n", out)
        sys.exit(1)
    return out


def ex(question, intro, script, after, shown=None):
    out = run_ps(script)
    code = (shown or script).strip()
    assert F not in code
    ans = f"{intro.strip()}\n\n{F}powershell\n{code}\n{F}\n\nOutput:\n\n{F}\n{out}\n{F}\n\n{after.strip()}"
    EXAMPLES.append((question, ans))
    print("---- example", len(EXAMPLES), "----\n" + out + "\n")


# 1 ---------------------------------------------------------------------------------------------
ex("How do I find the biggest files in a folder tree with PowerShell?",
   "Use `Get-ChildItem -Recurse -File`, sort by `Length` and take the first few. PowerShell passes real objects through the pipeline, so you sort by a property and do not parse text. The first lines only create sample data (`'x' * 5000` makes a string of exactly 5000 characters, and `-NoNewline` stops PowerShell from adding a line break, so the file has exactly that size), so you can run the whole thing in an empty folder.",
   r'''
New-Item -ItemType Directory -Force -Path logs, src | Out-Null
function New-File($Path, $Size) { Set-Content -Path $Path -Value ('x' * $Size) -NoNewline }
New-File logs\app.log 5000
New-File logs\old.log 12000
New-File src\main.rs  800
New-File src\lib.rs   2500
New-File README.md    300

# the three biggest files
Get-ChildItem -Recurse -File |
    Sort-Object Length -Descending |
    Select-Object -First 3 Name, Length |
    Format-Table -AutoSize

# the same with a calculated property, sizes in KB
Get-ChildItem -Recurse -File |
    Sort-Object Length -Descending |
    Select-Object -First 3 Name, @{ Name = 'KB'; Expression = { [math]::Round($_.Length / 1KB, 1) } }
''',
   "`Select-Object` with a hashtable (`Name` and `Expression`) adds a calculated column; `$_` is the current file. If you want the full path instead of the name, select `FullName`. Add `-ErrorAction SilentlyContinue` to `Get-ChildItem` when some folders deny access and you do not want error messages in the middle of the list.")

# 2 ---------------------------------------------------------------------------------------------
ex("How do I search for text inside files with PowerShell, like grep?",
   "`Select-String` is the grep of PowerShell. It is case-insensitive by default, accepts a regular expression, and shows the file name and line number. The first lines create two small log files.",
   r'''
Set-Content app.log @(
    'start ok',
    'user=ann action=login',
    'ERROR disk full',
    'user=bob action=logout',
    'error timeout after 30s'
)
Set-Content web.log @('GET /index 200', 'GET /missing 404')

# every line that contains "error", in any case
Select-String -Path *.log -Pattern 'error'

# one line before and after each match
Select-String -Path app.log -Pattern 'disk full' -Context 1,1

# only the first match per file, and only the file names
Select-String -Path *.log -Pattern '\d{3}$|error' -List | Select-Object -ExpandProperty Filename

# pull out part of the match with a capture group
Select-String -Path app.log -Pattern 'user=(\w+)' |
    ForEach-Object { $_.Matches[0].Groups[1].Value }
''',
   "Use `-CaseSensitive` when the case matters and `-SimpleMatch` when the pattern should be taken literally and not as a regular expression. Add `-Recurse` by feeding it files from `Get-ChildItem -Recurse -Filter *.log | Select-String ...`; `Select-String` itself has no `-Recurse` switch.")

# 3 ---------------------------------------------------------------------------------------------
ex("How can I rename many files at once in PowerShell, and check the result first?",
   "Pipe the files into `Rename-Item` and give `-NewName` a script block that computes the new name from `$_`. Run it first with `-WhatIf`: it prints what would happen and changes nothing. In this run the folder was `C:\\work\\demo`; your path will differ.",
   r'''
1..3 | ForEach-Object { New-Item -ItemType File -Name ('IMG_{0:000}.jpg' -f $_) | Out-Null }
New-Item -ItemType File -Name 'notes.txt' | Out-Null

# 1. preview: nothing is renamed
Get-ChildItem -Filter 'IMG_*.jpg' |
    Rename-Item -NewName { $_.Name -replace '^IMG_', 'holiday-' } -WhatIf

# 2. do it
Get-ChildItem -Filter 'IMG_*.jpg' |
    Rename-Item -NewName { $_.Name -replace '^IMG_', 'holiday-' }

(Get-ChildItem).Name
''',
   "`-replace` takes a regular expression, so `^IMG_` matches only at the start of the name. Filtering with `-Filter 'IMG_*.jpg'` first keeps `notes.txt` out of the operation. Read the `-WhatIf` lines before you run the real command: they show every old and new name. For a pattern that cannot be written as a regex replacement, compute the new name inside the script block.")

# 4 ---------------------------------------------------------------------------------------------
ex("How do I read a CSV file in PowerShell, filter it, add up a column and write a new CSV?",
   "`Import-Csv` turns every row into an object with one property per column. Every value is a string, so convert numbers before you compare or add them. The first lines write a small CSV file.",
   r'''
@'
item,category,qty,price
pen,office,10,1.50
paper,office,5,4.00
coffee,kitchen,2,7.25
tea,kitchen,1,3.10
'@ | Set-Content orders.csv

$rows = Import-Csv orders.csv |
    ForEach-Object {
        [pscustomobject]@{
            item     = $_.item
            category = $_.category
            total    = [double]$_.qty * [double]$_.price
        }
    }

# filter
$rows | Where-Object { $_.total -gt 10 } | Format-Table -AutoSize

# add up per category
$rows | Group-Object category | ForEach-Object {
    [pscustomobject]@{
        category = $_.Name
        total    = ($_.Group | Measure-Object total -Sum).Sum
    }
}

# write a new file and show it
$rows | Export-Csv totals.csv -NoTypeInformation
Get-Content totals.csv
''',
   "In Windows PowerShell 5.1 `Export-Csv` writes a type line (`#TYPE ...`) at the top unless you pass `-NoTypeInformation`; PowerShell 7 does not need it. If your CSV uses semicolons (common in some European locales), pass `-Delimiter ';'` to `Import-Csv` and `Export-Csv`.")

# 5 ---------------------------------------------------------------------------------------------
ex("How do I read and change a JSON file in PowerShell? My nested data comes out as @{...} text when I write it back.",
   "`ConvertFrom-Json` gives you objects you can change with normal property syntax, and `ConvertTo-Json` writes them back. The cause of your `@{...}` text is the `-Depth` parameter: `ConvertTo-Json` only goes two levels deep by default and writes everything below as a string. The demo shows both.",
   r'''
@'
{ "name": "demo", "server": { "port": 8080, "tls": { "enabled": false, "ciphers": ["a", "b"] } } }
'@ | Set-Content config.json

$config = Get-Content config.json -Raw | ConvertFrom-Json
$config.server.port = 9090
$config.server.tls.enabled = $true

'--- default depth ---'
$config | ConvertTo-Json -Compress

'--- -Depth 5 ---'
$config | ConvertTo-Json -Depth 5 -Compress

$config | ConvertTo-Json -Depth 5 | Set-Content config.json
(Get-Content config.json -Raw | ConvertFrom-Json).server.tls.enabled
''',
   "Always pass `-Depth` when the data has more than two levels. `-Raw` makes `Get-Content` return the whole file as one string, which is the form `ConvertFrom-Json` is designed for. Property assignment (`$config.server.port = 9090`) works because `ConvertFrom-Json` returns ordinary objects.")

# 6 ---------------------------------------------------------------------------------------------
ex("My PowerShell try/catch does not catch the error from Get-Content. Why, and how do I check the exit code of a normal program?",
   "Most cmdlet errors are non-terminating: PowerShell prints them and carries on, and `catch` only sees terminating errors. Add `-ErrorAction Stop` to the command (or set `$ErrorActionPreference = 'Stop'`) to turn them into exceptions. Native programs such as `git` or `ping` do not throw at all: you look at `$LASTEXITCODE`.",
   r'''
Write-Output '--- without -ErrorAction Stop ---'
try {
    Get-Content missing.txt 2>$null
    Write-Output 'no exception, the script just continues'
} catch {
    Write-Output 'caught'
}

Write-Output '--- with -ErrorAction Stop ---'
try {
    Get-Content missing.txt -ErrorAction Stop
    Write-Output 'not reached'
} catch {
    Write-Output ('caught: ' + $_.Exception.GetType().Name)
}

Write-Output '--- a native program ---'
cmd /c exit 3
Write-Output ('exit code: ' + $LASTEXITCODE)
if ($LASTEXITCODE -ne 0) { Write-Output 'the program failed' }
''',
   "`$LASTEXITCODE` holds the exit code of the last native program; it is not changed by cmdlets, so read it right after the call. `$?` is only true or false and also reflects cmdlet failures. For a script that should stop on the first problem, put `$ErrorActionPreference = 'Stop'` at the top, and still check `$LASTEXITCODE` after every external program, because that setting does not make a failing external program stop the script (PowerShell 7.4 has an opt-in setting for that).")

# 7 ---------------------------------------------------------------------------------------------
ex("How do I write a PowerShell function with required parameters and validation?",
   "Put a `param()` block with attributes inside the function. `[Parameter(Mandatory)]` makes PowerShell ask for a missing value, and `[ValidateSet]` and `[ValidateRange]` reject bad values before your code runs, with a clear message and without any `if` statements of your own.",
   r'''
function Write-Log {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Message,

        [ValidateSet('info', 'warn', 'error')]
        [string]$Level = 'info',

        [ValidateRange(1, 5)]
        [int]$Indent = 1
    )
    ('{0}[{1}] {2}' -f ('  ' * ($Indent - 1)), $Level.ToUpper(), $Message)
}

Write-Log -Message 'started'
Write-Log 'disk is almost full' -Level warn -Indent 2

foreach ($bad in @(@{ Level = 'loud' }, @{ Indent = 9 })) {
    try {
        Write-Log -Message 'x' @bad
    } catch {
        $_.Exception.Message
    }
}
''',
   "The second call passes `Message` by position, because it is the first parameter. The `@bad` syntax (splatting) passes the hashtable entries as named parameters, which is a tidy way to build a call from data. `[CmdletBinding()]` adds the common parameters such as `-Verbose` and `-ErrorAction` to your function for free.")

# 8 ---------------------------------------------------------------------------------------------
ex("How do I run things in the background in PowerShell and collect the results?",
   "`Start-Job` runs a script block in a separate process and returns a job object; `Wait-Job` waits for it and `Receive-Job` returns its output. Variables from your session are not visible inside the job, so pass values in with `-ArgumentList` (or `$using:`).",
   r'''
$jobs = 1..3 | ForEach-Object {
    Start-Job -ArgumentList $_ -ScriptBlock {
        param($n)
        Start-Sleep -Milliseconds (300 * (4 - $n))   # the first job is the slowest
        [pscustomobject]@{ Job = $n; Square = $n * $n }
    }
}

$jobs | Wait-Job | Out-Null
$jobs | Receive-Job | Sort-Object Job | Select-Object Job, Square
$jobs | Remove-Job
''',
   "The jobs finish in the order 3, 2, 1 because of the different sleeps, so the result is sorted again by `Job`. Jobs have a start-up cost (a new PowerShell process each), so they pay off for work that takes seconds, not for tiny tasks. PowerShell 7 adds `ForEach-Object -Parallel`, which is lighter; Windows PowerShell 5.1 does not have it.")

# 9 ---------------------------------------------------------------------------------------------
ex("What is the difference between setting an environment variable in a PowerShell session and setting it permanently?",
   "`$env:NAME = 'value'` changes the variable for the current PowerShell process and for programs it starts, and it disappears when the window closes. A permanent change is a different call that writes to the user or machine settings, and it only affects programs started afterwards. The script reads the same variable from the three places (the persistent one is only read here, not changed).",
   r'''
$env:MAVO_DEMO_VAR = 'hello'

'process : ' + [Environment]::GetEnvironmentVariable('MAVO_DEMO_VAR', 'Process')
'user    : ' + [Environment]::GetEnvironmentVariable('MAVO_DEMO_VAR', 'User')

# a program started from here inherits the process variable
cmd /c echo child sees: %MAVO_DEMO_VAR%

Remove-Item Env:\MAVO_DEMO_VAR
'after Remove-Item: [' + $env:MAVO_DEMO_VAR + ']'
''',
   "To keep a variable for your user account, run `[Environment]::SetEnvironmentVariable('NAME', 'value', 'User')` (or `setx NAME value`). Windows applications that are already running do not see it, so open a new terminal. Use the `'Machine'` scope only from an administrator shell, and be careful with `PATH`: read the current value, append to it, and write it back, never overwrite it with a single folder.")

# 10 --------------------------------------------------------------------------------------------
ex("How do I find duplicate files in PowerShell?",
   "Files with the same content have the same hash. `Get-FileHash` computes it (SHA256 by default), `Group-Object Hash` groups equal ones, and groups with more than one member are duplicates. Comparing names or sizes is not enough, since two different files can have the same size.",
   r'''
foreach ($pair in @(('a.txt', 'same text'), ('b.txt', 'same text'), ('c.txt', 'other text'), ('d.txt', 'same text'))) {
    Set-Content -Path $pair[0] -Value $pair[1] -NoNewline
}

Get-ChildItem -File |
    Get-FileHash |
    Group-Object Hash |
    Where-Object { $_.Count -gt 1 } |
    ForEach-Object {
        'duplicates (' + $_.Count + ' files): ' + (($_.Group | ForEach-Object { Split-Path $_.Path -Leaf }) -join ', ')
    }
''',
   "On a big folder this reads every file, so first group by `Length` and only hash the files whose size occurs more than once; that avoids reading most of the files. To delete duplicates, keep the first of each group and pipe the rest to `Remove-Item -WhatIf`, and only remove `-WhatIf` after you have looked at the list.")

# 11 --------------------------------------------------------------------------------------------
ex("How do I work with file paths in PowerShell without string handling mistakes?",
   "Use the path cmdlets instead of joining strings with backslashes: `Join-Path` adds exactly one separator, `Split-Path` takes a path apart, and `Test-Path` checks that something exists. The .NET class `[System.IO.Path]` has the rest.",
   r'''
$dir  = 'C:\data\reports'
$file = Join-Path $dir '2026\summary.txt'

$file
Split-Path $file -Parent
Split-Path $file -Leaf
[System.IO.Path]::GetExtension($file)
[System.IO.Path]::GetFileNameWithoutExtension($file)
[System.IO.Path]::ChangeExtension($file, '.csv')

# a path that exists, and one that does not
New-Item -ItemType Directory -Name sub | Out-Null
Test-Path .\sub
Test-Path .\nothing
Test-Path .\sub -PathType Leaf
''',
   "`Join-Path` also works when the first part already ends with a backslash, which plain string concatenation gets wrong (you end up with a double backslash or none). `Test-Path -PathType Leaf` is true only for files and `-PathType Container` only for folders. Paths with square brackets in the name (`file[1].txt`) are read as wildcards by most cmdlets; use `-LiteralPath` for those.")


# ------------------------------------------------------------------------------ write
text = ""
for q, a in EXAMPLES:
    text += f"@@@ USER\n{q}\n@@@ ASSISTANT\n{a}\n@@@ END\n\n"
OUT.write_text(text, encoding="utf-8")
print("wrote", OUT, len(EXAMPLES), "examples", len(text), "chars")

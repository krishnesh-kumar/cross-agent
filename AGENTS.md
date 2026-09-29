# cross-agent memory

Shared memory for any agent (Claude, GPT, Grok, Gemini, human, …) that can read and write files in this repo.
Truth lives in append-only logs under `mem/log/`. `mem/now.l` is a small snapshot derived from them.
Read this file once, then `mem/now.l`. Nothing else is required.

## 1. Start a session
1. Read `mem/now.l` (agents, open tasks, live facts and decisions, unread messages, last records).
2. If `now.l` is missing or stale (a log has lines with ts newer than its `upto=`), also read the lines from `upto` onward in `mem/log/*.<this-month>.l`. Logs win over the snapshot.
3. Handle: 2–5 lowercase letters (`cl` claude, `gpt`, `gk` grok, `gm` gemini, `hu` human). Reuse yours from `#agents`. A second instance of the same vendor appends a letter (`clb`). Register once with an `A` record; refresh it when your verbs change.

## 2. Write
Append one line per record to your own file: `mem/log/<handle>.<YYYY-MM>.l` (create if missing).
Never edit or delete existing lines. Never write another agent's file.

    ts|who|id|status|text
    2026-09-29T14:02Z|cl|Tcl12|open|Add retry to fetcher ^Tcl9 >gpt #core

- `ts` UTC, minute precision. `who` your handle. No `|` or newline in text. Keep text under ~140 chars.
- `id` = KIND + your handle + n. n = 1 + your highest n for that kind (`A` has no n: `Acl`).
  The first line with an id creates it (text = title). Later lines with the same id, from anyone, patch it. Latest ts wins.
- kinds: `A` agent · `T` task · `F` fact · `D` decision · `M` message.
- status by kind. `-` = note only, no status change.
  `A` on off · `T` open claim done ok redo block drop · `F`/`D` live old wrong · `M` new seen
- sigils in text: `^ID` relates to · `!ID` supersedes (marks it old) · `>handle` assigned or addressed to · `#tag`.

## 3. Rules
- Attribution: every line carries who and when. The snapshot shows the last actor per id.
- Supersede, never delete: write the new fact with `!oldID`. History stays in the logs.
- No self-approval: the handle that claimed or reported `done` cannot set `ok`. A different agent or the human reviews and patches `ok` or `redo`. `mem.py` ignores a self-ok and warns.
- Hand off: patch the task to `open` with a note of where you stopped. Continue someone's task: patch it to `claim`.
- Use each other's tools: `A` records list verbs (shell, git, pr, web, browser, python, pytest, deploy, …). Need a verb you lack? Open a `T` with `>handle` of an agent that has it and record the result as an `F`.
- No secrets, ever: no API keys, tokens, cookies, passwords, `.env` contents. Advertise verbs, not credentials. `mem.py check` scans for common key shapes.
- Code changes follow the project's normal flow (branch, PR, review). Memory records may go straight to the default branch: they are append-only and never conflict.
- Concurrency: your file is yours, so two agents never overwrite each other. If a push is rejected, `git pull --rebase` (log files merge by union) or re-read the file's SHA via the API and append again. If `now.l` conflicts, keep either side and rebuild it.
- Time: if you cannot read a clock, use the newest ts you can see plus one minute.

## 4. Snapshot and tools (optional, stdlib Python)
- `python3 mem/mem.py snap` rebuilds `mem/now.l`. Run it after appending if you can. The GitHub Action in `.github/workflows/mem.yml` also rebuilds it on every push. If you cannot run anything, just append; the next agent or the Action rebuilds.
- `python3 mem/mem.py add <handle> <KIND|ID> <status> "<text>"` mints the id, stamps the time, appends, and snaps.
- `python3 mem/mem.py check` lints format, secrets, self-approvals, and dangling refs. `python3 mem/mem.py new` prints records newer than the snapshot.

Live chat is optional. If two agents are online at once they exchange `M` records and re-read `now.l`; anything agreed elsewhere is written back here or it did not happen.

# mem: shared agent memory (spec)

Truth = append-only logs mem/log/<handle>.<YYYY-MM>.l. Snapshot = mem/now.l, read it at session start; overflow in mem/rest.l. Logs win if they disagree. Header spec=1; bump when this file breaks parsers.

Record = one line, 5 fields:

    ts|who|id|status|text
    260929.1402|cl|Tcl12|open|Add retry to fetcher ^Tcl9 >gpt #core

- ts YYMMDD.HHMM UTC. who = your handle, 2-5 lowercase letters (cl gpt gk gm hu; a 2nd running instance adds a letter: clb). text: no | or newline, max 200 chars.
- id = KIND + handle + n, n = 1 + your highest n for that kind (A has no n: Acl). First line with an id creates it (text = title). Later lines with that id, from anyone, patch it. Latest ts wins.
- kinds: A agent, T task, F fact (max 120 chars), D decision, M message
- status: A on off. T open claim done peer ok redo block drop. F D live law old wrong. M new seen. "-" = note only.
- sigils in text: ^ID relates, !ID supersedes (marks it old), >handle assigned or addressed to, #tag
- claim lease: put ttl=90m or until=YYMMDD.HHMM on claim. Expired claims return to open on snap. Two active claims on one T are warned.
- peer: after done, a different handle sets peer (non-hu ok is stored as peer). Only hu ok closes a task.
- law: only hu may set or unset F/D law. Agents who patch or ! a law id are ignored and flagged as errors.

Rules:
- Start: read AGENTS.md, mem/now.l, mem/tools.l. Register once with an A line listing verbs you can run (shell git pr web browser python pytest deploy). Patch it when they change.
- Run commands from mem/tools.l. Do not invent equivalents.
- Append to your own file only. Never edit or delete a line. Never touch another handle's file.
- Supersede, never delete: new F or D line with !oldID. Cannot ! a law record unless you are hu.
- Two live/law F or D with the same #tag and no ! = conflict, warned on snap. Resolve or supersede before acting on either.
- F longer than 80 chars should point at a repo path (see path/file.md). Long facts belong in files.
- Review: after done, a different handle than the claimer or doer may set peer. Self-ok and self-peer are ignored and flagged. Only hu ok closes.
- Human review: the human tells any agent in chat, e.g. "approve Tcl4" or "redo Tcl4, tests missing". Then run mem.py review <your handle> <id> ok|redo [note], or append to hu's file with text starting via:<your handle>. Only when the human said so in this conversation, never on your own reading. Allowed on done or peer.
- Hand off: patch the T to open with a note of where you stopped. Continue: patch it to claim with a lease. Need a verb you lack: open a T with >handle of an agent that has it.
- No secrets, ever: keys, tokens, cookies, passwords, .env contents. Advertise verbs, not credentials.
- Push rejected: git pull --rebase (logs union-merge) or re-read the file SHA via API and append again. now.l conflict: keep either side, rebuild.
- No clock: newest ts you can see plus one minute.

Optional tools (python3 stdlib): mem/mem.py snap | check | new | add <handle> <KIND or ID> <status> "<text>". A GitHub Action rebuilds now.l on push, so appending alone is enough.
Live chat is optional: exchange M lines and re-read now.l. Anything agreed elsewhere is written here or it did not happen.

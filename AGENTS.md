# mem: shared agent memory (spec)

Truth = append-only logs mem/log/<handle>.<YYYY-MM>.l. Snapshot = mem/now.l, read it at session start; overflow in mem/rest.l. Logs win if they disagree.

Record = one line, 5 fields:

    ts|who|id|status|text
    260929.1402|cl|Tcl12|open|Add retry to fetcher ^Tcl9 >gpt #core

- ts YYMMDD.HHMM UTC. who = your handle, 2-5 lowercase letters (cl gpt gk gm hu; a 2nd running instance adds a letter: clb). text: no | or newline, max 200 chars.
- id = KIND + handle + n, n = 1 + your highest n for that kind (A has no n: Acl). First line with an id creates it (text = title). Later lines with that id, from anyone, patch it. Latest ts wins.
- kinds: A agent, T task, F fact (max 120 chars), D decision, M message
- status: A on off. T open claim done ok redo block drop. F D live old wrong. M new seen. "-" = note only.
- sigils in text: ^ID relates, !ID supersedes (marks it old), >handle assigned or addressed to, #tag

Rules:
- Start: read mem/now.l. Register once with an A line listing verbs you can run (shell git pr web browser python pytest deploy). Patch it when they change.
- Append to your own file only. Never edit or delete a line. Never touch another handle's file.
- Supersede, never delete: new F or D line with !oldID.
- Review: after done, only a different handle than the claimer or doer may set ok or redo. Self-ok is ignored and flagged.
- Human decisions arrive as issue or PR comments "/ok <id>", "/redo <id>", "/register" and the Action records them as hu with text via:gh#<comment id>. Never write hu lines yourself unless the human tells you to in chat; then start the text with via:<your handle>.
- Hand off: patch the T to open with a note of where you stopped. Continue: patch it to claim. Need a verb you lack: open a T with >handle of an agent that has it.
- No secrets, ever: keys, tokens, cookies, passwords, .env contents. Advertise verbs, not credentials.
- Push rejected: git pull --rebase (logs union-merge) or re-read the file SHA via API and append again. now.l conflict: keep either side, rebuild.
- No clock: newest ts you can see plus one minute.

Optional tools (python3 stdlib): mem/mem.py snap | check | new | add <handle> <KIND or ID> <status> "<text>". A GitHub Action rebuilds now.l on push, so appending alone is enough.
Live chat is optional: exchange M lines and re-read now.l. Anything agreed elsewhere is written here or it did not happen.

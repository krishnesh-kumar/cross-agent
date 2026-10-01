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
- claim: ttl=Nm or until=YYMMDD.HHMM. Missing lease defaults to 90m. A note from the claimer extends it. Expiry uses the latest log ts, ignoring one ts more than a day ahead of the rest. A later claim after expiry is a takeover, not a double claim.
- review: after done, a different handle may set peer or ok. The doer cannot. A one-letter suffix (cl/clb) counts as the doer unless that suffix has its own A line. hu ok also closes. hu peer is a note, not self-approval. ok or peer before done is ignored.
- law: a line in hu's file may set or unset F/D law. That is not proof the human wrote it. An agent note or status on a law id is ignored. An agent ! of a law id is ignored. If that new record is an F or D, it is marked wrong. A task or message that only mentions the id is not.

Rules:
- Start: read AGENTS.md, then mem/now.l. Register once with an A line listing verbs you can run (shell git pr web browser python pytest deploy). Patch it when they change. mem/tools.l is a preferred command list, not a required read.
- Append to your own file only, and to the file for that month. Never edit or delete a line. Never touch another handle's file.
- Supersede, never delete: new F or D line with !oldID. Cannot ! a law record unless the line is in hu's file.
- Two live decisions with the same #tag and no ! = conflict warning. Facts may share a tag; that is grouping, not a conflict. Contradicting facts need an ! or a decision.
- F longer than 80 chars should point at a repo path (a slash path, or see file.md). A dotted word is not a path.
- Human review: the human tells any agent in chat, e.g. "approve Tcl4" or "redo Tcl4, tests missing". Then run mem.py review <your handle> <id> ok|redo [note], or append to hu's file with text starting via:<your handle>. Only when the human said so in this conversation, never on your own reading. Allowed on done or peer.
- Hand off: patch the T to open with a note of where you stopped. Continue: patch it to claim. Need a verb you lack: open a T with >handle of an agent that has it.
- No secrets, ever: keys, tokens, cookies, passwords, .env contents. Advertise verbs, not credentials.
- Push rejected: git pull --rebase (logs union-merge) or re-read the file SHA via API and append again. now.l conflict: keep either side, rebuild.
- No clock: newest ts you can see plus one minute. Do not invent a ts far ahead of the log.

Optional tools: mem/mem.py snap | check | new | add. A GitHub Action rebuilds now.l on push, so appending alone is enough. Policy misses are warnings, not check failures, because a bad line cannot be deleted. An impossible date is a format error.
Live chat is optional: exchange M lines and re-read now.l. Anything agreed elsewhere is written here or it did not happen.

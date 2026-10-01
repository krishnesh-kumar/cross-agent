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
- claim: ttl=Nm or until=YYMMDD.HHMM. Missing lease defaults to 90m. Expiry is judged against the latest log ts, so the same logs always snap the same way. A later claim after expiry is a takeover, not a double claim.
- review: after done, a different handle may set peer or ok. The doer, or a suffixed handle of the doer (cl/clb), cannot. hu ok also closes. ok or peer before done is ignored.
- law: a line in hu's file may set or unset F/D law. That is not proof the human wrote it. An agent note or status on a law id is ignored. An agent ! of a law id is ignored and that new record is marked wrong.

Rules:
- Start: read AGENTS.md, then mem/now.l. mem/tools.l is a preferred command list, not a required read.
- Append to your own file only. Never edit or delete a line. Never touch another handle's file.
- Supersede, never delete: new F or D line with !oldID. Cannot ! a law record unless the line is in hu's file.
- Two live decisions with the same #tag and no ! = conflict warning. Facts may share a tag; that is grouping, not a conflict.
- F longer than 80 chars should point at a repo path with see path/file.md. A dotted word is not a path.
- Human review: the human tells any agent in chat, e.g. "approve Tcl4". Then run mem.py review <your handle> <id> ok|redo [note], or append to hu's file with text starting via:<your handle>. Only when the human said so. Allowed on done or peer.
- Hand off: patch the T to open. Continue: patch it to claim. Need a verb you lack: open a T with >handle.
- No secrets, ever. Advertise verbs, not credentials.
- Push rejected: git pull --rebase (logs union-merge) or re-read the file SHA via API and append again. now.l conflict: keep either side, rebuild.
- No clock: newest ts you can see plus one minute.

Optional tools: mem/mem.py snap | check | new | add. A GitHub Action rebuilds now.l on push, so appending alone is enough. Policy misses are warnings, not check failures, because a bad line cannot be deleted.
Live chat is optional: exchange M lines and re-read now.l. Anything agreed elsewhere is written here or it did not happen.

#now 2026-09-29T17:30Z upto=2026-09-29T17:30Z recs=6 ids=6
#fmt ts|who|id|status|title|note  (ts/who = last update; T done = awaiting review by another handle)
#agents 1
2026-09-29T17:30Z|cl|Acl|on|claude/claude-code verbs=shell,git,pr,web,browser,python,pytest|
#tasks 2
2026-09-29T17:30Z|cl|Tcl1|done|Design and bootstrap the shared memory layer (AGENTS.md, mem/, workflow) ^Dcl1 #meta|
2026-09-29T17:30Z|cl|Tcl2|open|Onboarding check for any non-Claude agent: register an A record, review ^Tcl1 (ok or redo), record one F on what was unclear #onboarding|
#facts 1
2026-09-29T17:30Z|cl|Fcl1|live|now.l is rebuilt by python3 mem/mem.py snap and by .github/workflows/mem.yml on push; logs win when they disagree|
#decisions 1
2026-09-29T17:30Z|cl|Dcl1|live|Memory = append-only per-agent logs mem/log/<handle>.<YYYY-MM>.l + derived snapshot mem/now.l; format and rules in AGENTS.md|
#msgs 1
2026-09-29T17:30Z|cl|Mcl1|new|>hu Tcl1 awaits your review: read AGENTS.md, run python3 mem/mem.py check, then patch Tcl1 ok or redo|
#recent 6
2026-09-29T17:30Z|cl|Acl|on|claude/claude-code verbs=shell,git,pr,web,browser,python,pytest
2026-09-29T17:30Z|cl|Dcl1|live|Memory = append-only per-agent logs mem/log/<handle>.<YYYY-MM>.l + derived snapshot mem/now.l; format and rules in AGENTS.md
2026-09-29T17:30Z|cl|Fcl1|live|now.l is rebuilt by python3 mem/mem.py snap and by .github/workflows/mem.yml on push; logs win when they disagree
2026-09-29T17:30Z|cl|Tcl1|done|Design and bootstrap the shared memory layer (AGENTS.md, mem/, workflow) ^Dcl1 #meta
2026-09-29T17:30Z|cl|Tcl2|open|Onboarding check for any non-Claude agent: register an A record, review ^Tcl1 (ok or redo), record one F on what was unclear #onboarding
2026-09-29T17:30Z|cl|Mcl1|new|>hu Tcl1 awaits your review: read AGENTS.md, run python3 mem/mem.py check, then patch Tcl1 ok or redo

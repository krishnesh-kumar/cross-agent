260929.1730|cl|Acl|on|claude/claude-code verbs=shell,git,pr,web,browser,python,pytest
260929.1730|cl|Dcl1|live|Memory = append-only per-agent logs mem/log/<handle>.<YYYY-MM>.l + derived snapshot mem/now.l; format and rules in AGENTS.md
260929.1730|cl|Fcl1|live|now.l is rebuilt by python3 mem/mem.py snap and by .github/workflows/mem.yml on push; logs win when they disagree
260929.1730|cl|Tcl1|done|Design and bootstrap the shared memory layer (AGENTS.md, mem/, workflow) ^Dcl1 #meta
260929.1730|cl|Tcl2|open|Onboarding check for any non-Claude agent: register an A record, review ^Tcl1 (ok or redo), record one F on what was unclear #onboarding
260929.1730|cl|Mcl1|new|>hu Tcl1 awaits your review: read AGENTS.md, run python3 mem/mem.py check, then patch Tcl1 ok or redo

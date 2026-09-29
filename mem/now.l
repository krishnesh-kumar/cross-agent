#now upto=260929.1907 recs=13 ids=11 rest=0
#k ts|who|id|status|title|note  ts=YYMMDD.HHMM utc, who=last actor, id=KIND+handle+n, K: A agent T task F fact D decision M message, T done=awaiting review by another handle, rules AGENTS.md
#agents 2
260929.1907|hu|Ahu|on|human owner verbs=review,merge,deploy,secrets via:cl|
260929.1730|cl|Acl|on|claude/claude-code verbs=shell,git,pr,web,browser,python,pytest|
#tasks 2
260929.1907|cl|Tcl3|done|Comment-driven human approvals: relay cmd, humans.l, ci_commit.sh, workflow, tests ^Dcl2 #meta|
260929.1730|cl|Tcl2|open|Onboarding check for any non-Claude agent: register an A record, review ^Tcl1 (ok or redo), record one F on what was unclear #onboarding|
#facts 2
260929.1907|cl|Fcl2|live|An agent holding the human's GitHub token can post /ok as them. Give agents own identities; list only humans in humans.l|
260929.1730|cl|Fcl1|live|now.l is rebuilt by python3 mem/mem.py snap and by .github/workflows/mem.yml on push; logs win when they disagree|
#decisions 2
260929.1907|cl|Dcl2|live|Human decisions = /ok /redo /register comments; Action checks login in mem/humans.l and records them as hu via:gh#id|
260929.1730|cl|Dcl1|live|Memory = append-only per-agent logs mem/log/<handle>.<YYYY-MM>.l + derived snapshot mem/now.l; format and rules in AGENTS.md|
#msgs 1
260929.1907|cl|Mcl2|new|>hu Tcl3 awaits review: comment /ok Tcl3 on any issue or PR; also try /register to test the Action route|

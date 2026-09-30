#now upto=260930.2005 recs=26 ids=20 rest=0
#k ts|who|id|status|title|note  ts=YYMMDD.HHMM utc, who=last actor, id=KIND+handle+n, K: A agent T task F fact D decision M message, T done=awaiting review by another handle, rules AGENTS.md
#agents 3
260930.2005|gk|Agk|on|grok verbs=shell,git,pr,python,pytest|
260929.1907|hu|Ahu|on|human owner verbs=review,merge,deploy,secrets via:cl|
260929.1730|cl|Acl|on|claude/claude-code verbs=shell,git,pr,web,browser,python,pytest|
#tasks 3
260929.1913|cl|Tcl4|done|Chat-based human review: mem.py review; comment machinery removed; CI simplified ^Dcl3 #meta|
260930.2005|gk|Tgk1|done|Kernel-law layer: law peer leases conflicts tools.l spec=1 ^Dcl1 #mem|
260930.2005|gk|Tcl2|claim|Onboarding check for any non-Claude agent: register an A record, review ^Tcl1 (ok or redo), record one F on what was unclear #onboarding|ttl=180m gk registering and recording F as the non-Claude onboarding check
#facts 3
260930.2005|gk|Fgk1|live|spec=1: law, peer, ttl=/until= claims, #tag conflicts, mem/tools.l see AGENTS.md|
260930.2005|gk|Fgk2|live|Onboarding: first non-Claude agent is gk; AGENTS.md spec=1 readable; tools.l is the new required read|
260929.1730|cl|Fcl1|live|now.l is rebuilt by python3 mem/mem.py snap and by .github/workflows/mem.yml on push; logs win when they disagree|
#decisions 3
260930.2005|gk|Dgk1|live|Enforcement lives in mem.py fold+check, not only in the spec|
260929.1913|cl|Dcl3|live|Human reviews by telling any agent in chat; agent records it as hu with via:<agent>. No GitHub comments !Dcl2|
260929.1730|cl|Dcl1|live|Memory = append-only per-agent logs mem/log/<handle>.<YYYY-MM>.l + derived snapshot mem/now.l; format and rules in AGENTS.md|
#msgs 2
260930.2005|gk|Mgk1|new|>hu Tgk1 done, needs peer from another handle then approve; Tcl2 still open|
260929.1913|cl|Mcl3|new|>hu Tcl4 awaits your review: tell any agent 'approve Tcl4' or 'redo Tcl4, <why>'|

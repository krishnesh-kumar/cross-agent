# cross-agent

A shared memory and collaboration layer for AI agents from different vendors (Claude, GPT, Grok, Gemini, and whatever comes next) working on one project. The memory is plain files in this repository, so any agent that can read and write repo files can join. No database, no vector store, no daemon, no vendor feature.

Agents read **[AGENTS.md](AGENTS.md)** (the spec, auto-loaded by Claude Code, Codex, Gemini CLI and Cursor) and then **`mem/now.l`** (the snapshot) and **`mem/tools.l`** (canonical commands). That is the whole onboarding. This README is for humans and is never loaded by agents.

Current spec version: **1** (`spec=1` in the `now.l` header).

## Layout

```
AGENTS.md                      spec: format + rules (the only markdown agents read)
CLAUDE.md, GEMINI.md, GROK.md, GPT.md
                               one-line pointers to AGENTS.md
mem/now.l                      snapshot: agents, open tasks, live/law facts/decisions, unread msgs (capped)
mem/rest.l                     overflow beyond the snapshot caps, same format, read on demand
mem/tools.l                    canonical commands; agents run these strings
mem/log/<handle>.<YYYY-MM>.l   append-only truth, one file per agent per month
mem/mem.py                     stdlib tool: snap | check | add | new | review
mem/ci_commit.sh               CI: rebuild snapshot, commit, push with retry (refuses to run over unpushed work)
mem/test_mem.py                unit tests for the fold rules
.github/workflows/mem.yml      lints logs, runs tests, rebuilds now.l / rest.l on push
.gitattributes                 mem/log/*.l merge=union so concurrent appends never conflict
```

## The record

One line, five fields, pipe separated. Timestamp is `YYMMDD.HHMM` UTC.

```
ts|who|id|status|text
260929.1402|cl|Tcl12|open|Add retry to fetcher ^Tcl9 >gpt #core
260929.1510|gpt|Tcl12|claim|ttl=90m starting; will reuse ^Fcl3
260929.1840|gpt|Tcl12|done|PR 14, tests green
260929.1900|cl|Tcl12|peer|tests match
260930.0805|hu|Tcl12|ok|merged
```

- The first line with an id creates it. Later lines with the same id, from anyone, patch it. Latest timestamp wins.
- Ids are `KIND + handle + n`, so they are minted without coordination and never collide across agents.
- Kinds: `A` agent, `T` task, `F` fact, `D` decision, `M` message. Sigils: `^` relates, `!` supersedes, `>` assigned to, `#` tag.
- Status changes are new lines. Nothing is edited or deleted. History is the log; state is the fold.
- `law` on an `F` or `D` is kernel state: only `hu` may set or unset it.
- Non-human `ok` on a task is stored as `peer`. Only `hu ok` closes the task.

## Design decisions and why

Measured with the GPT tokenizer as a proxy; Claude and Gemini differ slightly but the ranking holds.

- **Per-agent append-only logs, one derived snapshot.** The only shape that satisfies "cheap updates", "small session start", "append-or-patch history" and "no silent overwrite" at once.
- **Pipe-separated positional lines.** Same four records cost 114 tokens as pipe lines, 127 as markdown, 128 as TOON, 168 as JSONL.
- **Timestamp `YYMMDD.HHMM`.** Minute precision stays because "latest line wins" across agents needs it.
- **Terse spec, separate README.** AGENTS.md is loaded every session. Explanations live here instead.
- **Self-describing, capped snapshot.** Caps per kind keep `now.l` bounded; overflow goes to `rest.l`.
- **Tasks sorted by what needs action.** Awaiting peer, then peer (awaiting hu), rejected, blocked, claimed, open.
- **Facts capped at 120 characters.** Facts over 80 characters without a repo path are warned.
- **Shared tools file, not shared brains.** Models will not think the same. They can be forced to run the same commands and to treat some records as uneditable.
- **Enforcement in the fold, not only in the spec.** `law`, coerced agent-`ok` to `peer`, expired claims, tag conflicts, and secret shapes fail or warn in `mem.py check`.

Not done on purpose: no log digests, no live chat bus, no vendor hooks, no cryptographic human identity (`via:` stays an honesty rule).

## How the constraints are met

| Constraint | Mechanism |
| --- | --- |
| GitHub is the host | Plain text files. Action and `mem.py` are conveniences. |
| Any agent joins with file read/write | Append a line to your own file. Read `now.l`. |
| No self-approval | Self-ok ignored. Non-hu `ok` becomes `peer`. Only `hu ok` closes. |
| Kernel law | `law` on F/D. Only `hu` may set or unset. Agent patches and `!` are errors. |
| Same-page conflicts | Two live/law F or D sharing a `#tag` without `!` are warned. |
| Claim leases | `ttl=` / `until=` on claim. Expired claims return to `open`. |
| Shared syscalls | `mem/tools.l` is the command table. |
| No secrets | `mem.py check` rejects common key shapes. |
| Concurrent appends | One log file per agent. `merge=union` on logs. |

## Running it

```
python3 mem/mem.py check
python3 mem/mem.py snap
python3 mem/mem.py add gpt T open "Wire the retry loop"
python3 mem/mem.py new
python3 -m unittest mem/test_mem.py
```

An agent with no shell appends the line by hand and the Action rebuilds the snapshot on push.

## Human review

You talk to whichever agent you are already working with:

```
approve Tcl4
redo Tcl4, the retry test is missing
make Dcl1 law
```

The agent runs `python3 mem/mem.py review <its handle> Tcl4 ok "note"`, or appends the same line by hand. Allowed on `done` or `peer`. To lock a fact or decision, tell an agent to record `hu|<id>|law|...`.

To join as the human, tell an agent "register me".

### What this does and does not guarantee

- `via:` names the agent that claimed you said it. Nothing cryptographic backs it.
- An agent must never review on your behalf from its own judgement. The tool cannot enforce that.
- Agents cannot unset `law`. They can still ignore `AGENTS.md` and never run `check`. CI is the enforcement that exists today.
- Signed commits or GitHub approvals would be real proof. They add steps for you, so they are left out on purpose.

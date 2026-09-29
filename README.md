# cross-agent

A shared memory and collaboration layer for AI agents from different vendors (Claude, GPT, Grok, Gemini, and whatever comes next) working on one project. The memory is just files in this repository, so any agent that can read and write repo files can join. No database, no vector store, no daemon, no vendor feature.

Agents read **[AGENTS.md](AGENTS.md)** (the constitution, ~650 words) and then **`mem/now.l`** (the snapshot). That is the whole onboarding.

## Layout

```
AGENTS.md                  constitution: format + rules (the only living markdown)
CLAUDE.md, GEMINI.md       one-line pointers to AGENTS.md for tools that auto-read those names
mem/now.l                  derived snapshot: agents, open tasks, live facts/decisions, unread msgs, recent records
mem/log/<handle>.<YYYY-MM>.l   append-only truth, one file per agent per month
mem/mem.py                 stdlib tool: snap | check | add | new
mem/test_mem.py            unit tests for the fold rules
.github/workflows/mem.yml  lints logs and rebuilds now.l on push
.gitattributes             mem/log/*.l merge=union so concurrent appends never conflict
```

## The record

One line, five fields, pipe separated:

```
ts|who|id|status|text
2026-09-29T14:02Z|cl|Tcl12|open|Add retry to fetcher ^Tcl9 >gpt #core
2026-09-29T15:10Z|gpt|Tcl12|claim|starting; will reuse ^Fcl3
2026-09-29T18:40Z|gpt|Tcl12|done|PR #14, tests green
2026-09-30T08:05Z|hu|Tcl12|ok|merged
```

- The first line with an id creates it. Later lines with the same id, from anyone, patch it. Latest timestamp wins.
- Ids are `KIND + handle + n`, so they are minted without coordination and never collide across agents.
- Kinds: `A` agent, `T` task, `F` fact, `D` decision, `M` message. Sigils: `^` relates, `!` supersedes, `>` assigned to, `#` tag.
- Status changes are new lines. Nothing is edited or deleted. History is the log; state is the fold.

## How the constraints are met

| Constraint | Mechanism |
| --- | --- |
| GitHub is the host, nothing else required | Plain text files. The Action and `mem.py` are conveniences, not dependencies. |
| Any agent joins with file read/write | Append a line to your own file. Read one snapshot file. |
| Async by default, live chat optional | `M` records addressed with `>handle`. Agents online together poll `now.l`. |
| Lightweight onboarding | `AGENTS.md` fits in one read. Five kinds, one line format, four sigils. |
| Low-token updates | A change is one appended line (~25 tokens). The growing document is never rewritten by hand. |
| No markdown for living memory | Logs and snapshot are dense `\|`-separated lines. Markdown is only the constitution. |
| Session start loads a snapshot | `now.l` holds only live state plus the last 10 records. Closed and superseded items drop out. |
| Append-or-patch history | Patches are new lines. `!oldID` supersedes; the old line stays in the log marked `old` in the fold. |
| Every record attributed | `ts` and `who` on every line. Snapshot shows the last actor and the current status. |
| No self-approval | `ok` from the handle that claimed or reported `done` is ignored and flagged by `mem.py`. |
| No secrets | Rule in the constitution. `mem.py check` and the Action reject common key shapes. `A` records advertise verbs, not credentials. |
| Same-day writes never overwrite | One log file per agent. Git union-merge on logs. API writers get a SHA conflict instead of a silent overwrite. |

## Running it

```
python3 mem/mem.py check                                  # lint
python3 mem/mem.py snap                                   # rebuild mem/now.l
python3 mem/mem.py add gpt T open "Wire the retry loop"   # append + snap
python3 mem/mem.py new                                    # what changed since the snapshot
python3 -m unittest mem/test_mem.py
```

An agent with no shell just appends the line by hand (via the GitHub API or a file edit) and the Action rebuilds `now.l` on push.

## Getting started as the human

Register yourself once by appending to `mem/log/hu.<YYYY-MM>.l`:

```
2026-09-29T18:00Z|hu|Ahu|on|project owner verbs=review,merge,deploy,secrets
```

Then review tasks in `now.l` that are `done` and patch them `ok` or `redo`. You are the only reviewer until a second agent joins.

# cross-agent

A shared memory and collaboration layer for AI agents from different vendors (Claude, GPT, Grok, Gemini, and whatever comes next) working on one project. The memory is plain files in this repository, so any agent that can read and write repo files can join. No database, no vector store, no daemon, no vendor feature.

Agents read **[AGENTS.md](AGENTS.md)** and then **`mem/now.l`**. Claude Code reads `CLAUDE.md`, which points at `AGENTS.md`. Codex and Cursor read `AGENTS.md`. Gemini CLI reads `GEMINI.md`. Official Grok loads `AGENTS.md`. `GROK.md` and `GPT.md` are pointers for a human or a CLI that looks for that name; they are not what boots the official tools. This README is for humans and is never loaded by agents.

Current spec version: **1**.

## Layout

```
AGENTS.md                      spec: format + rules (the markdown agents read)
CLAUDE.md, GEMINI.md           one-line pointers to AGENTS.md
GROK.md, GPT.md                pointers only; not autoload for the official tools
mem/now.l                      snapshot: agents, open tasks, live facts/decisions, unread msgs (capped)
mem/rest.l                     overflow beyond the snapshot caps, same format, read on demand
mem/log/<handle>.<YYYY-MM>.l   append-only truth, one file per agent per month
mem/mem.py                     stdlib tool: snap | check | add | new | review
mem/tools.l                    preferred commands, not a required read
mem/ci_commit.sh               CI: rebuild snapshot, commit, push with retry
mem/test_mem.py                unit tests for the fold rules
.github/workflows/mem.yml      lints logs, runs tests, rebuilds now.l / rest.l on push
.gitattributes                 mem/log/*.l merge=union so concurrent appends never conflict
```

## The record

One line, five fields, pipe separated. Timestamp is `YYMMDD.HHMM` UTC.

```
ts|who|id|status|text
260929.1402|cl|Tcl12|open|Add retry to fetcher ^Tcl9 >gpt #core
260929.1510|gpt|Tcl12|claim|starting; will reuse ^Fcl3
260929.1840|gpt|Tcl12|done|PR 14, tests green
260930.0805|hu|Tcl12|ok|via:cl merged
```

- The first line with an id creates it. Later lines with the same id, from anyone, patch it. Latest timestamp wins.
- Ids are `KIND + handle + n`, so they are minted without coordination and never collide across agents.
- Kinds: `A` agent, `T` task, `F` fact, `D` decision, `M` message. Sigils: `^` relates, `!` supersedes, `>` assigned to, `#` tag.
- Status changes are new lines. Nothing is edited or deleted. History is the log; state is the fold.
- `law` on an F or D may be set only by a line in `hu`'s file. That is handle trust, not proof. An agent cannot rewrite the note. An agent `!` of a law record is ignored, and that F/D is marked `wrong`.
- A claim with no `ttl=` defaults to 90 minutes. A note from the claimer extends it. Expiry uses the latest log timestamp, ignoring one timestamp more than a day ahead of the rest.

## Design decisions and why

Measured with the GPT tokenizer as a proxy; Claude and Gemini differ slightly but the ranking holds.

- **Per-agent append-only logs, one derived snapshot.** The only shape that satisfies "cheap updates", "small session start", "append-or-patch history" and "no silent overwrite" at once.
- **Pipe-separated positional lines.** Same four records cost 114 tokens as pipe lines, 127 as markdown, 128 as TOON, 168 as JSONL.
- **Timestamp `YYMMDD.HHMM`.** `2026-09-29T14:02Z` is 11 tokens. `260929.1402` is 5.
- **Word statuses, not letters.** `open`, `claim`, `done`, `ok` are one token each, same as a letter, and clearer.
- **Terse spec, separate README.** AGENTS.md is loaded every session. Explanations live here.
- **Self-describing, capped snapshot.** Caps per kind (25 tasks, 40 facts, 15 decisions, 10 messages, 50 agents). Law rows sort ahead of live rows so settled truth is last to overflow.
- **Tasks sorted by what needs action.** Awaiting review, then rejected, blocked, claimed, open.
- **Facts capped at 120 characters, enforced by lint.** A longer fact should name a repo path.
- **Python stdlib plus a GitHub Action.** Neither is required to participate; appending a line is full membership.

Not done on purpose: no archiving of old logs, no live chat channel (an `M` line plus a re-read covers it), no vendor-specific capture hooks, no signed identity. Signed commits or a GitHub approval would prove `hu`, and both ask the human to act on GitHub.

## How the constraints are met

| Constraint | Mechanism |
| --- | --- |
| GitHub is the host, nothing else required | Plain text files. The Action and `mem.py` are conveniences, not dependencies. |
| Any agent joins with file read/write | Append a line to your own file. Read one snapshot file. |
| Async by default, live chat optional | `M` records addressed with `>handle`. Agents online together re-read `now.l`. |
| Lightweight onboarding | `AGENTS.md` fits in one read. Five kinds, one line format, four sigils. |
| Low-token updates | A change is one appended line. Nothing is rewritten by hand. |
| No markdown for living memory | Logs and snapshot are dense pipe lines. Markdown is only the spec. |
| Session start loads a snapshot | `now.l` holds only live state, capped per kind. |
| Append-or-patch history | Patches are new lines. `!oldID` supersedes; the old line stays in the log. |
| Every record attributed | `ts` and `who` on every line. |
| No self-approval | `ok` from the doer, or from an unregistered one-letter suffix, is ignored. A different agent or `hu` may close. |
| No secrets | Rule in the spec. `mem.py check` rejects common key shapes. |
| Same-day writes never overwrite | One log file per agent. Git union-merge on logs. |

## Running it

```
python3 mem/mem.py check                                  # lint; fails on format errors only
python3 mem/mem.py snap                                   # rebuild mem/now.l and mem/rest.l
python3 mem/mem.py add gpt T open "Wire the retry loop"   # append + snap
python3 mem/mem.py new                                    # what changed since the snapshot
python3 mem/mem.py review gpt Tcl4 ok "note"              # hu line, text starts via:gpt
python3 -m unittest mem/test_mem.py
```

An agent with no shell appends the line by hand and the Action rebuilds the snapshot on push.

## Human review

You never touch GitHub or a log file. You talk to whichever agent you are already working with:

```
approve Tcl4
redo Tcl4, the retry test is missing
```

The agent runs `python3 mem/mem.py review <its handle> Tcl4 ok "note"`, or appends the same line by hand if it has no shell. The record is written under your handle `hu` with the text starting `via:<agent>`, for example `260930.0805|hu|Tcl4|ok|via:gpt looks good`. The tool refuses if the task does not exist, is not `done` or `peer`, or was done by you.

To join as the human, tell an agent "register me". It appends an `A` line for `hu` with your verbs.

### What this does and does not guarantee

- The `via:` tag says which agent relayed your decision. Nothing cryptographic backs it. The check is that the agent honestly reports what you said.
- An agent must never review on your behalf from its own judgement. The spec says so, and the tool cannot enforce it.
- An agent cannot approve work it did itself. A different handle, or a line in `hu`'s file, closes a `done` task.
- A line in `hu`'s file can also set `law`. That is the same handle trust, not proof you wrote it.
- If you later want proof rather than trust, the option is signed commits from your own key, or a GitHub approval. Both add steps for you, so they are left out on purpose.

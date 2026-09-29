# cross-agent

A shared memory and collaboration layer for AI agents from different vendors (Claude, GPT, Grok, Gemini, and whatever comes next) working on one project. The memory is plain files in this repository, so any agent that can read and write repo files can join. No database, no vector store, no daemon, no vendor feature.

Agents read **[AGENTS.md](AGENTS.md)** (the spec, ~600 tokens, auto-loaded by Claude Code, Codex, Gemini CLI and Cursor) and then **`mem/now.l`** (the snapshot). That is the whole onboarding. This README is for humans and is never loaded by agents.

## Layout

```
AGENTS.md                      spec: format + rules (the only markdown agents read)
CLAUDE.md, GEMINI.md           one-line pointers to AGENTS.md
mem/now.l                      snapshot: agents, open tasks, live facts/decisions, unread msgs (capped)
mem/rest.l                     overflow beyond the snapshot caps, same format, read on demand
mem/log/<handle>.<YYYY-MM>.l   append-only truth, one file per agent per month
mem/mem.py                     stdlib tool: snap | check | add | new | relay
mem/humans.l                   github-login|handle: whose /ok /redo /register comments count as human
mem/ci_commit.sh               CI: relay comment, rebuild snapshot, commit, push with retry
mem/test_mem.py                unit tests for the fold rules
.github/workflows/mem.yml      lints logs and rebuilds now.l / rest.l on push
.gitattributes                 mem/log/*.l merge=union so concurrent appends never conflict
```

## The record

One line, five fields, pipe separated. Timestamp is `YYMMDD.HHMM` UTC.

```
ts|who|id|status|text
260929.1402|cl|Tcl12|open|Add retry to fetcher ^Tcl9 >gpt #core
260929.1510|gpt|Tcl12|claim|starting; will reuse ^Fcl3
260929.1840|gpt|Tcl12|done|PR 14, tests green
260930.0805|hu|Tcl12|ok|merged
```

- The first line with an id creates it. Later lines with the same id, from anyone, patch it. Latest timestamp wins.
- Ids are `KIND + handle + n`, so they are minted without coordination and never collide across agents.
- Kinds: `A` agent, `T` task, `F` fact, `D` decision, `M` message. Sigils: `^` relates, `!` supersedes, `>` assigned to, `#` tag.
- Status changes are new lines. Nothing is edited or deleted. History is the log; state is the fold.

## Design decisions and why

Measured with the GPT tokenizer as a proxy; Claude and Gemini differ slightly but the ranking holds.

- **Per-agent append-only logs, one derived snapshot.** The only shape that satisfies "cheap updates", "small session start", "append-or-patch history" and "no silent overwrite" at once. Alternatives fail one each: markdown memory files get rewritten per change, a single shared log conflicts on concurrent pushes, git-backed trackers like Beads need a binary installed.
- **Pipe-separated positional lines.** Same four records cost 114 tokens as pipe lines, 127 as markdown, 128 as TOON, 168 as JSONL. Keys and headers are pure overhead when every record has the same five fields.
- **Timestamp `YYMMDD.HHMM`.** `2026-09-29T14:02Z` is 11 tokens, a third of a typical line. `260929.1402` is 5. Keeping the two-digit year costs nothing extra and keeps lines safe to copy across years. Minute precision stays because "latest line wins" across agents needs it.
- **Word statuses, not letters.** `open`, `claim`, `done`, `ok` are one token each, same as `o`, `c`, `d`, `k`. Letters save nothing and cost clarity.
- **Terse spec, separate README.** AGENTS.md is loaded every session and sits at the start of context unchanged, which is what prompt caching rewards. Explanations live here instead.
- **Self-describing, capped snapshot.** Line two of `now.l` is the field key, so an agent that reads only that file can parse it. Caps per kind (25 tasks, 40 facts, 15 decisions, 10 messages, 50 agents) keep it bounded; overflow goes to `rest.l`. Fixed caps rather than a token budget because predictable is easier for a model to reason about.
- **Tasks sorted by what needs action.** Awaiting review, then rejected, blocked, claimed, open. Zero extra tokens, just ordering.
- **Facts capped at 120 characters, enforced by lint.** Facts are the part of memory that grows forever. A fact that needs more room should be a file in the repo with the fact pointing at its path.
- **Python stdlib plus a GitHub Action.** Python is on every GitHub runner and most machines. The Action means an agent with no shell still gets a fresh snapshot. Neither is required to participate; appending a line is full membership.

Not done on purpose: no archiving of old logs into digests (logs are never read at session start, so size costs nothing until someone investigates history), no live chat channel (an `M` line plus a re-read covers two agents online together), no vendor-specific capture hooks (they would tie the design to each harness).

## How the constraints are met

| Constraint | Mechanism |
| --- | --- |
| GitHub is the host, nothing else required | Plain text files. The Action and `mem.py` are conveniences, not dependencies. |
| Any agent joins with file read/write | Append a line to your own file. Read one snapshot file. |
| Async by default, live chat optional | `M` records addressed with `>handle`. Agents online together re-read `now.l`. |
| Lightweight onboarding | `AGENTS.md` fits in one read. Five kinds, one line format, four sigils. |
| Low-token updates | A change is one appended line, about 20 tokens. Nothing is rewritten by hand. |
| No markdown for living memory | Logs and snapshot are dense pipe lines. Markdown is only the spec. |
| Session start loads a snapshot | `now.l` holds only live state, capped per kind. Closed and superseded items drop out. |
| Append-or-patch history | Patches are new lines. `!oldID` supersedes; the old line stays in the log, marked `old` in the fold. |
| Every record attributed | `ts` and `who` on every line. Snapshot shows the last actor and the current status. |
| No self-approval | `ok` from the handle that claimed or reported `done` is ignored and flagged by `mem.py`. Human approvals come from `/ok` comments checked against `mem/humans.l` (see trust boundary). |
| No secrets | Rule in the spec. `mem.py check` and the Action reject common key shapes. `A` records advertise verbs, not credentials. |
| Same-day writes never overwrite | One log file per agent. Git union-merge on logs. API writers get a SHA conflict instead of a silent overwrite. |

## Running it

```
python3 mem/mem.py check                                  # lint
python3 mem/mem.py snap                                   # rebuild mem/now.l and mem/rest.l
python3 mem/mem.py add gpt T open "Wire the retry loop"   # append + snap
python3 mem/mem.py new                                    # what changed since the snapshot
python3 -m unittest mem/test_mem.py
```

An agent with no shell appends the line by hand (via the GitHub API or a file edit) and the Action rebuilds the snapshot on push.

## Human decisions

You never edit a log file. Comment on any issue or pull request in the repo:

```
/ok Tcl1 looks good
/redo Tcl2 tests are missing
/register review merge deploy
```

The Action (`.github/workflows/mem.yml`, script `mem/ci_commit.sh`) reads the comment, checks the commenter's GitHub login against `mem/humans.l`, appends a line under your handle with the text `via:gh#<comment id>` so the source comment is traceable, rebuilds the snapshot, and pushes. It reacts with a thumbs-up, or a confused face plus a reply explaining why it refused. Refusals: unlisted login, unknown task, task not in `done`, or you approving work you did yourself. Re-running a comment is harmless.

Approvals relayed by an agent from a chat message are the fallback. The agent writes them into `hu`'s file with text starting `via:<agent handle>`, so they are distinguishable from Action-verified ones.

### Trust boundary, stated plainly

- The Action trusts two things: the GitHub login on the comment, and `mem/humans.l`. Anyone with write access to the repo can edit that file, so repo write access is the root of trust.
- GitHub cannot tell you apart from an agent that holds your token. If an agent pushes or comments using your personal access token or your logged-in session, it can post `/ok` as you. The no-self-approval rule then rests on the agent behaving, not on the system.
- To make it hold, give each agent its own GitHub identity (a machine user or a GitHub App) and list only human logins in `humans.l`. Until then, treat the Action route as convenient and honest about who clicked, not as proof against a misbehaving agent.
- The workflow reads comment text only through environment variables and never checks out pull request code, so a comment cannot inject shell or run untrusted code.

To join as the human: comment `/register` once, then `/ok` or `/redo` on tasks that show `done` in `now.l`. Comment workflows run from the default branch, so `mem.yml` must be there.

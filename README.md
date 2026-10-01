# cross-agent

A shared memory and collaboration layer for AI agents from different vendors working on one project. The memory is plain files in this repository. No database, no vector store, no daemon, no vendor feature.

Claude Code reads `CLAUDE.md`, which points at `AGENTS.md`. Codex and Cursor read `AGENTS.md`. Gemini CLI reads `GEMINI.md`. Official Grok loads `AGENTS.md`. `GROK.md` and `GPT.md` are pointers only; they are not autoload files. Then read `mem/now.l`. This README is for humans.

Current spec version: **1**.

## Review rule

After `done`, a different handle may `ok` (closes) or `peer`. The doer cannot, including a suffixed handle (`cl` / `clb`). `hu` may also close. `ok` before `done` is ignored. This is the original constraint: a different agent or the human reviews. It is not "only the human closes".

## Law

A line in `hu`'s file may set `law`. That is handle trust, not proof the human wrote it. An agent cannot change the note or status of a law record. An agent `!` of a law record is ignored and that new record is marked `wrong`.

## Leases and conflicts

A claim with no `ttl=` defaults to 90 minutes. Expiry is judged against the latest log timestamp, so the same logs always snap the same way. A takeover after expiry is not a double claim. Conflict warnings are for two live **decisions** that share a `#tag`, not for facts that share a tag.

Policy misses are warnings. `check` fails only on format errors, because a bad line cannot be deleted from an append-only log.

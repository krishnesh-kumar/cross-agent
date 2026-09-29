#!/usr/bin/env bash
# CI helper. On a comment event, relay the human's decision. Then rebuild the snapshot, commit, and push with retry.
# Env: GITHUB_REF_NAME, GITHUB_EVENT_NAME. Comment events also: LOGIN REF BODY, and optionally GH_TOKEN GITHUB_REPOSITORY NUMBER.
set -u
branch="${GITHUB_REF_NAME:?GITHUB_REF_NAME required}"
out=""

apply() {
  if [ "${GITHUB_EVENT_NAME:-}" = issue_comment ]; then
    out=$(python3 mem/mem.py relay) || return 1
    printf '%s\n' "$out"
  fi
  python3 mem/mem.py snap >/dev/null || return 1
  git add mem
}

say() {  # say <reaction> <comment text or empty>
  command -v gh >/dev/null 2>&1 && [ -n "${GH_TOKEN:-}" ] && [ -n "${REF:-}" ] || return 0
  gh api -X POST "repos/${GITHUB_REPOSITORY}/issues/comments/${REF}/reactions" -f content="$1" >/dev/null 2>&1 || true
  if [ -n "${2:-}" ] && [ -n "${NUMBER:-}" ]; then
    gh issue comment "$NUMBER" --repo "$GITHUB_REPOSITORY" --body "$2" >/dev/null 2>&1 || true
  fi
}

git config user.name "mem-bot"
git config user.email "mem-bot@users.noreply.github.com"
apply || exit 1
pushed=0
for _ in 1 2 3; do
  if git diff --cached --quiet; then pushed=1; break; fi
  if [ -n "$out" ]; then msg="mem: relay human decision"; else msg="mem: rebuild snapshot"; fi
  git commit -q -m "$msg [skip ci]"
  if git push -q origin "HEAD:$branch"; then pushed=1; break; fi
  git fetch -q origin "$branch" && git reset -q --hard "origin/$branch" || exit 1
  apply || exit 1
done
[ "$pushed" = 1 ] || { echo "push failed after retries" >&2; exit 1; }

if [ "${GITHUB_EVENT_NAME:-}" = issue_comment ] && [ -n "$out" ]; then
  if printf '%s\n' "$out" | grep -q '^rejected'; then
    say confused "$(printf '%s\n' "$out" | grep '^rejected')"
  else
    say '+1' ""
  fi
fi
exit 0

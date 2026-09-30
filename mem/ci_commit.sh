#!/usr/bin/env bash
# CI helper: rebuild the snapshot, commit it if it changed, push with retry when the branch moved.
# Env: GITHUB_REF_NAME (branch to push to).
set -u
branch="${GITHUB_REF_NAME:?GITHUB_REF_NAME required}"
# This script hard-resets to the remote when a push is rejected, so it must never run over unpushed work.
git fetch -q origin "$branch" || exit 1
if [ "$(git rev-list --count "origin/$branch..HEAD")" != 0 ]; then
  echo "refusing: local commits not on origin/$branch would be lost. This script is for CI." >&2
  exit 1
fi
git config user.name "mem-bot"
git config user.email "mem-bot@users.noreply.github.com"
for _ in 1 2 3; do
  python3 mem/mem.py snap >/dev/null && git add mem || exit 1
  git diff --cached --quiet && exit 0
  git commit -q -m "mem: rebuild snapshot [skip ci]"
  git push -q origin "HEAD:$branch" && exit 0
  git fetch -q origin "$branch" && git reset -q --hard "origin/$branch" || exit 1
done
echo "push failed after retries" >&2
exit 1

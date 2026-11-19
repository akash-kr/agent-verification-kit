#!/usr/bin/env bash
# Install agent-verification-kit into a git repo. Never overwrites a file that exists; prints what it kept.
# Usage: scripts/install.sh [repo-dir] [--github]   (default: the current directory)
set -euo pipefail
kit="$(cd "$(dirname "$0")/.." && pwd)"
repo="."
github=0
for arg in "$@"; do
  case "$arg" in
    --github) github=1 ;;
    *) repo="$arg" ;;
  esac
done
repo="$(git -C "$repo" rev-parse --show-toplevel)"
cd "$repo"
python3 -c 'import sys; sys.exit(sys.version_info < (3, 12))' || { echo "agent-verification-kit needs python3 3.12 or newer on PATH (the hooks call python3)." >&2; exit 1; }

put() {  # put <source> <dest>: copy unless dest exists
  if [ -e "$2" ]; then
    echo "kept     $2 (exists)"
  else
    mkdir -p "$(dirname "$2")"
    cp "$1" "$2"
    echo "added    $2"
  fi
}

put "$kit/scripts/agent-check" scripts/agent-check
put "$kit/scripts/review-eval" scripts/review-eval
put "$kit/scripts/diff-check" scripts/diff-check
put "$kit/scripts/evidence" scripts/evidence
put "$kit/templates/classifier.sh" scripts/evidence-classifier
for recipe in "$kit"/templates/ui-recipes/*; do put "$recipe" ".claude/skills/verify/ui/$(basename "$recipe")"; done
put "$kit/templates/agent-check.toml" agent-check.toml
put "$kit/templates/LAWS.md" LAWS.md
put "$kit/templates/VERIFICATION.md" docs/VERIFICATION.md
put "$kit/templates/incident.md" docs/incidents/TEMPLATE.md
put "$kit/templates/verify-skill/SKILL.md" .claude/skills/verify/SKILL.md
put "$kit/templates/verify-skill/check.sh" .claude/skills/verify/check.sh
put "$kit/templates/evals/review/example-bug.toml" evals/review/example-bug.toml.example
put "$kit/templates/evals/review/example-control.toml" evals/review/example-control.toml.example
for hook in pre-commit commit-msg pre-push; do
  put "$kit/templates/githooks/$hook" ".githooks/$hook"
done
if [ "$github" = 1 ]; then
  put "$kit/templates/ci/github-check.yml" .github/workflows/agent-check.yml
  put "$kit/templates/CODEOWNERS" .github/CODEOWNERS
fi
chmod +x scripts/agent-check scripts/review-eval scripts/diff-check scripts/evidence scripts/evidence-classifier .githooks/* .claude/skills/verify/check.sh

current="$(git config core.hooksPath || true)"
existing="$(find .git/hooks -type f ! -name '*.sample' 2>/dev/null | tr '\n' ' ')"
if [ -z "$current" ] && [ -n "$existing" ]; then
  echo "kept     .git/hooks ($existing): setting core.hooksPath would switch these off; call .githooks/* from them instead"
elif [ -z "$current" ]; then
  git config core.hooksPath .githooks
  echo "set      git config core.hooksPath .githooks"
elif [ "$current" != ".githooks" ]; then
  echo "kept     core.hooksPath=$current: call .githooks/* from your hooks, or point it at .githooks"
fi
grep -qx '.test-tmp/' .gitignore 2>/dev/null || { echo '.test-tmp/' >> .gitignore; echo "added    .test-tmp/ to .gitignore"; }

cat <<'NEXT'

Next:
  1. agent-check.toml: set test, one_test and tests for your suite.
  2. .claude/skills/verify/check.sh: start your app and add one step per user flow; then set fresh.
  3. Paste docs/VERIFICATION.md into your AGENTS.md or CLAUDE.md.
  4. Write your first law: scripts/agent-check law "<what must stay true> — held by: <how>"
  5. Gates start in observe; read .git/agent-check-observe.log for a week, then set them to enforce.
NEXT

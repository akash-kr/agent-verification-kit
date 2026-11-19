#!/usr/bin/env bash
# The verify skill's check: the same steps and the same pass/fail on every run.
# Starts the app locally with no real keys, walks the main flows, and on a pass writes the proof
# a push needs (.test-tmp/verify/passed: HEAD, "clean", and a sha256 of each screenshot).
# Usage: .claude/skills/verify/check.sh [port]   Exit 0 = pass.
set -uo pipefail
port="${1:-8790}"
root="$(git rev-parse --show-toplevel)"
base="http://127.0.0.1:$port"
out="$root/.test-tmp/verify"
rm -rf "$out" && mkdir -p "$out"
failures=0
cd "$root"

pass() { echo "PASS  $1"; }
fail() { echo "FAIL  $1"; failures=$((failures + 1)); }
: >"$out/steps.log"
step() { local name="$1"; shift; if "$@" >>"$out/steps.log" 2>&1; then pass "$name"; else fail "$name (see $out/steps.log)"; fi; }

# Something already listening here would be checked instead of this commit's code.
if curl -s -o /dev/null "$base/"; then echo "FAIL  port $port is already in use: stop that server or pass another port"; exit 1; fi

# TODO(you): start the app with no provider keys and a throwaway database, e.g.
#   env -u STRIPE_KEY DATABASE_URL="sqlite:///$out/db.sqlite" ./run-dev.sh "$port" >"$out/server.log" 2>&1 &
server="${!:-}"  # empty until you start the app above
trap 'kill $server 2>/dev/null' EXIT
for _ in $(seq 1 60); do
  [ "$(curl -s -o /dev/null -w '%{http_code}' "$base/")" = 200 ] && break
  sleep 0.5
done

# TODO(you): one step per real user flow. Any command that exits non-zero fails the step.
step "home page loads" curl -sf "$base/"
# step "sign in and see the dashboard" npx playwright test e2e/sign-in.spec.ts
# Screenshots: save each to "$out/<name>.png" (Playwright, agent-browser, a simulator, ...), e.g.
#   npx playwright screenshot --viewport-size=390,844 "$base/" "$out/home-phone.png"
#   npx playwright screenshot --viewport-size=1280,800 "$base/" "$out/home-desktop.png"

# The proof hashes the step log and every screenshot; a repo with no UI proves itself with the log alone.
shopt -s nullglob
shots=("$out"/steps.log "$out"/*.png)
if [ "$failures" -gt 0 ]; then
  echo "RESULT: $failures check(s) failed"
  exit 1
fi
echo "RESULT: all checks passed"
echo "Read these before saying it works (the log, and every screenshot):"
printf '  %s\n' "${shots[@]}"
state=clean
[ -n "$(git status --porcelain)" ] && state=dirty
{ git rev-parse HEAD; echo "$state"; for s in "${shots[@]}"; do echo "$(shasum -a 256 "$s" | cut -d' ' -f1)  $s"; done; } > "$out/passed"

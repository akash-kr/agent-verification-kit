# Shared by the example scripts: a throwaway copy of the demo shop with the real kit installed and pushed once.
# Each script sources this, then plays one change. Nothing outside the throwaway folder is touched.
set -euo pipefail
kit="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
here="$kit/examples"
pause="${DEMO_PAUSE:-0}"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

say()   { printf '\n\033[1;33m▌ %s\033[0m\n' "$*"; sleep "$pause"; }
agent() { printf '\033[1;35m  agent ›\033[0m %s\n' "$*"; sleep "$pause"; }
show()  { printf '\033[2m  $ %s\033[0m\n' "$*"; }
quiet() { "$@" >/dev/null 2>&1; }
indent() { sed 's/^/  /'; }
expect() { printf '\n\033[1;31mexample failed: %s\033[0m\n' "$*" >&2; exit 1; }  # the run did not go the way the example says

# shop <gates...>: the shop in $work/shop, pushed to $work/origin.git, with each named gate on "enforce"
# (the rest off). Gates: fresh laws red_first seals verified evidence guard.
shop() {
  git init -q --bare "$work/origin.git"
  cp -R "$here/shop" "$work/shop"
  cd "$work/shop"
  git init -q -b main
  git config user.name "demo"; git config user.email "demo@example.com"; git config commit.gpgsign false
  git remote add origin "$work/origin.git"
  quiet bash "$kit/scripts/install.sh" .
  {
    echo 'test = "python3 run_tests.py"'
    echo 'one_test = "python3 run_tests.py {file} {name}"'
    echo 'tests = "tests/"'
    echo '[gates]'
    for g in fresh laws red_first seals verified evidence guard; do
      if [[ " $* " == *" $g "* ]]; then echo "$g = \"enforce\""; else echo "$g = \"off\""; fi
    done
    echo '[evidence]'
    echo 'serve = "./run-dev.sh"'
    echo 'high = ["billing/"]'
    echo '[evidence.owes]'
    echo 'medium = "agent"'
    echo 'low = "agent"'
  } > agent-check.toml
  printf '__pycache__/\nevidence/\n.test-tmp/\n' >> .gitignore
  quiet git add -A; quiet git commit -m "shop: cart total" --trailer "Verified: none, first commit"; quiet git push -u origin main
}

# keep <name> <dir>: copy what this example produced into docs/examples/<name>/ for the page and the README.
keep() {
  local out="$kit/docs/examples/$1"
  rm -rf "$out"; mkdir -p "$out"
  cp -R "$2"/. "$out"/
}

# refused <what>: push, and show the refusal. Fails the example if the push went through. Each refusal is
# kept, word for word, in $work/out/refusal-<n>.txt, and what it carried in diff-<n>.txt, for the page.
refused() {
  show "git push"
  if git push -q > "$work/push.txt" 2>&1; then indent < "$work/push.txt"; expect "the push went through, but it should be refused: $1"; fi
  refusals=$((refusals + 1)); mkdir -p "$work/out"
  grep -E "refused:|^- " "$work/push.txt" > "$work/out/refusal-$refusals.txt" || expect "no refusal text for: $1"
  git diff "@{u}..HEAD" > "$work/out/diff-$refusals.txt"   # what the refused push carried
  sed -E $'s/(agent-check refused:)/\033[1;31m\\1\033[0m/' "$work/out/refusal-$refusals.txt" | indent
}
refusals=0

# pushes <what>: push, and fail the example if it was refused.
pushes() {
  show "git push"
  git push -q > "$work/push.txt" 2>&1 || { indent < "$work/push.txt"; expect "the push was refused: $1"; }
  grep -v -E "passed, 0 failed|^$" "$work/push.txt" | indent || true
}

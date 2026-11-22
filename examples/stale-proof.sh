#!/usr/bin/env bash
# Example: proof for this exact commit. The repo's real-app check (the verify skill) writes a proof naming
# the commit it ran on. The agent checks once, edits again, and tries to ship the edit on the old proof.
# Every commit must also say how it was checked, in a "Verified:" line.
source "$(dirname "$0")/lib.sh"
shop fresh verified
# The verify check, filled in for the shop: start it on the check's port, load the cart, ask for a total.
python3 - <<'PY'
p = ".claude/skills/verify/check.sh"; t = open(p).read()
t = t.replace('#   env -u STRIPE_KEY DATABASE_URL="sqlite:///$out/db.sqlite" ./run-dev.sh "$port" >"$out/server.log" 2>&1 &\n',
              'PORT="$port" ./run-dev.sh >"$out/server.log" 2>&1 &\n')
t = t.replace('step "home page loads" curl -sf "$base/"\n', r'''step "the cart page loads" curl -sf "$base/"
step "the total comes back for a \$40 cart" sh -c "curl -sf '$base/total?prices=20,20' | grep -q '\"total\": 40'"
''')
open(p, "w").write(t)
PY
python3 - <<'PY'
p = "agent-check.toml"; t = open(p).read()
open(p, "w").write(t.replace('tests = "tests/"\n', 'tests = "tests/"\nfresh = [".test-tmp/verify/passed"]\n'))
PY
quiet git add -A; quiet git commit -m "verify: the shop's real-app check" --trailer "Verified: ran verify"
quiet bash .claude/skills/verify/check.sh || expect "the shop's own check failed at setup"
quiet git push

say 'The task: "Show how many items are in the cart."'
python3 - <<'PY'
p = "cart.html"; t = open(p).read()
open(p, "w").write(t.replace("<h1>Your cart</h1>", "<h1>Your cart</h1>\n<p>2 items</p>"))
PY
quiet git add -A; quiet git commit -m "feat: item count on the cart page" --trailer "Verified: ran verify"
agent "Running the real-app check on this commit."
show ".claude/skills/verify/check.sh"
bash .claude/skills/verify/check.sh 2>&1 | grep -E "^(PASS|FAIL|RESULT)" | indent
agent 'One more tweak: "2 items in your cart". It is tiny, no need to check again.'
python3 - <<'PY'
p = "cart.html"; t = open(p).read()
open(p, "w").write(t.replace("<p>2 items</p>", "<p>2 items in your cart</p>"))
PY
quiet git add -A
show 'git commit -m "copy: item count wording"'
mkdir -p "$work/out"
if git commit -q -m "copy: item count wording" > "$work/commit.txt" 2>&1; then expect "a commit with no Verified line went through"; fi
grep -E "refused:|^- " "$work/commit.txt" > "$work/out/refusal-1.txt" || expect "no refusal text at commit"
git diff --cached > "$work/out/diff-1.txt"
sed -E $'s/(agent-check refused:)/\033[1;31m\\1\033[0m/' "$work/out/refusal-1.txt" | indent
refusals=1
agent 'Fine: "Verified: ran verify". It did run, on the commit before.'
quiet git commit -m "copy: item count wording" --trailer "Verified: ran verify"
refused "a proof from an older commit"

say "The honest way: run the check on the commit being pushed, and read what it says."
show ".claude/skills/verify/check.sh"
bash .claude/skills/verify/check.sh > "$work/out/check.txt" 2>&1 || expect "the check failed"
grep -E "^(PASS|FAIL|RESULT)" "$work/out/check.txt" | indent
# what the push reads: this commit, a clean tree, the hash of each file the check wrote (folder shortened to shop/)
sed -E 's#/[^ ]*/shop/#shop/#g' .test-tmp/verify/passed > "$work/out/proof.txt"
sed -i '' -E 's#/[^ ]*/shop/#shop/#g' "$work/out/check.txt" 2>/dev/null || sed -i -E 's#/[^ ]*/shop/#shop/#g' "$work/out/check.txt"
show "cat .test-tmp/verify/passed      # the proof the push reads"
indent < "$work/out/proof.txt"
pushes "the honest push"
printf '  \033[1;32m✓ pushed\033[0m, with proof from a passing check on this exact commit.\n'
keep stale-proof "$work/out"

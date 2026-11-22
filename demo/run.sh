#!/usr/bin/env bash
# demo/run.sh: watch an agent try to fake a green build, and the push get refused. About 30 seconds.
# It runs the real kit in a throwaway repo (deleted at the end) and changes nothing else on your machine.
# Needs git and python3 3.12+.   DEMO_PAUSE=0 demo/run.sh   runs it without the pauses.
set -euo pipefail
kit="$(cd "$(dirname "$0")/.." && pwd)"
pause="${DEMO_PAUSE:-1.4}"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

say()   { printf '\n\033[1;33m▌ %s\033[0m\n' "$*"; sleep "$pause"; }
agent() { printf '\033[1;35m  agent ›\033[0m %s\n' "$*"; sleep "$pause"; }
show()  { printf '\033[2m  $ %s\033[0m\n' "$*"; }
quiet() { "$@" >/dev/null 2>&1; }
shown() { sed -E $'s/^/  /; s/(agent-check refused:)/\033[1;31m\\1\033[0m/; s/(sk_live_)[A-Za-z0-9]+/\\1••••••••/'; }  # indent, mark refusals red, never print a key (even a fake one)

# ── a tiny shop with one passing test, already pushed ───────────────────────
git init -q --bare "$work/origin.git"
git init -q -b main "$work/shop"
cd "$work/shop"
git config user.name "demo"; git config user.email "demo@example.com"; git config commit.gpgsign false
git remote add origin "$work/origin.git"
quiet bash "$kit/scripts/install.sh" .
cat > agent-check.toml <<'TOML'
test = "python3 -m unittest discover -s tests -q"
tests = "tests/"
[gates]
guard = "enforce"
fresh = "off"
laws = "off"
red_first = "off"
seals = "off"
verified = "off"
evidence = "off"
TOML
cat > cart.py <<'PY'
def total(prices):
    return sum(prices)
PY
mkdir -p tests
cat > tests/test_cart.py <<'PY'
import unittest

from cart import total


class TestCart(unittest.TestCase):
    def test_adds_prices(self):
        self.assertEqual(total([20, 20]), 40)
PY
printf '__pycache__/\n' >> .gitignore
quiet git add -A; quiet git commit -m "shop: cart total"; quiet git push -u origin main

say "The task: \"Add a percentage coupon to the cart.\""
cat > cart.py <<'PY'
def total(prices, coupon=0):
    return sum(prices) - coupon  # bug: takes 10 off, not 10%
PY
cat >> tests/test_cart.py <<'PY'

    def test_coupon_is_a_percentage(self):
        self.assertEqual(total([20, 20], coupon=10), 36)
PY
agent "Wrote the coupon and its test. Running the tests..."
show "python3 -m unittest -q"
python3 -m unittest discover -s tests -q 2>&1 | grep -E "^(FAIL|AssertionError|FAILED)" | sed 's/^/  /' || true
agent "One fails. The deadline is close, so I'll skip that test and report green."
python3 - <<'PY'
p = "tests/test_cart.py"
t = open(p).read().replace("    def test_coupon", '    @unittest.skip("flaky")\n    def test_coupon')
open(p, "w").write(t)
PY
show "python3 -m unittest -q"
python3 -m unittest discover -s tests -q 2>&1 | tail -1 | sed 's/^/  /'
agent "All tests pass. Done!"
quiet git add -A; quiet git commit -m "Add coupon support"
say "The suite is green, so most CI would ship this. Receipts checks the push:"
show "git push"
git push -q 2>&1 | grep -E "refused|^\- \[" | shown || true

say "Try two: the agent hard-codes a payment key, then deletes it in the next commit."
quiet git reset --hard HEAD~1
key="sk""_live_""Demo0nlyN0tARealKey12345"
printf 'PAYMENTS_KEY = "%s"  # TODO remove\n' "$key" > settings.py
quiet git add -A
show "git commit -m \"Wire up payments\""
git commit -q -m "Wire up payments" 2>&1 | grep -E "refused|^\- " | head -2 | shown || true
agent "The commit check stopped me. I'll skip it with --no-verify, then delete the key."
quiet git commit --no-verify -m "Wire up payments"
quiet git rm -q settings.py; quiet git commit -m "Remove key"
show "git push"
git push -q 2>&1 | grep -E "refused|^\- \[" | shown || true
say "The key is gone from the files, but not from history. Anyone who clones the repo can read it."

say "Try three: the honest fix."
quiet git reset --hard HEAD~2
cat > cart.py <<'PY'
def total(prices, coupon=0):
    return round(sum(prices) * (100 - coupon) / 100, 2)
PY
show "python3 -m unittest -q"
python3 -m unittest discover -s tests -q 2>&1 | tail -1 | sed 's/^/  /'
quiet git add -A; quiet git commit -m "Add percentage coupon"
show "git push"
if git push -q >/dev/null 2>&1; then printf '  \033[1;32m✓ pushed\033[0m: 2 tests ran, none switched off, no keys in history.\n'; else echo "  push refused (unexpected)"; exit 1; fi
say "That's Receipts. Agents show their work; the checks stay out of their reach."

#!/usr/bin/env bash
# Example: a bug fix needs a test that names the bug and fails on the old code. Two tries are refused
# (a test that names nothing, a test that passes on the old code); the third goes through.
source "$(dirname "$0")/lib.sh"
shop laws red_first
quiet python3 "$kit/scripts/agent-check" bug "A 10% coupon takes 10% off the total, not 10 dollars."
quiet git add LAWS.md; quiet git commit -m "LAWS: B1, the coupon bug" --trailer "Verified: none, the owner's line"; quiet git push

say 'The owner logged the bug in LAWS.md as B1: "A 10% coupon takes 10% off the total, not 10 dollars."'
agent "Fixed cart.py and added a test."
cat > cart.py <<'PY'
def total(prices, coupon=0):
    """The cart total after a percentage coupon."""
    return round(sum(prices) * (100 - coupon) / 100, 2)
PY
cat >> tests/test_cart.py <<'PY'


def test_coupon():
    assert total([20, 20], coupon=0) == 40
PY
quiet git add -A; quiet git commit -m "fix: coupon is a percentage" --trailer "Verified: 2 tests pass"
refused "a test that names no law or bug"

say "Try two: the agent tags the test [B1], but it still checks nothing the fix changed."
python3 - <<'PY'
p = "tests/test_cart.py"; t = open(p).read()
open(p, "w").write(t.replace("def test_coupon():\n", "def test_coupon():\n    # [B1]\n"))
PY
quiet git add -A; quiet git commit -m "test: tag the coupon test" --trailer "Verified: 2 tests pass"
refused "a test that passes on the old code"

say "Try three: a test of the bug itself. It must fail on the old code and pass on the new."
python3 - <<'PY'
p = "tests/test_cart.py"; t = open(p).read()
open(p, "w").write(t.replace("assert total([20, 20], coupon=0) == 40", "assert total([20, 20], coupon=10) == 36"))
PY
quiet git add -A; quiet git commit -m "test: the coupon takes 10% off" --trailer "Verified: 2 tests pass"
base="$(git rev-parse @{u})"   # the old code: what the remote had before this push
pushes "the honest fix"
printf '  \033[1;32m✓ pushed\033[0m: the test names B1, fails on the old code and passes on the new.\n'

say "What red-first ran before letting it through: the new test on the old code, then the suite on this commit."
quiet git worktree add --detach "$work/old" "$base"
cp tests/test_cart.py "$work/old/tests/test_cart.py"
show "python3 run_tests.py tests/test_cart.py test_coupon      # on the old code ($(git rev-parse --short=8 "$base"))"
if (cd "$work/old" && python3 run_tests.py tests/test_cart.py test_coupon) > "$work/out/tests-old-code.txt" 2>&1; then expect "the new test passed on the old code"; fi
indent < "$work/out/tests-old-code.txt"
show "python3 run_tests.py      # on this commit ($(git rev-parse --short=8 HEAD))"
python3 run_tests.py > "$work/out/tests-this-commit.txt" 2>&1 || expect "the suite failed on this commit"
indent < "$work/out/tests-this-commit.txt"
keep bug-test "$work/out"

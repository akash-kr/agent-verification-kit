#!/usr/bin/env bash
# Example: a bug fix proved with evidence. The agent fixes the coupon, then records the same request
# on the old code and the new code. The evidence page shows the bug, then the fix.
source "$(dirname "$0")/lib.sh"
shop evidence

say 'The bug report: "A 10% coupon on a $40 cart charges $30. It should be $36."'
agent "Fixing the coupon in cart.py."
cat > cart.py <<'PY'
def total(prices, coupon=0):
    """The cart total after a percentage coupon."""
    return round(sum(prices) * (100 - coupon) / 100, 2)
PY
quiet git add -A; quiet git commit -m "fix: coupon is a percentage" --trailer "Verified: evidence, see evidence/"

say "Proving it: the same request on the old code and the new code."
show 'scripts/evidence start'
python3 "$kit/scripts/evidence" start --request <(echo 'A 10% coupon on a $40 cart charges $30. It should be $36.') 2>&1 | indent
show 'scripts/evidence run --case "..." --before --expect-contains '"'"'"total": 36'"'"' -- curl $EVIDENCE_URL/total?prices=20,20&coupon=10'
python3 "$kit/scripts/evidence" run --case 'a 10% coupon on a $40 cart totals $36' --before \
  --expect-status 200 --expect-contains '"total": 36' \
  -- 'curl -s -i "$EVIDENCE_URL/total?prices=20,20&coupon=10"' 2>&1 | indent
show 'scripts/evidence run --case "..." --expect-status 400 -- curl $EVIDENCE_URL/total?prices=20,20&coupon=ten'
python3 "$kit/scripts/evidence" run --case 'a coupon that is not a number is refused' \
  --expect-status 400 --expect-contains 'must be numbers' \
  -- 'curl -s -i "$EVIDENCE_URL/total?prices=20,20&coupon=ten"' 2>&1 | indent
show 'scripts/evidence finish'
python3 "$kit/scripts/evidence" finish 2>&1 | indent
folder="$(ls -d evidence/*/ | head -1)"
grep -q "PASS" "$folder/evidence.md" || expect "the evidence page does not pass"

pushes "the fix with evidence"
printf '  \033[1;32m✓ pushed\033[0m with its evidence page.\n'
keep api-bug-fix "$folder"

#!/usr/bin/env bash
# Example: high-stakes code needs evidence. A change under billing/ is high severity, so a green suite is
# not enough: the push is refused until the agent records an evidence page for that exact commit.
source "$(dirname "$0")/lib.sh"
shop evidence

say 'The task: "Add 20% VAT at checkout." billing/ is on the high-stakes list in agent-check.toml.'
mkdir -p billing
cat > billing/vat.py <<'PY'
def with_vat(amount):
    """The amount with 20% VAT added."""
    return round(amount * 1.2, 2)
PY
python3 - <<'PY'
p = "app.py"; t = open(p).read()
t = t.replace("from cart import total\n", "from billing.vat import with_vat\nfrom cart import total\n")
t = t.replace('''        self.reply(404, b"not found", "text/plain")''', '''        if url.path == "/checkout":
            try:
                prices = [float(p) for p in parse_qs(url.query).get("prices", [""])[0].split(",") if p]
            except ValueError:
                return self.reply(400, b'{"error": "prices must be numbers"}', "application/json")
            return self.reply(200, json.dumps({"to_pay": with_vat(total(prices))}).encode(), "application/json")
        self.reply(404, b"not found", "text/plain")''')
open(p, "w").write(t)
PY
agent "Added VAT. The suite passes, so I'm pushing."
quiet git add -A; quiet git commit -m "feat: 20% VAT at checkout" --trailer "Verified: 1 test passes"
refused "billing code with no evidence"

say "The agent records evidence for this exact commit: real requests to the app it just built."
show "scripts/evidence start"
python3 "$kit/scripts/evidence" start --request <(echo 'Add 20% VAT at checkout.') 2>&1 | indent
show 'scripts/evidence run --case "..." --expect-contains '"'"'"to_pay": 48'"'"' -- curl $EVIDENCE_URL/checkout?prices=20,20'
python3 "$kit/scripts/evidence" run --case 'a $40 cart costs $48 with 20% VAT' \
  --expect-status 200 --expect-contains '"to_pay": 48' -- 'curl -s -i "$EVIDENCE_URL/checkout?prices=20,20"' 2>&1 | indent
show 'scripts/evidence run --case "..." --expect-status 400 -- curl $EVIDENCE_URL/checkout?prices=20,abc'
python3 "$kit/scripts/evidence" run --case 'a price that is not a number is refused' \
  --expect-status 400 --expect-contains 'must be numbers' -- 'curl -s -i "$EVIDENCE_URL/checkout?prices=20,abc"' 2>&1 | indent
show "scripts/evidence finish"
python3 "$kit/scripts/evidence" finish 2>&1 | indent
folder="$(ls -d evidence/*/ | head -1)"
grep -q "^# Evidence: PASS" "$folder/evidence.md" || expect "the evidence page does not pass"
pushes "the push with evidence"
printf '  \033[1;32m✓ pushed\033[0m, with the page the owner reads before it ships.\n'
mkdir -p "$work/out"; cp -R "$folder"/. "$work/out"/
keep missing-evidence "$work/out"

#!/usr/bin/env bash
# Example: a UI change proved with evidence. The agent adds a coupon box to the cart page, then records
# the real page: a video of the flow, screenshots at desktop and phone width, console errors and failed
# requests. Needs agent-browser (npm i -g agent-browser && agent-browser install); ffmpeg is optional.
source "$(dirname "$0")/lib.sh"
command -v agent-browser >/dev/null || expect "this example needs agent-browser: npm i -g agent-browser && agent-browser install"
shop evidence

say 'The task: "Add a coupon box to the cart page."'
agent "Adding the box to cart.html and making the coupon a percentage in cart.py."
cat > cart.py <<'PY'
def total(prices, coupon=0):
    """The cart total after a percentage coupon."""
    return round(sum(prices) * (100 - coupon) / 100, 2)
PY
python3 - <<'PY'
p = "cart.html"; t = open(p).read()
t = t.replace('<div class="sum">', '''<form class="coupon" id="coupon-form"><input id="coupon" inputmode="numeric" placeholder="Coupon, e.g. 10 for 10%" aria-label="Coupon percent"><button>Apply</button></form>
<div class="sum">''')
t = t.replace('.sum { font-weight', '''.coupon { display: flex; gap: 8px; margin: 18px 0; }
.coupon input { flex: 1; font: inherit; padding: 12px 14px; border: 1px solid #c9ced4; border-radius: 10px; }
.coupon button { font: 600 16px system-ui; padding: 0 20px; border: 0; border-radius: 10px; background: #1c1b19; color: #fff; }
.sum { font-weight''')
t = t.replace('''fetch("/total?prices=20,20").then(r => r.json()).then(d => { document.getElementById("total").textContent = "$" + d.total; });''',
'''const show = (coupon) => fetch("/total?prices=20,20&coupon=" + (coupon || 0)).then(r => r.json()).then(d => { document.getElementById("total").textContent = "$" + d.total; });
document.getElementById("coupon-form").addEventListener("submit", (e) => { e.preventDefault(); show(document.getElementById("coupon").value); });
show(0);''')
open(p, "w").write(t)
PY
quiet git add -A; quiet git commit -m "feat: coupon box on the cart page" --trailer "Verified: evidence, see evidence/"

say "Proving it on the real page, not with a green suite."
show "scripts/evidence start"
python3 "$kit/scripts/evidence" start --request <(echo 'Add a coupon box to the cart page.') 2>&1 | indent
show 'scripts/evidence run --case "..." --before --expect-contains "id=\"coupon\"" -- curl $EVIDENCE_URL/'
python3 "$kit/scripts/evidence" run --case 'the cart page has a coupon box' --before \
  --expect-status 200 --expect-contains 'id="coupon"' -- 'curl -s -i "$EVIDENCE_URL/"' 2>&1 | grep -E "^(PASS|FAIL)" | indent

# The app from this commit, on a free port, and the kit's browser steps against it.
port="$(python3 -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])')"
PORT="$port" ./run-dev.sh >/dev/null 2>&1 & server=$!
trap 'code=$?; kill $server 2>/dev/null || true; wait $server 2>/dev/null || true; agent-browser --session receipts-example close >/dev/null 2>&1; rm -rf "$work"; exit $code' EXIT
for _ in $(seq 1 40); do curl -s -o /dev/null "http://127.0.0.1:$port/" && break; sleep 0.25; done
out="$work/ui"; mkdir -p "$out"
ab() { agent-browser --session receipts-example "$@" >/dev/null; }
show "browser: open the cart, type 10 in the coupon box, press Apply"
ab open "http://127.0.0.1:$port/" 2>/dev/null
ab set viewport 960 600
ab record start "$out/flow.webm" --cursor
ab wait 1200
ab click "#coupon"
ab keyboard type "10"
ab wait 900
ab click "#coupon-form button"
ab wait --text '$36'
ab wait 1800
ab screenshot "$out/desktop.png"
ab record stop
ab set viewport 390 844 2
ab wait 400
ab screenshot "$out/phone.png"
agent-browser --session receipts-example errors > "$out/page-errors.txt" 2>&1 || true
agent-browser --session receipts-example network requests > "$out/requests.txt" 2>&1 || true   # every request, so "none failed" reads as checked
agent-browser --session receipts-example network requests --status 400-599 > "$out/failed-requests.txt" 2>&1 || true
grep -q '\$36' <(agent-browser --session receipts-example get text "#total") || expect 'the total did not show $36'
printf '  requests: %s   failed: %s   page errors: %s\n' "$(grep -c -E ' [0-9]{3}$' "$out/requests.txt" || true)" "$(grep -c -E ' [45][0-9]{2}$' "$out/failed-requests.txt" || true)" "$(grep -c . "$out/page-errors.txt" || true)"

show 'scripts/evidence attach --case "..." flow.webm desktop.png phone.png'
python3 "$kit/scripts/evidence" attach --case 'apply a 10% coupon on the cart page: the total goes from $40 to $36' \
  "$out/flow.webm" "$out/desktop.png" "$out/phone.png" 2>&1 | indent
show "scripts/evidence finish"
python3 "$kit/scripts/evidence" finish 2>&1 | indent
folder="$(ls -d evidence/*/ | head -1)"
grep -q "^# Evidence: PASS" "$folder/evidence.md" || expect "the evidence page does not pass"
cp "$out/page-errors.txt" "$out/requests.txt" "$out/failed-requests.txt" "$folder/"
pushes "the change with evidence"
printf '  \033[1;32m✓ pushed\033[0m with screenshots and a recording of the real page.\n'
keep ui-change "$folder"
# The recording stays as recorded (webm). Some browsers play only mp4, so the page gets a copy when ffmpeg is here.
if command -v ffmpeg >/dev/null; then
  ffmpeg -v error -y -i "$kit/docs/examples/ui-change/media/flow.webm" -c:v libx264 -pix_fmt yuv420p -movflags +faststart \
    "$kit/docs/examples/ui-change/flow-copy.mp4"
fi

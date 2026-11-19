#!/usr/bin/env bash
# UI evidence with agent-browser: one real recording, screenshots at desktop and phone
# width, and the console errors and failed requests the flow produced.
# Usage: agent-browser.sh <url> <out-dir>      HEADED=1 to watch it in a window (default: headless)
set -uo pipefail
url="$1"; out="$2"
mkdir -p "$out"
ab() { agent-browser --session evidence ${HEADED:+--headed} "$@"; }
trap 'ab record stop >/dev/null 2>&1; ab close >/dev/null 2>&1' EXIT

ab open "$url" >/dev/null || { echo "FAIL  could not open $url"; exit 1; }
ab set viewport 1280 800 >/dev/null
ab record start "$out/flow.webm" --cursor >/dev/null

# TODO(you): the steps of the flow under test, e.g.
#   ab click "text=Sign in"; ab fill "#email" "reader@example.com"; ab wait --text "Welcome"

ab screenshot "$out/desktop.png" >/dev/null
ab set viewport 390 844 >/dev/null
ab screenshot "$out/phone.png" >/dev/null
ab record stop >/dev/null

ab errors >"$out/page-errors.txt" 2>&1
ab console >"$out/console.txt" 2>&1
ab network requests --status 400-599 >"$out/failed-requests.txt" 2>&1
ls "$out"

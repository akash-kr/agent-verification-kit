---
name: verify
description: Run this repo's app the way a user would and prove a change works - start it on a throwaway local setup, walk the main flows, take screenshots, and write the proof a push needs. Use before every commit that changes behaviour, and whenever asked to "check it works", "test it in the browser", "smoke test" or "verify".
---

# Verify

Run `.claude/skills/verify/check.sh` from the repo root. It must print `RESULT: all checks passed`.

1. It starts the app with no real keys and a fresh database, so it cannot bill a provider or touch
   production. Never point it at a live service.
2. Each `step` follows a real user flow and prints PASS or FAIL with what broke.
3. Read every screenshot it lists before saying the change works. A passing script on a page you
   did not look at is not verified.
4. On a pass it writes `.test-tmp/verify/passed`: this commit, "clean", and a hash of each
   screenshot. The push gate (`fresh` in agent-check.toml) accepts nothing else, so commit first,
   then run it.
5. A FAIL you cannot fix in three attempts goes to a human with the output.

Add a step whenever a flow ships or breaks. Keep the whole run under two minutes: a slow check gets
skipped.

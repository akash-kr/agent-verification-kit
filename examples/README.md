# Examples

Six short runs of the real kit against a tiny shop (`shop/`: a cart page, a `/total` endpoint and two
tests). Each one makes a throwaway copy of the shop, installs the kit, plays one change the way an agent
would, and deletes the copy at the end. Nothing outside that copy is touched.

Every refusal, evidence page, screenshot and recording in `docs/examples/` comes from these runs. None of
it is typed in by hand.

```bash
examples/run-all.sh          # all six, then refresh docs/examples/ (about 30 seconds)
examples/api-bug-fix.sh      # or one at a time; DEMO_PAUSE=1.5 slows it down for a screen recording
```

They need git and Python 3.12+. `ui-change.sh` also needs
[agent-browser](https://github.com/vercel-labs/agent-browser) (`npm i -g agent-browser && agent-browser install`).
ffmpeg is optional: with it, the recording gets an mp4 copy for browsers that don't play webm.

| Example | Check | What the agent does | What it gets |
|---|---|---|---|
| `api-bug-fix.sh` | evidence | Fixes the coupon bug | An evidence page: the same request on the old code (`{"total": 30.0}`) and on the fix (`{"total": 36.0}`) |
| `ui-change.sh` | evidence | Adds a coupon box to the cart page | An evidence page with a recording of the real page, phone and desktop screenshots, and its console and network errors |
| `missing-evidence.sh` | evidence | Changes `billing/` and pushes on a green suite | Refused: high-stakes code owes an evidence page. It records one, and the push goes through |
| `bug-test.sh` | laws, red-first | Adds a test with the fix | Refused twice: the test names no logged bug, then it passes on the old code. The third test fails before the fix and passes after |
| `sealed-test.sh` | seals | Loosens the owner's sealed test to make the suite green | Refused: the test no longer matches its seal |
| `stale-proof.sh` | fresh, verified | Edits after its last check, then ships on the old proof | Refused at commit (no `Verified:` line), then at push (the proof names the commit before). It checks again, and the push goes through |

The guard (a skipped, deleted or moved test, a key in history) has its own demo: `demo/run.sh`.

Each script checks its own outcome. If a push that should be refused goes through, a push that should
go through is refused, or an evidence page does not pass, it stops with "example failed: …".

## Removing them

Everything here is for showing the kit. To drop it, delete `examples/` and `docs/examples/`. The
project page hides its examples section when `docs/examples/` is gone.

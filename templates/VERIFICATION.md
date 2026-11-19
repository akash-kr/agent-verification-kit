# Verification rules for agents

Paste this into your AGENTS.md or CLAUDE.md. Each rule says what enforces it; the rest are rules
an agent follows because no check can see them.

## Done means observed

- "Done", "fixed" or "works" cites what you observed after the last edit: the command and its output,
  the page in a browser, the number against its source. Reading code is "inferred", never "verified".
- Verify by running the change: web in a browser, mobile in a simulator, a backend by running the
  service locally. Use the repo's verify skill (`.claude/skills/verify/`) before committing.
  Once `[gates] fresh` is on enforce, a push needs proof from that skill on this exact commit.
- Show evidence, not a green suite: `scripts/evidence start`, then one `scripts/evidence run --case
  "<what it proves>" --expect-... -- <the real request, call or command>` per case (a bug fix needs one
  with `--before`), then `scripts/evidence finish`. Never type a result. A case that can write on
  production waits for the owner's yes.
- Say how you checked in the commit, as a trailer: `Verified: ran verify, 14/14 PASS, read both
  screenshots`, or `Verified: none, <why>`. Checked at commit and in CI once `[gates] verified` is on. It is your claim, not
  proof; it makes unverified commits searchable.
- Prefer the check you did not write: the old system on the same data, the real page, the real
  service's reply, a statement's own totals.

## Laws and tests

- What must stay true is `LAWS.md`: one line per law (`L3: …`) or fixed bug (`B2: …`), each saying
  what holds it. Only the owner adds or changes a line; you may propose the wording.
- Write a test only to hold a law or a fixed bug, and name it as `[L3]` or `[B2]`. Once `[gates] laws` is on
  enforce, a new test that names no line is refused.
- A bug test must fail on the code before the fix. The red-first check runs it there (`[gates] red_first`).
- A new law's test is written by a fresh agent that sees only the law line and the interface, never
  the implementation, and the owner seals it (`agent-check seal`). The implementing agent makes it
  pass and never edits it. A sealed test that changes is refused unless its law changed.
- No tests for copy, layout, getters, constants or mocks: check those in the real output.
- Never weaken an assertion or a law to make a check pass. Shown: every removed or rewritten
  assertion is listed at push.

## When checks fail

- Three strikes: if the same check still fails after three fix attempts, stop and hand it to a
  human with the failing output and what you tried. Do not try a fourth idea on your own.
- Flaky tests: never skip one, add a sleep or rerun it until it passes. Find the cause. If you
  cannot, delete the test and record why (the commit message and the law it held).
- A check that escalates says why, so the reviewer does not have to reconstruct it from the diff.

## The checks are not yours to change

- `LAWS.md`, `.sealed-tests`, `agent-check.toml`, `scripts/agent-check`, git hooks and CI change only
  with the owner's approval of that exact change. CI reads the checker and its config from the base
  commit; the rest is protected only by CODEOWNERS with branch protection.
- New gates start in observe mode. Switch one to enforce only after its log shows no false positives.

## Learning from misses

- A miss becomes a rule only when it recurs (two or more changes) and can be seen in a diff. Write it
  as a `[[question]]` with the paths that trigger it, or as a law with a test; the owner approves it.
- Every bug that ships becomes a review-eval case (`evals/review/`) with a one-sentence answer key,
  and a clean merged change of the same size becomes a control. Run `review-eval` after changing
  the reviewer's prompt or rules.
- Prune monthly: run `agent-check audit`, delete laws nothing holds, questions that never fire and
  approved diffs that no longer exist. Rules only grow unless someone removes them.

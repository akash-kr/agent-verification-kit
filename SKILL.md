---
name: agent-verification-kit
description: Sets up and runs a verification harness for coding agents in any git repo - laws with sealed, red-first tests, real-app proof per commit, checks a change cannot edit, diff-triggered questions, observe-then-enforce gates, a "Verified:" stamp, evidence owed by change type and severity (real requests, before/after, recordings), reviewer evals, differential tests and a pruning audit. Use when installing agent guardrails, "set up verification", "make agents prove their work", "add a pre-push gate", adding a law or bug test, grading a code reviewer, "show me evidence", or when an agent claims done without evidence.
---

# Agent Verification Kit

Agents show evidence a change works; the checks stay out of the change's reach. `--help` on each script lists everything.

## Install

`scripts/setup <repo> [--github]` copies scripts, templates and hooks (never over an existing file),
detects the suite, app and surfaces, and offers to install missing tools. `--check` is the health check.

## The loop for every change

1. **Run it** with the repo's verify skill (`.claude/skills/verify/check.sh`): the app locally with no
   real keys, every flow walked, every screenshot read. Its proof names this commit.
2. **Stamp it:** a `Verified: <command and result>` trailer, or `Verified: none, <why>`.
3. **Answer the questions** `agent-check commit` prints for the paths this diff touches.
4. **Push.** Refused when behind upstream, dirty or failing; under enforce, also for a missing proof,
   a test naming no law, a bug test green on old code or a changed sealed test.
5. **Three strikes:** a check still failing after three fixes goes to a human with the output.

## Evidence (references/evidence.md)

`scripts/evidence start` labels the push by surface, intent and severity and says what it owes.
Record each case with `evidence run --case "<what it proves>" --expect-... -- <real command>`:
the real request, function call or command, never suite output. A bug fix needs one `--before` case
that fails on the old code. UI: run a recipe in `.claude/skills/verify/ui/`, then `evidence attach`.
`evidence finish` writes the page. High severity is refused at push without it, and is recorded by
an agent other than the author (`evidence brief`). Never type a result; never run a write on
production without the owner's yes.

## Laws (references/laws-and-seals.md)

- `LAWS.md` holds one line per law or fixed bug, each saying what holds it: architecture, then a type,
  then a lint, then a test. Only the owner adds lines (`agent-check law|bug "<text>"`).
- A new law's test is written by a fresh agent that sees only the law line and the interface. The owner
  seals it with `agent-check seal file::test`, and the implementer never edits it.
- Never weaken an assertion to pass. Every changed assertion is listed at push.

## Tests worth writing (references/test-types.md)

End-to-end tests of real flows first, then property tests for invariants, then differential tests
(`scripts/diff-check`) when replacing code that works. Never skip, sleep-pad or rerun a flaky test: fix or delete it.

## Gates (references/gates.md)

`[gates]` in `agent-check.toml` sets `fresh`, `laws`, `red_first`, `seals`, `verified` and `evidence`
to off, observe or enforce. Observe logs to `.git/agent-check-observe.log` without blocking. CI runs the base commit's checker and config; CODEOWNERS guards `LAWS.md` and the seals.

## Learning (references/measuring-reviewers.md)

- A miss seen in two changes becomes a `[[question]]` or a law; the owner approves it.
- Every shipped bug becomes a `review-eval` case with a clean control.
- Prune monthly with `agent-check audit`.

## Never

- Edit `LAWS.md`, `.sealed-tests`, the checker, its config, hooks or CI without the owner's approval.
- Use `--no-verify`, or write a proof file by hand.
- Call a change verified from reading code.

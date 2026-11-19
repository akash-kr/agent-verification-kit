# Measuring the checks, and turning misses into rules

## Grade the reviewer on bugs that happened

`scripts/review-eval` replays your reviewer against past changes:

- **bug cases:** a commit that shipped a real bug, a one-sentence `answer`, and `match` words that any
  correct finding must contain;
- **controls:** merged changes of similar size that stayed clean. A reviewer that flags them is
  over-flagging.

```
scripts/review-eval --reviewer "./scripts/my-reviewer" --set test
test: recall 7/9 bugs caught, false flags 1/9 clean changes, errors 0
```

The reviewer reads the diff on stdin and prints findings like
`FINDING important|nit|pre-existing: <text>`. Only `important` counts: nits are noise, and a
pre-existing bug isn't the author's fault. Any reviewer works, including a model CLI, a script or a
wrapper around your review bot. Running a model reviewer costs money.

- **Keep two sets.** Tune the reviewer's prompt and rules against `tune`. Report on `test`, which you
  never tune against. Stop raising recall once gains on `tune` stop showing up on `test`: that's
  overfitting.
- **Source every answer key** from an incident doc, a revert or a PR (`source =`). Never write one
  from memory.
- **Shortcut:** grading matches words. A finding that describes the bug in other words counts as a
  miss. Read the misses before trusting a low score. Upgrade to a model judge if word matching
  misgrades often.

What to track beyond review-eval, from your own history:

- reverts and fix-up commits after merge (misses that shipped);
- changes a maintainer rejected (misses the checks didn't catch);
- `agent-check audit`'s unverified-commit count.

Measure each stage separately where you have stages: raw findings, after self-verification, final
review. Then you can see where a real bug was dropped.

## Turn misses into rules

There are two sources:

1. **Mining.** Scan review comments and reverts for patterns that appear in at least two changes and
   can be seen in a diff. Have two or three agents try to disprove each candidate. The owner approves
   the survivors in a PR.
2. **Replay.** Run bug finders against the change behind a known incident. If most catch it, the bug
   was detectable, and the miss is a gap in your rules: add a `[[question]]` with the paths that
   trigger it, a law, or a review rule.

Every rule names the incident or PR it came from, so whoever prunes it later knows what it guards.

## Prune

Rules, laws, questions and approved diffs only grow unless someone removes them. Once a month:

- `scripts/agent-check audit` lists laws nothing holds, "held by" references to tests that are gone,
  tests that name no law, tags naming no law, orphan seals and unverified commits;
- delete questions whose paths no longer exist or that never caught anything;
- delete review-eval cases whose code is gone (keep the controls balanced with the bugs);
- the owner deletes the law lines that no longer apply.

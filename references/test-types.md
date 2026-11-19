# Three tests worth investing in

Avoid flaky tests: they teach an agent to rerun instead of fix. Avoid slow tests too: fewer runs per
batch means failures get harder to pin down.

## 1. End-to-end: the real flow

Example flow: sign in, add an item, check out, see the confirmation. An E2E test is hard to fool,
has a clear done state, and says where things broke. A unit test that says "Timeout after 30s"
helps less than a step trace with a screenshot that says "Place order stayed disabled because the
payment form never loaded".

- Give the agent hands and eyes: a browser driver (Playwright, Chrome DevTools Protocol), a mobile
  simulator, computer use for desktop apps, or an API harness for a backend.
- Keep a feature map: each feature as the user sees it, with its path, selector or shortcut and the
  expected result. It doubles as the grading rubric.
- Put the flows in the verify skill's `check.sh`, so every commit runs the same ones.

## 2. Property tests: rules that must always hold

You state the invariant and a library generates the inputs, so the cases are free of the bias of
whoever wrote the code.

| Property | Example |
|---|---|
| Round trip | `decode(encode(x)) == x` |
| Invariant | a balance never goes negative after any sequence of transfers |
| Idempotent | applying a webhook twice equals applying it once |
| Equivalence | the optimised function equals the naive, obviously correct one |

```python
from hypothesis import given, strategies as st

@given(st.lists(st.integers()))
def test_sorted_keeps_every_item(xs):
    """[L7]"""
    assert sorted(fast_sort(xs)) == sorted(xs)
```

Libraries: Hypothesis (Python), fast-check (JS/TS), proptest (Rust). A property test holds a law
like any other test: tag it.

## 3. Differential tests: the old system is the oracle

Use these for a rewrite or migration that should behave the same. Feed the same inputs to both and
treat any difference as a bug or a breaking change.

```
scripts/diff-check --cmd "python3 -m app.cli price" --base origin/main --inputs samples/ --approved samples/APPROVED
scripts/diff-check --old "./legacy/price" --new "python3 -m app.cli price" --inputs samples/
```

- Inputs are files fed on stdin, either generated or sampled from real traffic (scrubbed of personal
  data).
- Whitespace is collapsed unless you pass `--exact`. Normalise other noise, like timestamps and ids,
  in the command.
- `APPROVED` lists the inputs whose difference is intended, one per line with a `#` reason.
  `diff-check` names approved entries that no longer match an input, so you can prune them.

## Flaky tests

Never skip one, add a sleep, or rerun it until it passes. Find the cause, usually time, ordering,
shared state or the network. If you can't, delete the test and say why in the commit, and if it held
a law, say what holds that law now.

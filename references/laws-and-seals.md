# Laws, seals and red-first tests

## A law line

```
L4: Every fetch of a user-supplied URL goes through the one network door. — held by: architecture (net.fetch is the only caller of the HTTP client) and lint tests/test_laws.py::test_no_raw_http
B2: A retried webhook never grants the plan twice. — held by: tests tagged [B2]
```

- One plain sentence a non-engineer can check. `L` for a law, `B` for a fixed bug.
- "held by" names the cheapest thing that keeps it true:
  1. architecture: one function owns the write; everything else must call it;
  2. a type the compiler checks;
  3. a lint: a test that reads the source (for example "no file outside net/ imports requests");
  4. a behaviour test, as the fallback.
- `agent-check audit` checks every `file.py::test` named after "held by" still exists.

## Who writes what

| Step | Who | Why |
|---|---|---|
| Law wording | owner approves, agent may draft | the law is the spec; the implementer cannot move it |
| The law's test | a fresh agent that sees only the law line, the request and the interface | a test written by the implementer shares its blind spots |
| Seal | owner runs `agent-check seal file::test` | the fingerprint ignores comments and layout, but not logic or string data |
| Code | implementing agent | makes the sealed test pass, never edits it |

A sealed test may change only in a push that also changes its law, which only the owner does.
Fixtures listed in `seal_support` are not sealed; a push that changes one warns.

## Red-first

A bug test must fail on the code before the fix. At push, agent-check:

1. checks out the base commit in a throwaway worktree;
2. copies in the new tests as committed (not as on disk);
3. runs one old test first, so a runner that cannot run old code doesn't make every new test look red;
4. runs each new test. Exit 0 means it already passes, so it tests nothing: refused. Exit 1 means a
   real failure: accepted. Any other code means it couldn't load: refused. Test the bug through code
   the old version had.

A test for a law added in the same push is exempt: a new law may already be true.

## What the push hook refuses (enforce mode)

- A new test that names no line in LAWS.md (`laws`).
- A test defined twice in one file (`laws`).
- A bug test that passes, or cannot run, on the old code (`red_first`).
- A test for a new law or bug that isn't sealed, a changed sealed test, and a seal changed without its
  law (`seals`).

It always lists removed or rewritten assertions and every LAWS.md change.

# Guard: spec

Status: approved by the owner 2026-11-22 (laws L1 and L2, narrow v1, Foreman's cases as a replay set);
being built. Source: Foreman (github.com/PedValme/foreman, MIT) at
`23353319063619f47e7b1c477220d24f20d496dd`. Line numbers are its `plugin/foreman/detector.py`.
Reviewed twice by a fresh Fable agent; its findings are folded in below.

## What it is for

A push is refused when it switches a test off, deletes a test file or moves one out of the runner's
reach, unless the owner allowed that exact finding. A push is always refused when any of its commits
adds a credential in a known format. It answers "did the agent rig the check?". Proof and evidence still
answer "does the change work?".

## Laws

- `L1: With the guard gate on enforce, a push that adds a skip marker to a test, deletes a test file, or moves a test file where the runner won't collect it is refused, unless .guard-allow names that exact finding.`
- `L2: A push is refused when any of its commits adds a credential in a known format, even if a later commit removes it.`

Each law is held by blind-written, sealed tests in `tests/test_guard_laws.py`, tagged `[L1]` / `[L2]`.

## Interface (what the law tests see)

- **Run:** `python3 scripts/agent-check push --base <sha> --no-suite`, from inside the repo. It checks
  `<sha>..HEAD`. `scripts/agent-check` calls `scripts/guard`, its sibling file.
- **Config:** `agent-check.toml` at the repo root. `[gates] guard = "off" | "observe" | "enforce"`,
  default `observe`.
- **Exit:** 0 = pass, 1 = refused.
- **Output:** each finding is one stderr line containing
  `[<rule>] <path>[:<line>] id=<8 hex> — <what>. Fix: <fix>`. Rules are `test-skipped`, `test-deleted`,
  `test-moved` and `secret-history`.
- **Observe:** a test-rule finding prints `agent-check observe mode, would refuse (not blocking)` and
  exits 0.
- **Secrets:** `secret-history` refuses in every mode, including `guard = "off"`, and no grant passes it.
- **Grant:** `.guard-allow` at the repo root, read from the pushed HEAD. One finding per line:
  `<id>  # <reason>`. A grant covers only that id.
- **Agent mark:** a `guard:allow` comment on a line never passes on its own. The finding stays refused
  until `.guard-allow` names its id.
- `scripts/guard --base <sha>` can also run alone: exit 0 clean, 1 findings, 2 could not inspect.

## Rules in v1

| Rule | Refused when | Foreman source to port |
|---|---|---|
| `test-skipped` | an added line in a test file has a skip, only, ignore or xfail marker; a conditional skip is added to an existing test file; a test is renamed so the runner stops collecting it | `SKIPPED_TEST` L105, `CONDITIONAL_SKIP` L121, `PY_ALIAS_*` L338, `code_only` L328, `CHECK_SURFACE` L324, `_renamed_tests` L628 and helpers L557-603 |
| `test-deleted` | a test code file is deleted (not fixtures, snapshots, data or `.pyc`) | `TEST_PATH` L51, `TEST_CODE` L131, `NOT_TEST_CODE` L137 |
| `test-moved` | a test file moves out of the tests, or is renamed to a name the runner does not collect | `COLLECTED_NAME` L135, `detect` L739 |
| `secret-history` | a credential in a known format in any pushed commit (its changes or its message), even one a later commit removed | `history_secrets` L704, `SECRET_FORMATS` L56 |

- Markers are matched as text, so these rules cover Python, JS, Go, Rust and Java.
- Outside test files, a marker counts only as code, not inside a string or comment. The exception is
  files that run the check (workflows, Makefile, `tox.ini`, `package.json`), where any mention counts.
- `secret-history` uses known formats only (`SECRET_FORMATS`). Guesses stay with the commit check, which
  is unchanged in v1. Switching the commit check to Foreman's lists would loosen it.

## Finding ids

The id is the first 8 hex digits of the sha256 of the rule family, the path, the normalised content and
the test the line covers (line findings): for a decorator, the line it decorates (past the rest of a
multi-line decorator, comments and other decorators); for a call that names its test on the next lines
(`it.skip(` then the name), those lines; then the definitions it sits in. So one grant never covers the
same line in a second test. File findings use the rule, the path and the new content's blob
id, or "deleted" (`fingerprint` L201). A line number never counts, so a grant survives an edit elsewhere
in the file and dies with any change to what it covers.

## Wiring

- `agent-check push` runs the guard before the suite and reports its findings first, so a failing suite
  does not hide one. The credential check runs even when the repo has no `agent-check.toml`.
- It fails closed: a missing `scripts/guard`, an exit other than 0 or 1, or an answer that is not a list of
  findings matching the exit refuses the push as "could not inspect".
- The guard reads every file as text (`--text`, no textconv, no external diff), reads git's output as
  bytes split on `\n` only, and follows each hunk by its line counts, so neither `.gitattributes`, a NUL
  byte, a stray `\r` nor a line starting `++ ` can hide an added line.
- On a first push (no upstream) the guard runs against the empty tree, so secrets in the whole history
  are caught, root commit included.
- `guard` is added to `DEFAULT_MODE`. An old checker rejects an unknown gate, so `setup --check` says to
  update `scripts/agent-check` and `scripts/guard` together.
- CI copies `scripts/guard` from the base beside `agent-check`. When the base has none, it warns and uses
  the pushed copy, as it does for `agent-check`.
- `.guard-allow` and `scripts/guard` are added to `templates/CODEOWNERS` and to CI's
  "this change edits the checks" warning.
- `install.sh` copies `scripts/guard`.

## Foreman's cases: a replay set, not tests

Foreman's detector cases go in `evals/guard/cases.json` (input diff or file operations, expected rule
or pass), rewritten to our semantics: a mark alone never passes, so his allowance cases flip.
`scripts/guard replay evals/guard` runs them and prints misses. They are data, not sealed tests, so fixing
a false positive edits the case or the rule, never a seal.

## Trust, stated plainly

- `.guard-allow` is read from the pushed commit, so the agent can write it. It is held the way
  `LAWS.md` is: CODEOWNERS plus branch protection, with no direct pushes to main. On a repo without
  branch protection, it is advice.
- Local config comes from the working tree, so `guard = "off"` in the same push switches the local check
  off. CI reads the base's config.
- Local hooks can be bypassed. CI is the gate that counts.

## Not in v1

- Check edits (`check-changed`) and loosened CI (`check-weakened`). With the template's pytest command,
  check-changed would protect nothing.
- Hook bypass at tool time (step 5).
- Loosened or removed assertions and emptied tests. These stay listed at push. Foreman's detector cannot
  see them either.
- A second-model review, a merge gate, SARIF, and Foreman's board, panel and notifications.

## Known limits we inherit

- Tests switched off through configuration: `-k 'not x'` in `addopts`, `collect_ignore`, `python_files`,
  a `load_tests` that returns nothing.
- An unknown rename (`test_x` to `tst_x`) or an unknown decorator.

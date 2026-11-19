# Evidence by change type

`scripts/evidence` decides what proof a push owes, records it from real runs and keeps it readable.
`scripts/evidence --help` lists every option.

## The flow

```bash
scripts/evidence start --request ask.txt     # labels the push, opens evidence/<date>-<slug>-<commit>/
scripts/evidence run --case "a negative quantity is refused" --before \
    --expect-status 400 --expect-contains "must not be negative" \
    -- 'curl -s -i "$EVIDENCE_URL/total?qty=-2"'
scripts/evidence attach --case "checkout on phone and desktop" out/desktop.png out/phone.png out/flow.webm
scripts/evidence finish                      # writes evidence.md, the proof and the index line
```

Nobody types a result. `run` executes the command, records the command line, output, exit code, HTTP
status and time, and compares them with the expectation. `finish` writes `evidence.md` with a verdict,
a "Not shown yet" list, and one section per case: input, expected, before, after, what ran, what came
back.

## Labels

Each push gets three labels (`evidence classify`):

- **Surfaces:** ui, api, logic, migration, job, cli, config, dependency, performance, security, prompt,
  tests, docs, exploration. The built-in rules read file paths, first match wins.
- **Intent:** bug, feature, refactor, exploration, from commit subjects (`fix:` is a bug).
- **Severity:** `high` if a changed path (either end of a move) starts with an `[evidence] high`
  prefix (default: the `review` list); `medium` for `[evidence] medium` prefixes and for any
  migration, security or job change; otherwise `low`.

`[evidence] classifier` names a command that reads the diff on stdin and prints JSON. `setup` installs
one as `scripts/evidence-classifier` (the prompt is in it; it calls Claude Code's small model, or
whatever `EVIDENCE_MODEL_CMD` names). It can add surfaces, set the intent and raise the severity. It can
never remove a surface or lower the severity. Without it the rules alone label the push: free and
offline, and blind to what file names do not show (a permission check inside `utils.py` is `logic`).

## What is owed

| Surface | A case must show |
|---|---|
| ui | Screenshots at phone and desktop width, one real recording, console errors, failed requests |
| api | The exact request and response for one success and each failure case |
| logic | Input, expected output and actual output from calling it for real |
| migration | On a copy: schema and row counts before and after, sample rows, the rollback, time taken |
| job | The job triggered once: what it picked up, what it wrote, what a second run does |
| cli | The command typed and its output, for one good and one bad input |
| config | The value before and after, and what it controls behaving differently (or a dry run) |
| dependency | Old and new version, what the changelog says breaks, the flows that use it re-run |
| performance | The same measurement before and after, with the method and number of runs |
| security | The allowed request succeeding and the forbidden one refused, each as a different user |
| prompt | The same fixed inputs before and after, outputs side by side |
| tests | Per test: input, expected, actual, and that it fails on the old code |
| docs | The rendered page or text, before and after |

A mixed change owes one case on the outermost surface a person uses (ui, then api, then cli, then
logic), plus its own case for every migration, security, job, config, dependency, prompt and
performance surface. `finish` reports INCOMPLETE while an owed surface has no case, a ui surface has no
media, a bug fix has no `--before` case, or a case was recorded on another commit or with
uncommitted files.

The recorder checks exit code, HTTP status and output text. For surfaces that need more (a
migration's row counts, a job's writes, two users), the case command is a script that prints those
facts; the recorder cannot tell whether the script looked at the right thing.

## Severity decides the gate

```toml
[gates]
evidence = "observe"     # off | observe | enforce
[evidence.owes]
medium = "agent"         # none | agent | human
low = "none"
```

High always owes `human`. With the gate on, `agent-check push` refuses a push that owes `agent` or
`human` evidence unless a folder for this exact commit has a proof whose hashes still match. The gate
recomputes severity from the paths and the base commit's config (`--config-from`), so editing
`labels.json` to "low" passes nothing. `human` prints the page's path and asks you to read it; `agent`
means nobody has to.

`scripts/evidence override --reason "..."` passes one refusal. It needs a person at a terminal and
writes a line to `evidence/OVERRIDES.log`.

## Before and after

`--before` replays the same command on the commit the change started from, in a throwaway worktree.
The old code must not meet the expectation. If it does, the case is flagged: it does not show what
the change fixed. If the command cannot run there (not found, timed out), the case is inconclusive.
With `[evidence] serve` set, `$EVIDENCE_URL` points at the app started from the same checkout as the
case, on a free port, so the response comes from that code and not from a server already running.

## An independent verifier

`scripts/evidence brief` prints a brief for an agent that did not write the change: the request, the
diff range, what each surface owes and the rules (record through the recorder, call the real thing,
choose cases from the request). Give it to a different model and have it set `EVIDENCE_DRIVER` so
the page says who recorded it. The kit cannot check which model ran.

## UI recipes

`templates/ui-recipes/` (installed to `.claude/skills/verify/ui/`). Each takes a URL and an output
folder, and produces `flow.webm`, `desktop.png`, `phone.png`, `console.txt` and
`failed-requests.txt`. Headless by default; `HEADED=1` opens a window.

- `agent-browser.sh`: run against a local page; produces numbered-label screenshots.
- `playwright.mjs`: **not run by the kit's authors**; needs `playwright` in the repo's `node_modules`.
  No numbered labels.
- Chrome DevTools: no recipe yet. Use it to debug, then record with one of the two above.

With no recording, `scripts/evidence stitch --out flow.mp4 a.png b.png` joins screenshots into a clip
(needs ffmpeg). A produced, captioned video is a demo, never evidence.

## Where it lives

```
evidence/
  INDEX.md                               one line per change: date, labels, verdict, commit, release tag
  OVERRIDES.log
  2026-01-14-refuse-negative-qty-3f2a91c0de/
    evidence.md   labels.json   cases.jsonl   passed   media/
```

One folder per commit; `start` on the same commit starts over. Text stays for good. `finish` and
`prune` delete `media/` older than `keep_days` (30) unless the change was high severity or its
commit is tagged. A file over `max_media_mb` (25) is refused. `setup` adds `evidence/` to
`.gitignore`; `setup --commit-evidence` leaves it in git.

## Environments and secrets

`--env NAME` says where a case runs. Under `[evidence.env.NAME]` with `production = true`, a case
that is not `--read-only` stops and asks for a typed `yes` at a terminal; with no terminal it is
refused. A command naming a production host without the matching `--env` is refused.

Authorization and cookie headers, bearer tokens, `key=value` secrets, JWTs, email addresses and the
values of `redact_env` variables are replaced in the recorded command and output before anything is
written. The repo's path becomes `.` and the home folder `~`.

## Limits

- The proof is a local file. An author who can run `finish` can regenerate it; it stops a stale or
  hand-edited page, not a determined author. CI cannot see it, so the evidence gate is local only.
- `OVERRIDES.log` is a plain file: the terminal prompt stops an accident, not an agent that appends a
  line. Read the log; `git diff` shows it when the folder is committed.
- The gate reads the base commit's config when it has one, so a config change takes effect from the
  push after it. The independent verifier's model is whatever `EVIDENCE_DRIVER` says.
- `--read-only` and `--env` are the author's word. The recorder cannot see what a command does.
- Screenshots and recordings are not redacted. Text redaction is pattern-based and will miss a secret
  with no recognisable shape; list its variable in `redact_env`.
- A case can pass without exercising the change. The before run catches that for bug fixes only.
- A classifier command sends your diff to whatever it calls.
- Not built: posting the page to a pull request, a UI before-screenshot, a sample page at setup.

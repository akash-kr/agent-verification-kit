# Evidence by change type: design

Status: built in `scripts/evidence`, except pull-request posting, the UI before-screenshot, the
Chrome DevTools recipe and the sample page at setup. How it works as built: `references/evidence.md`. The gate described in the README (laws, seals, red-first, proof
file, questions, observe mode, the `Verified:` trailer) exists; this adds the layer that decides
what evidence a change owes and records it.

## 1. Classify, once per push

The whole diff from where the branch started to the pushed commit gets three labels.

**Surface** (where the change shows):

| Surface | Evidence a human reads |
|---|---|
| UI (web, mobile, extension) | Screenshots at phone and desktop width, one real recording of the flow, console errors and failed network requests |
| API or endpoint | The exact request and response for one success and each failure case |
| Logic (a function or module) | A table of input, expected output and actual output from calling it for real |
| Database migration | Run on a copy: schema before and after, row counts before and after, three sample rows before and after, the rollback run, time taken and locks |
| Background job, queue or scheduler | The job triggered once: what it picked up, what it wrote, what a retry or second run does |
| CLI or script | The command typed and its real output, for one good and one bad input |
| Config, CI, deploy or infra | The value before and after, and the thing it controls behaving differently (or a dry run) |
| Dependency upgrade | Old and new version, what the changelog says breaks, the flows that use it re-run |
| Performance | The same measurement before and after, with the method and number of runs |
| Security, auth or permissions | The allowed request succeeding and the forbidden one refused, each as a different user |
| Prompt or model behaviour | The same fixed inputs before and after, outputs side by side |
| Tests only | Per test: input, expected, actual, and that it fails on the old code. Never raw suite output |
| Docs or copy only | The rendered page or text, before and after |
| Exploration or research (no change) | Each claim with its source or the command that showed it |

**Intent** (what must be shown on any surface): bug fix (broken before, fixed after, same steps);
feature (the new flow plus one failure path); refactor (old and new give the same result);
exploration (nothing ships).

**Severity:** low, medium, high. Paths listed in the config set a floor; the classifier may raise a
grade and never lower it. Migration, security and job surfaces are at least medium.

The classifier is any command named in the config: it reads the diff and prints the three labels
as JSON (the kit ships the prompt and the schema). With no command set, a built-in rules classifier
works from paths and file types: free and offline.

## 2. What each severity owes

A config table maps severity (optionally per surface) to one of three levels:

- **human evidence**: an evidence page the owner reads;
- **agent verified**: a verifier runs the cases and records a one-line verdict, no page to read;
- **none**.

High is always human evidence, and a push without current, passing evidence is refused. Medium and
low are the owner's choice. An owner override passes a refusal and is logged (who, why, commit);
the audit lists every one.

## 3. Mixed changes

Evidence goes through the outermost surface a person uses (the screen recording already exercises
the endpoint and function behind it). Migration, security and job surfaces always owe their own
evidence on top, because the outer surface cannot show them.

## 4. Who records

A recorder command runs each case and captures the real command, request, response, output, exit
code and time, then compares with the stated expectation:

    evidence run --case "expired token is refused" --expect-status 401 -- curl -s -i ...

Nobody types results. The agent chooses the cases and writes one line saying what each proves. The
captured output is hashed into the proof, so editing it breaks the proof.

For high severity an independent agent, on a different model from the author, drives the recorder.
It sees the owner's request, the diff and the labels, never the author's reasoning. For medium and
low the author drives the recorder unless the config says independent.

## 5. Before and after

For a bug fix, each API, logic, CLI, job, migration and test case is replayed on the commit before
the change in a throwaway worktree, and shown as Before (expected to fail) and After (expected to
pass). A bug case that passes on the old code is flagged. UI gets a before screenshot only at high
severity.

## 6. UI evidence

One contract (steps, screenshots at two widths, one real recording, console and failed
network requests) and one recipe each for agent-browser, Playwright and Chrome DevTools, each
producing exactly that. Headless by default so it runs in CI; headed on request. If recording is
unavailable, the screenshots are stitched into a clip with ffmpeg. A produced, captioned video
(for example rendered from HTML) is an optional demo and is never proof.

## 7. Where evidence lives

A local folder per push, `evidence/<date>-<slug>-<commit>/`, holding `evidence.md` and `media/`. An
index file has one line per change: date, labels, severity, verdict, commit, and the release tag it
shipped in. Text and the index are kept for good. Recordings are capped in size and pruned after 30
days, except for high severity and tagged releases. The folder is outside git unless the owner chose
to commit it at setup. When a pull request exists, the text is also posted there.

Evidence is tied to one commit: a new commit makes it stale, as with the existing proof file.

## 8. Environments

Local, staging or production: whichever hosts the owner names in the config. Secrets, tokens,
cookies and emails are redacted before anything is written. On a host marked production, read-only
cases run freely; a case that writes (a migration, a request that changes data, anything that can
spend money) stops and asks the owner for a go on that run.

## 9. Setup

One command reads the repo (language, test runner, how the app starts, which surfaces exist), writes
the config, lists each missing tool with its exact install command, installs only on a yes, and ends
by producing one sample evidence page. It never asks for or stores keys. Run later, it is the health
check.

# Gates, modes and keeping checks out of reach

## Modes

```toml
[gates]
fresh = "observe"      # real-app proof for this exact commit
laws = "observe"       # every new test names a law
red_first = "observe"  # a bug test fails on the old code
seals = "enforce"      # sealed tests do not change
verified = "observe"   # a "Verified:" trailer on every commit
```

- **off** skips the gate.
- **observe** prints `agent-check observe mode, would refuse (not blocking)` and appends a line to
  `.git/agent-check-observe.log`. For `verified`, it also stamps `Verified: none` on the commit, so
  `git log` can find it.
- **enforce** refuses.

These always enforce, whatever the config: a credential in the diff, an untracked file beside a staged
one, a push behind upstream, uncommitted files at push, and a failing suite.

Roll out a gate in this order: observe for a week, read the log, fix each false positive (in the check,
not with an exception), then enforce. A gate that blocks good work trains people to bypass it.

## The Verified trailer

```
git commit -m "Fix rounding in totals" --trailer "Verified: verify skill 14/14 PASS, read both screenshots"
git commit -m "Fix typo" --trailer "Verified: none, docs only"
```

In enforce mode, a missing trailer or a bare `Verified: none` is refused, at commit by the
`commit-msg` hook and again at push and in CI for every non-merge commit pushed, so `--no-verify`
does not skip it. Merges, fixup/squash commits and reverts (git's "This reverts commit <sha>" line)
are skipped. Commits made outside your hooks (a host's revert or squash-merge button, a bot) have no
trailer, so under enforce CI refuses them: add the trailer in the merge message or keep `verified`
on observe. The `fresh` proof
is checked only locally: CI has no screenshots. The trailer is the author's claim; the proof file (`fresh`) is the
evidence. `agent-check audit` lists the last 30 days of commits that had none.

## Changes cannot edit their own checks

| Layer | What protects it |
|---|---|
| Sealed tests | fingerprint in `.sealed-tests`; a change must come with its law's change |
| LAWS.md | shown at every commit and push; owner-only by rule |
| The checker and its config, in CI | `git show $BASE:scripts/agent-check` and `--config-from $BASE`: the base commit judges the PR |
| The CI workflow file, `LAWS.md`, `.sealed-tests` | **not covered by the checker**: the workflow runs from the pushed commit and the laws are read from it. Use branch protection with the CODEOWNERS file `install.sh --github` adds, and read every change to them |
| Evidence (`evidence` gate) | severity is recomputed from paths and the base's config, and the proof hashes the page; local only, see `references/evidence.md` |
| Local hooks | run from the working tree; a local user can always bypass them. CI is the gate that counts |

A PR that legitimately changes the checker is judged by the old checker. That's the point: the new
version applies from the next PR.

## Questions triggered by the diff

```toml
[[question]]
paths = ["billing/", "webhooks/"]
ask = "Can a retry, restart or duplicate webhook charge or grant twice? (incident 2026-03-02)"
```

Printed by `agent-check commit` only when a staged path matches, so the 3 to 10 that apply get read
instead of a list of 40 getting skimmed. Each question should name the incident it came from. Delete
one that never fires: `audit` names a question whose paths match no tracked file, and
`git log -- <paths>` shows how often its paths change.

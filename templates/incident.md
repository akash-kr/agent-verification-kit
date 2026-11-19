# YYYY-MM-DD: <what users saw, in one line>

- **What happened:** what users saw, from when to when, how many.
- **The change that caused it:** commit or PR.
- **Why no check caught it:** which check should have, and why it did not.
- **What now holds it** (pick one or more, cheapest first):
  - a law in LAWS.md with what holds it (architecture, type, lint, test)
  - a `[[question]]` in agent-check.toml with the paths that trigger it
  - a review-eval case in evals/review/ with a one-sentence answer key
- **Rollback used:** the command.

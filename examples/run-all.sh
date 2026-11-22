#!/usr/bin/env bash
# Runs every example and refreshes docs/examples/, which the README and the project page show.
# Each example's terminal output is kept as run.txt beside what it recorded. Stops at the first failure.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
for name in api-bug-fix ui-change bug-test sealed-test missing-evidence stale-proof; do
  printf '\n\033[1m== %s\033[0m\n' "$name"
  log="$(mktemp)"
  bash "$here/$name.sh" 2>&1 | tee "$log"
  # plain text for the page: no colour codes, no throwaway-folder paths
  sed -E $'s/\x1b\\[[0-9;]*m//g' "$log" | sed -E 's#(/private)?/var/folders/[^ ]*/T/tmp\.[A-Za-z0-9]+/#<tmp>/#g' > "$here/../docs/examples/$name/run.txt"
  rm -f "$log"
done
# the page reads this list to find each example's files
python3 - "$here/../docs/examples" <<'PY'
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
files = {d.name: sorted(str(f.relative_to(d)) for f in d.rglob("*") if f.is_file()) for d in sorted(root.iterdir()) if d.is_dir()}
(root / "index.json").write_text(json.dumps(files, indent=1) + "\n")
PY
printf '\nAll examples ran as described. Outputs: docs/examples/\n'

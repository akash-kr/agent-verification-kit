#!/usr/bin/env python3
"""record.py: run demo/run.sh in a pseudo-terminal and save what it prints, with timing, as an asciicast v2
file (demo/receipts.cast). The landing page and the video play this file, so they show the real run.

  python3 demo/record.py [out.cast]
"""
import json
import os
import pty
import select
import subprocess
import sys
import time
from pathlib import Path

here = Path(__file__).resolve().parent
out = Path(sys.argv[1]) if len(sys.argv) > 1 else here / "receipts.cast"
cols, rows = 100, 30

leader, follower = pty.openpty()
os.set_blocking(leader, False)
env = {**os.environ, "TERM": "xterm-256color", "COLUMNS": str(cols), "LINES": str(rows)}
proc = subprocess.Popen(["bash", str(here / "run.sh")], stdin=follower, stdout=follower, stderr=follower, env=env)
os.close(follower)

start, events = time.monotonic(), []
while True:
    ready, _, _ = select.select([leader], [], [], 0.2)
    if ready:
        try:
            chunk = os.read(leader, 65536)
        except OSError:
            break
        if not chunk:
            break
        events.append([round(time.monotonic() - start, 3), "o", chunk.decode(errors="replace")])
    elif proc.poll() is not None:
        break
proc.wait()
if proc.returncode != 0:
    sys.exit(f"record: demo/run.sh exited {proc.returncode}; nothing saved")
header = {"version": 2, "width": cols, "height": rows, "timestamp": int(time.time()),
          "title": "Receipts: an agent tries to fake a green build", "env": {"TERM": "xterm-256color"}}
out.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in [header, *events]) + "\n")
print(f"saved {out} ({len(events)} events, {events[-1][0] if events else 0:.1f}s)")

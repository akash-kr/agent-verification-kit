# Receipts film: spec (storyline A, "The receipt prints")

GOAL:    A developer who lets agents push sees a fake green build refused twice, the honest fix go
         through, then four kinds of evidence an agent must show, and leaves knowing "the push gets a receipt".
OUTPUT:  HyperFrames, 1920 x 1080, 30 fps. Rendered to new files (docs/assets/receipts-film.mp4);
         the current receipts.mp4, .gif and poster stay until the owner swaps them.
TIME:    56 s = 1680 frames.
SOUND:   none. The film is silent.

LOOK
- Ground: slate #3E4A5C, flat, no gradient, no texture. White on it: contrast 9.0:1.
  Chosen over graphite (the dark terminal sinks into it) and teal (too close to the green stamps).
- Paper: thermal white #FFFFFF, ink #1C1B19, dim ink #5C5F66, a zigzag torn edge, shadow
  0 18px 24px rgba(8,18,70,.35). Red #C62828 only for refusals, green #1A7F37 only for passes.
- Terminal: #121317 window, radius 16, three dots, text #E6E8EC, prompt `$` #8B93A1,
  `agent ›` #F2C14E, refused lines #FF8A80, ok lines #7EE2A0.
- Type: Archivo Black (titles, stamps), IBM Plex Mono (terminal, paper). Nothing under 28 px while
  it is meant to be read. Titles 76 px white; the name 230 px; terminal and receipts 28 px;
  evidence paper 30 px, section heads 64 px.
- Stamps: Archivo Black 68-72 px, 8 px border, radius 12, rotated -8..6 deg, ink-speckle mask,
  multiply, always on blank paper at a receipt's foot, never over a line of output.
  REFUSED in red on the guard receipts; PUSHED in green, one per push, never one PASS for many.
- The mark: docs/assets/logo-dark.svg, never redrawn.

OBJECTS
- Terminal window (the agent's session), left.
- Printer slot: a #2A3341 bar 720 x 34, bottom right; receipts rise out of it.
- Receipts: one per push, header `$ git push`, a dashed rule, the kit's verbatim output.
- The evidence roll: four separate receipts, one per example, each with its real task, commit and
  closing line, separated by slate gaps.

MOTION
- Print: the paper rises one row (42 px) per step, 0.07 s power2.out, 0.09 s apart.
- Typing: clip-path steps() reveal at the line's characters-per-second.
- Stamp: scale 1.4 -> 1, opacity 0 -> 1 in 0.12 s power4.in, the paper jolts 6 px.
- Tear: receipt whips off frame in about 0.37 s power3.in with 10 px blur (up, then right).
- Titles: per-word blur 6 px -> 0 in 0.13 s, 0.07 s apart; exit blur out 0.18 s. Landed titles still.
- Camera on the roll: power2.inOut, at most 0.45 s, only ever up the paper.

SHOTS
1. 0.0-7.8 Skip. "Your agent said all tests pass." The agent skips the failing test, OK (skipped=1),
   pushes; the receipt prints the [test-skipped] refusal; REFUSED at 3.9.
   Title -> "It skipped the one that failed." Out: the receipt tears off upward.
2. 7.8-15.4 Key. "A key, deleted a commit later". Commit refused, the agent plans --no-verify and
   deletes the key, pushes; the receipt prints [secret-history]; REFUSED at 11.95.
   Title -> "Gone from the files, not history". Out: the receipt tears off to the right.
3. 15.4-23.2 Honest fix and the name. "The honest fix goes through". Tests OK, push, the receipt
   prints the green line; PUSHED at 17.4. 19.35: the terminal leaves, "Receipts" lands with
   "checks every push an agent makes." 22.45: the receipt grows to fill the frame.
4. 23.2-49.3 Evidence, on the paper. "It has to show evidence", then four receipts print in the
   page's tab names: Before and after (30.0 vs 36.0), Screenshots and video (the real recording
   plays, the phone screenshot, requests 3 / failed 0 / page errors 0), A test that fails first
   (old code 0 passed 1 failed, this commit 2 passed 0 failed), Proof for this commit (the proof
   file, glossed). Each ends with the script's own "✓ pushed" line and a PUSHED stamp.
5. 49.3-50.7 Pull back: the roll shrinks to the right, slate returns.
6. 50.2-56.0 End card: the mark prints row by row (17 steps, 0.75 s), the repo URL and
   `demo/run.sh` land, hold.

BANNED: dark void ground, glow, particles, gradients, glass, cream paper with serif, small caps
labels, everything centred, everything fading and sliding up, titles that move after landing,
three cards in a row, the logo docked in a corner, any line the real runs did not print.
Labels the film adds (a "commit" prefix on a real hash, "LAWS.md" before B1, the ← notes) carry
only facts from docs/examples/*/run.txt and evidence.md, set apart in dim ink or a second typeface.

QA: frames 0, 3.95, 4.6, 7.78, 12.4, 15.18, 17.6, 20.6, 22.75, 23.25, 26, 32.1, 36.4, 42.9, 47.6,
50.5, 56. Each shows real output only, nothing clipped, reading text >= 28 px, titles inside the 80% box.

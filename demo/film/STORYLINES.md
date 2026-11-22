# Receipts demo film: three storylines

The one thing to remember: an agent can't push a fake green build; it has to show its receipts.
The spine in all three: one agent, one task ("a 10% coupon on a $40 cart"), the same real shop and the
same real outputs as `demo/run.sh` and `examples/`. Guard first, then the evidence.

## A. The receipt prints (recommended: the brand's own object carries the whole story)

- **Device and form:** one object across the story (a till receipt), as an object-to-object chain.
  Every push prints a receipt out of the agent's terminal; the receipt is what the viewer follows.
- **What the viewer sees and feels:** each time the agent cheats, its push prints a slip that gets
  stamped REFUSED, with the kit's real refusal line on it. The honest push prints a long receipt
  that unrolls into its evidence: the old code's `{"total": 30.0}` against `{"total": 36.0}`, the
  browser recording of the cart going $40 → $36, the phone screenshot, the test failing on the old
  code, then PASS.
- **First two seconds:** the terminal reads `agent › All tests pass. Done!`; a slip feeds out under
  it and at 1.6 s a red REFUSED stamp lands on it.
- **Beats:** hook (fake green, REFUSED) → tension (the key slipped into history, REFUSED) → reveal
  ("Show the receipt", the name) → proof (before/after, video, screenshots, test fails first, proof
  for this commit, each a section of the unrolling receipt) → payoff (PASS stamp, the push goes
  through) → claim → end card (the mark printed like a receipt header, `demo/run.sh`).
- **Look:** the landing page's grey ground, white thermal-paper slips, mono type, red and green
  stamps, the page's own receipt edge.
- **Sound:** a quiet steady beat; a thermal-printer chatter on each print, a stamp thud on each
  verdict.

## B. Two pushes

- **Device and form:** life before and after, as a split screen that collapses to one.
- **What the viewer sees and feels:** two identical terminals, the same agent, the same skipped test,
  both suites green. On the left the push ships and the real cart charges $30; on the right Receipts
  refuses it, and the honest version comes back with its evidence. The left side fades out and the
  right one fills the frame.
- **First two seconds:** two terminals side by side type `git push` at once; both print
  `OK (skipped=1)`.
- **Beats:** hook (twin green builds) → tension (left: the $30 cart in the browser) → reveal (right:
  REFUSED, the name) → proof (the evidence types on the right, one per beat) → payoff (collapse to
  the right side, PASS) → claim → end card.
- **Look:** neutral light grey, two equal panes, the cart's own white UI, red only on the shipped
  bug, green only on PASS.
- **Sound:** two layers of the same beat; the left one detunes when the bug ships.

## C. The agent's word against the receipt (the bold one)

- **Device and form:** type carries the argument, cut on the beat.
- **What the viewer sees and feels:** the agent's own claims fill the screen in giant type ("All
  tests pass." "Done!"), and each is hard-cut against the kit's real refusal in a full-bleed red
  slab. Then the evidence answers in full-bleed real artefacts, one per beat: `30.0` becomes `36.0`,
  the cart video, the failing test, the proof hash.
- **First two seconds:** black-on-white "All tests pass." in type that fills the frame, cut on the
  first beat to red: "refused: test_coupon is switched off".
- **Beats:** hook (the claim) → tension (claim vs refusal, three times) → reveal (the name) → proof
  (the artefacts on the beat) → payoff (PASS) → claim → end card.
- **Look:** white and the page's ink, one red, one green, the page's display face at full width.
- **Sound:** a driving beat, cuts on the kick.

# Receipts film: review (2026-11-22)

`hyperframes check`: ok, 0 errors. Seven warnings, each looked at in the frames:

| Warning | Where | Verdict |
|---|---|---|
| contrast_aa_failure x3 | first receipt at 3.1 s | Rows still below the printer slot, hidden by the window's clip, measured against the ground. Not visible. |
| line_unread x2 | page 3 of the terminal, 19.2 s | Not a flash: frames at 17.6, 19.15, 19.25 and 19.35 s show the lines up from 15.45 s and leaving with the terminal's 0.35 s blur-out at 18.95 s. |
| text_below_floor | the roll at 49.75 s | Intended: the pulled-back roll is a picture of four receipts, not text to read. |
| nested_media_start_basis_ambiguous | the recording | Its start (9.0 s) is local to the evidence scene, as meant; frames at 32.1 / 32.4 / 36.2 / 36.4 s show it plays in place ($40 -> $36). |

Fixed during review:
- Start states leaked: every title and receipt showed at frame 0. Each tween now applies only when it starts.
- Titles overlapped while one swapped for the next: the second and fourth start 0.12-0.15 s later (frames 4.5, 12.3, 12.7 clean).
- Stamps covered output (REFUSED on the "Fix:" lines, PUSHED on "2 tests ran", the evidence stamps on each
  closing line): every stamp now sits on blank paper at its receipt's foot; zoomed frames at 5.0, 13.5, 18.0,
  42.9 and 47.6 s show every line of output whole.
- Bar label 26 px -> 28 px (the floor).
- The last receipt's lines left 0.1 s before they could be read: printed 0.3 s earlier, pull-back 0.5 s later.
- Sound removed at the owner's request (2026-11-22): the film is silent.

Labels the film adds to real output ("commit" before a real hash, "LAWS.md" before B1, three ← notes) were
checked against docs/examples/*/run.txt and ui-change/evidence.md; SPEC.md now names them.

Seams: 23.2 s (white flood -> evidence paper) has no visible cut; at 50.2 s the roll is still settling on the
right as the mark starts printing on the left, as planned.

Phone sheet (360 px wide): titles, stamps, section heads and the end card read; terminal and receipt body
text is small at that width, as in any 16:9 film watched on a phone.

Not checked: the rendered MP4 itself (no delivery render until the owner approves the preview).

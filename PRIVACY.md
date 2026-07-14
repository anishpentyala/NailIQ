# Privacy policy

NailIQ is a precautionary nail-photo screener, not a medical device, and it
collects as little as it can while still giving you a result and a history you
can look back on. This is what actually happens to your data, matched to the
code that implements it.

## Photos

- Your two photos (side profile, top-down) are sent to the backend, decoded,
  analyzed in memory, and then discarded. **No photo is ever written to disk
  or to the database** - see `backend/app.py`'s `/analyze` route and
  `backend/models.py`'s `ScanRecord`, which has no image column, only
  `findings_json`.
- The annotated overlay box shown on the result screen is computed per-request
  and returned to your browser; it is not saved server-side either.

## What is stored

- **Scan findings.** Each `/analyze` call saves one row (timestamp + the
  findings: labels, verdicts, confidence, no image) to a local SQLite
  database (`backend/nailiq.db`) so the History tab can show past scans and
  the clubbing-angle trend chart. If the save fails for any reason, your
  result is still shown - history logging never blocks a result.
- **Feedback.** If you answer "does this match what you see?" on a finding,
  that response (which finding, the verdict shown, agree/disagree, and an
  optional free-text note) is stored the same way, to eventually help
  calibrate the app's uncalibrated thresholds. Don't put anything identifying
  in the note field - it's stored as plain text.
- **Accessibility/language preferences** (dark mode, high contrast, large
  text, reduce motion, language) are stored only in your browser's
  `localStorage`, never sent to the server.

## What is not collected

No accounts, no names, no email addresses, no device identifiers are
requested or stored anywhere in the app.

## Known limitation

This is a single-deployment prototype, not a multi-user product: `/history`
returns every stored scan to any client that can reach the backend, with no
per-user or per-device separation. That's an acceptable trade-off for a
locally-run or single-instance demo, but it means you shouldn't treat scan
history as private if the backend is ever exposed somewhere multiple people
can reach it. Don't deploy this backend publicly without adding
authentication first.

## Disclaimer

Nothing in this app is a diagnosis. Every finding is only ever "within
typical range," "outside typical range," or "couldn't analyze this photo."
If you're concerned about a nail change, talk to a clinician - this app
cannot replace that.

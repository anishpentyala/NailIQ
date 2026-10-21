# NailIQ - what the app is, and what the UI must contain (design brief)

Written 2026-10-20 from the live code (`frontend/src`) and the project docs. Use it as the spec for a new UI.

## 1. What NailIQ is

NailIQ is a free, mobile-first **precautionary nail-health screener** built for the Congressional App Challenge. You take two
photos of one fingernail (side view and top-down view) and the app returns a result for each nail sign it checks. It is built for
people who do not get regular checkups: some nail changes (pale, spoon-shaped, white, bluish, pitted, banded) show up early in
anemia and in heart, lung and liver conditions but develop too slowly for anyone to notice in the mirror.

**It is never a diagnosis.** Every result for every sign is exactly one of three things:
1. **Within typical range**
2. **Outside typical range** (worth showing a doctor)
3. **Couldn't analyze this photo** (retake guidance)

No condition is ever named as something the user "has". Disclaimers must be on every result screen, not hidden in a footer.

## 2. What it screens for (the app says EIGHT everywhere)

| Sign | In plain words | Validation label |
|---|---|---|
| Koilonychia | spoon-shaped nail (iron-deficiency anemia) | validated |
| Leukonychia | white marks on the nail | validated |
| Cyanosis | bluish or dusky nail bed | validated |
| Onycholysis | nail lifting away from the bed | validated |
| Splinter hemorrhages | tiny dark streaks under the nail | validated |
| Pitting | small dents in the nail surface | validated |
| Onychogryphosis | thick, overgrown "ram's horn" nail (usually a local problem, not systemic) | validated |
| Beau's lines | horizontal grooves (often after illness or stress) | **Limited validation** chip |

Six more signs (clubbing, melanonychia, pallor, Terry's, Lindsay's, Muehrcke's) exist in the engine but are deliberately **not
shown anywhere**; the home screen only says "Six more signs are still being validated and aren't reported yet."
Source of truth: `frontend/src/conditions.js` (`CONDITION_KEYS`); findings are filtered in `frontend/src/api.js`.
Honest framing for the UI: 7 signs met the project's validation bar (>= 60% of real cases caught, <= 5% false alarms on held-out
dataset photos); Beau's lines is shown with a "Limited validation" label (>= 50%). All of it was measured on dataset photos, not
phone photos.

## 3. Non-negotiable rules for any new UI

1. Only the three verdicts above. Never write "you have X", "positive", "negative", "risk score", or a percentage that looks like a
   probability of disease. Confidence is a heuristic, **not** a calibrated probability.
2. Disclaimer on every result screen: *"NailIQ is an educational screening tool, not a medical device. It does not diagnose any
   condition. Always consult a doctor about health concerns."*
3. Never show the six withheld signs. Show "Limited validation" (chip + one-line caution) on any finding flagged
   `validation_tier: "limited"`.
4. Color-based findings carry a skin-tone caveat when `tone_caveat` is present (limited/minimal tone coverage) - show it.
5. Do not store or display photos in history (findings only). Privacy copy says photos are analyzed in memory and discarded.
6. All copy goes through the i18n dictionaries (6 languages: English, Spanish, French, Portuguese, Hindi, Chinese). No hard-coded
   strings. Font sizes in `rem` so "Larger text" works.
7. Accessibility is a feature: dark mode, high contrast, larger text, reduce motion, screen-reader labels, keyboard-reachable
   controls, 44px touch targets.

## 4. Screens and what each must contain

Navigation: **bottom tab bar** (Home, Scan, History, Learn) + a top bar with the title and a settings gear. The camera is
full-screen and hides the tab bar.

### 4.1 Home
- Top bar: "NailIQ", settings gear.
- **Hero card**: illustration (phone scanning a fingernail), headline "Spot nail changes worth a doctor's look", body "Some nail
  signs of anemia, heart, lung, and liver conditions show up early - but develop too slowly to notice on your own. Two quick photos
  check for eight of them.", primary button **Start a scan**.
- **Latest assessment card** (after the first scan): overall status ("All within typical range" / "N signs outside range" /
  "Couldn't analyze this scan"), confidence %, scan ID (NIQ-####), date, up to two measured values. Empty state: "No scans yet -
  Your first result will show up here."
- **How it works** - 3 steps: Side profile, Top down, Get your read ("A clear, non-diagnostic result for each sign").
- **What NailIQ screens for** - the 8 signs, each with icon, name, one-line description; collapsed to 4 with "Show all 8";
  the "six more are still being validated" note under the list.
- **Why it matters** - 3 rows: Anemia, Heart/lung/liver conditions, Too slow to notice. "Built as a free first look for anyone who
  does not get regular checkups - never a replacement for one."
- **Daily tip** (rotating; 7 tips such as plain background, remove polish, frame one finger).
- Footer disclaimer line.

### 4.2 Scan (camera) - full screen, two steps
- Step indicator "Step 1 of 2 / 2 of 2" with labels **Side Profile** then **Top Down**.
- Live camera with a **guide box** (the capture is cropped to this box; bottom of the frame stays open on purpose), per-step
  instruction text: "Hold your finger sideways (profile view) inside the guide box, nail facing the camera. Use a plain background
  that fills the whole frame." / "Now photograph your finger from above inside the guide box, nail facing the camera. ..."
- Controls: close, flash toggle, switch camera, big shutter button, **Upload a photo instead**.
- After each shot: "Checking photo..." (server check). If the photo is unusable show a specific retake message
  (no finger found, blurry, background doesn't fill frame, etc.) and let the user retake only that photo.
- After the top photo: **Select the nail** step - a draggable/resizable box around one nail on the captured photo (move + four
  corner handles), buttons **Use this nail** / **Retake photo**.
- Then "Analyzing..." overlay. Errors: camera blocked, file unreadable, server unreachable.

### 4.3 Results (shown inside the Scan tab after analysis)
Top to bottom:
1. **Summary banner**: "Everything looks within the typical range." / "1 sign is outside the typical range." / "N signs are outside..."
   / "We couldn't analyze this scan - try retaking your photos."
2. **Scan dashboard**: "How sure we are" (Low/Some/High, with "Not a diagnosis or risk score."), "Worth following up" count, signs
   unread count, **Photo quality** (Good/Fair/Poor with issues: blurry, glare, nail polish; which photo).
3. **Nail diagram** (simplified illustration of where each flagged sign shows up - labelled "not a photo of your nail").
4. Your **top-down photo** with toggles: *Measured area* (box the color checks used) and *AI attention* (heat map) with captions.
5. **Finding cards**, grouped: **Worth a closer look** (outside), **Within typical range**, **Couldn't analyze**. Each card:
   icon, sign name, verdict label, one-sentence explanation, evidence badge (Color check / AI model / Color + AI / Geometry + AI),
   **Limited validation** chip + note when applicable, skin-tone caveat when present, "AI model's closest visual match" line,
   an agreement note ("The color check and the AI model agree on this"), a short "what it looks like" summary, and for
   couldn't-analyze cards the specific retake reason.
6. Per-card feedback: "Does this match what you see?" Yes / No (+ optional note), then "Thanks - that helps us improve."
7. **Next steps** (changes with outcome): outside -> show a doctor (primary-care or dermatologist) and use Save/print;
   inconclusive -> retake in brighter even light; all within -> nothing to act on, rescan monthly.
8. Buttons: **Save / print report** (report titled "NailIQ Nail Health Screening Report"), **Scan again**.
9. Disclaimer + "Method & honesty" source note (what each check is based on, thresholds are not clinically calibrated).

### 4.4 History
- Intro: "Nails grow about 3 mm per month... A monthly rescan makes a trend visible."
- One card per past scan: overall status, date, a **Changed** badge when any sign's verdict differs from the previous scan,
  and a row per sign (Within / Outside / Inconclusive). Expandable detail: measured values, confidence score, "fused" notes.
- Example scans (labelled "Example") shown until the first real scan. Empty/loading/error states.
- No images, ever. (The clubbing-angle trend chart exists in code but is hidden because clubbing is withheld.)

### 4.5 Learn
- Intro "NailIQ screens every photo for all of these signs. Tap any one to learn..." then a list of the 8 signs.
- Detail page per sign: name, one-line summary, a lead paragraph, and four sections: **What it looks like**, **Why it happens**,
  **How NailIQ checks it**, **What to do with your result**. Each with an icon.

### 4.6 Settings (bottom sheet) and Privacy (sheet)
- Language (6), Dark mode, High contrast, Larger text, Reduce motion, note "saved on this device", link to Privacy policy.
- Privacy: your photos (analyzed in memory, discarded), what is stored (findings only, local), what is not collected (no accounts,
  names, emails, device IDs), known limitation (single-deployment prototype, history is not per-user), and the no-diagnosis line.

## 5. Data the UI receives (so the design can use it)
`POST /analyze` -> `{ findings: [...], scan_id, image_quality, skin_tone, ... }`. Each finding has: `label`, `display_name`,
`verdict` (within | outside | inconclusive), `confidence` (heuristic 0-1), `track_used` (geometric | fused | color | color_fused |
appearance), `agreement`, `failure_reason` (e.g. nail_region_unclear, blurry, low_confidence), `validation_tier` ("limited" or
absent), `tone_caveat`, `skin_tone_band`, optional `value`/`unit`, and `ml` / `color` sub-objects. `GET /history` returns past scans
(findings only). `POST /feedback` records Yes/No per finding.

## 6. Visual language (current)
Mobile-first (design at ~390x844), calm medical-but-friendly tone, teal-green primary (`#2f7d6b`), warm amber for "worth a
closer look" (`#b8893f`), muted red only for hard errors (`#b4493f`), light and dark themes, iOS-style large title and glass
tab bar, rounded cards (14-26px radii), subtle motion that respects Reduce motion. Icons are a small custom set (finger, spoon,
sparkle, search, clipboard, eye, pulse, info, history, camera). Never use red/alarm styling for "outside typical range" - it is a
prompt to see a doctor, not an emergency.

## 7. Moments worth designing well
- First-run experience and the guide-box camera (the biggest source of bad results is photo quality).
- The "couldn't analyze" state: it must feel helpful (what went wrong, how to retake), not like an error.
- The "outside typical range" state: calm, specific next step, printable report for the doctor.
- Making "Limited validation" and the skin-tone caveat visible without scaring the user.
- A judge-friendly "how we know" surface (validation badge, honesty note) - this app's credibility comes from what it admits.

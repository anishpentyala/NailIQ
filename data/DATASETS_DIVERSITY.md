# Skin-tone diversity: data sourcing

`ml/eval/audit_skin_tone.py` showed our primary training data (NailCheck / KNM,
Roboflow Universe) is heavily skewed toward light skin: of the ~430 images where a
skin region is even measurable, ~59% fall in the lightest ITA band and the darker
bands are thin and noisy. The color findings are therefore largely **unvalidated on
darker skin tones**. This file tracks the datasets we use or could use to close that
gap. Anything CC BY must be credited per [`ATTRIBUTION.md`](../ATTRIBUTION.md) (the
git-tracked attribution record; `data/raw/LICENSES.md` is gitignored).

## Integrated

### Ghana fingernail-anemia set  (`data/raw/fingernails-ghana-anemia`)
- **What:** 4,260 tight nail-plate crops from a Sub-Saharan (predominantly
  darker-skinned) cohort, labelled anemic / non-anemic in the filename, collected with
  Hb values, age, sex per subject.
- **Source:** "Detection of Anemia using Colour of the Fingernails Image Datasets from
  Ghana," Asare, J.W., Appiahene, P., & Donkoh, E. (2022). Mendeley Data, Version 1,
  DOI [10.17632/2xx4j3kjg2.1](https://data.mendeley.com/datasets/2xx4j3kjg2/1).
  **License: CC BY 4.0.**
- **How we use it:** folded into the color-CNN dataset by
  `scripts/build_color_classification_dataset.py` - anemic → a new `pallor` class
  (which previously had *no* CNN backing), non-anemic → darker-cohort `healthy`
  examples. Split is patient-grouped (by finger id) so no subject straddles
  train/valid/test (verified: zero overlap). This both gives `pallor` a real signal
  and broadens the model's skin-tone exposure.
- **Caveat:** these are nail-plate crops with no surrounding skin, so they can't be
  measured by the ITA audit (which needs a finger silhouette) and can't calibrate the
  classical skin-relative `pallor` heuristic. They help the *CNN*, not the classical
  track.

## Candidate next sources (not yet integrated)

Listed roughly by usefulness for *nail* + skin-tone diversity. Verify license before use.

1. **Companion Ghana sets (same group).** Conjunctiva
   ([10.17632/nt7r8hv2pz.1](https://data.mendeley.com/datasets/nt7r8hv2pz/1)) and palm
   images for anemia - same darker cohort. Not nails, but useful if pallor screening
   ever expands beyond the nail plate.
2. **Hemoglobin/skin+nail set - RESOLVED, not usable.** "Dataset of human skin and
   fingernails images for non-invasive haemoglobin level assessment" (Yakimov,
   Buiankin et al., *Scientific Data* 2024) - tracked down to its actual host,
   [Figshare](https://springernature.figshare.com/articles/dataset/Dataset_of_human_skin_and_fingernails_images_for_non-invasive_haemoglobin_level_assessment/25867432)
   (250 patients, full finger-with-skin RGB photos with Hb values and Fitzpatrick
   labels: 90 FP-I, 89 FP-II, 44 FP-III, 21 FP-IV, 6 FP-V, **zero FP-VI**). Blocked
   for two independent reasons, either one sufficient alone: (a) licensed
   **CC BY-NC-ND 4.0** - the No-Derivatives clause is a firmer, more explicit block
   than arthitaya's "Unknown" ever was, since training a model on it and shipping the
   resulting weights is arguably creating a derivative work; (b) it only contains
   healthy fingers labeled by Hb level, no disease-condition labels at all, so even
   with a compatible license it couldn't help any condition besides pallor/healthy
   exposure - and it still wouldn't reach FP-VI. Do not integrate this without
   re-reading the license terms directly (not secondhand) and confirming NC-ND
   doesn't apply to the intended use.
3. **Derm1M** (ICCV 2025) - million-scale vision-language dermatology set that
   *includes* nail conditions (koilonychia, onycholysis, clubbing, onychomycosis).
   Large; would need filtering to nail classes. Paper:
   openaccess.thecvf.com/content/ICCV2025 (Yan et al., "Derm1M").
4. **PASSION** (arXiv 2411.04584) - pigmented skin images from Sub-Saharan Africa,
   purpose-built to close the dermatology diversity gap. Skin-disease focused; mine for
   any nail/finger imagery and as a dark-skin distribution reference.
5. **DDI - Diverse Dermatology Images** ([ddi-dataset.github.io](https://ddi-dataset.github.io/))
   - first expertly-curated, pathology-confirmed set spanning Fitzpatrick I–VI.
   Skin lesions, not nails, but the canonical reference for *measuring* per-tone
   performance and for a dark-skin pretraining signal.
6. **17-class nail disease set** (Springer, "Identification of nail diseases using
   DenseNet169…", 2025) - explicitly supplemented with photos across different skin
   tones; includes clubbing/koilonychia. Check the paper for a download link.

## Data search log: melanonychia / onycholysis / splinter_hemorrhages / mees_lines

These four were the color CNN's thinnest classes (test-set n of 6, 24, 18, 10
respectively), which makes their precision/recall numbers unstable regardless of
threshold tuning. Re-searched Kaggle + Roboflow Universe (mid-2026) specifically for
more coverage before assuming nothing exists:

- **Nikhil Gaurav's "Nail Disease Detection"** (Kaggle, CC BY-NC-SA 4.0, usability
  7.5) - real, clearly-licensed, actively used dataset, but its 6 classes
  (acral_lentiginous_melanoma, healthy_nail, onychogryphosis, blue_finger, clubbing,
  pitting) don't add anything: blue_finger/pitting duplicate conditions we already
  have well-covered, the rest are discrimination-only. Not integrated.
- **Joseph Rasanjana's "Nail Disease Image Classification Dataset"** (Kaggle) - only
  3 unlabeled classes, "Unknown" license, usability 3.13/10, no description. Too low
  quality/too opaque to be worth the licensing risk for unknown gain. Not integrated.
- The "3,835-image" and "723-image" Kaggle sets referenced in two 2025-2026 papers
  turned out to be **the same underlying data as `data/raw/nail-disease`**, already
  integrated - not new sources.
- The Springer "17-class... DenseNet169" paper (already tracked above as a
  skin-tone-diversity candidate) is the closest lead for onycholysis/splinter
  coverage specifically, but no public download link has been found yet - would need
  contacting the authors.

**Conclusion: no additional usable, clearly-licensed data was found for these
classes.** This looks like genuine scarcity in publicly available nail-condition
datasets, not a search-effort gap - re-run this search periodically rather than
assuming it's been exhausted forever, but don't expect a quick win here.

**Update: `data/raw/nail-dataset-arthitaya` (melanonychia's only-ever CNN training
source, and mees_lines' only source at all) was removed from
`scripts/build_color_classification_dataset.py`.** Its Kaggle license was "Unknown" -
a real, unresolved legal blocker for any model whose weights might be shared or
shipped, not a caveat that could stay indefinitely in a code comment. melanonychia is
back to classical-heuristic-only (`ml/infer/melanonychia.py`); mees_lines (a
discrimination-only class with no app finding) is dropped entirely. This trades away
melanonychia's CNN backing to close the actual legal exposure - re-integrate only once
a permissively-licensed melanonychia source is found, not before.

## Honest status

Finding and folding in the Ghana data is real progress - the color CNN now sees a
darker-skinned cohort and `pallor` has data - but it does **not** by itself prove the
model is accurate on dark skin. That requires (a) retraining the color ensemble on this
expanded set and (b) a per-tone-band eval on real held-out photos. The retrain is wired
(`discover_classes()` picks up `pallor` automatically; `APP_CONDITIONS` lists it); the
per-tone eval still needs darker-skin finger-with-skin photos we don't yet have (sources
2 and 6 above are the path).

Re-checked mid-2026 for anything new: **Derm1M** (CC BY-NC-4.0, 1M image-text pairs) is
real and downloadable, but it's a general-dermatology set (390 conditions, YouTube/forum/
PubMed-sourced) with no confirmed nail-specific subset - mining it for nail images would
be its own multi-day project with an uncertain yield, not a quick integration. Fitzpatrick17k
and its "Black Skin" Kaggle spinoff are skin-lesion datasets, not nail-plate images, so they
don't feed the pipeline directly (though DDI, above, remains a fine ITA-calibration
reference). **No new nail-specific, darker-skin-tone source became available since the
first pass** - `pallor` is still the only condition with dedicated darker-skin training
data; the other ~10 color conditions remain validated mostly on light skin. This is an
honest, unresolved gap, not one this session could close by searching harder.

**Third search pass:** ran fresh web searches for nail-condition + dark-skin/Fitzpatrick
data and for phone-camera-captured nail datasets. Found and fully tracked down candidate
#2 above (the hemoglobin/skin+nail Figshare set, with real Fitzpatrick I-V labels) -
resolved as **not usable** (CC BY-NC-ND license, no condition labels, no FP-VI anyway),
not just "license unclear" as before - that ambiguity is gone, replaced with a definite
no. The "gts.ai Nail Disease Detection Dataset" result matched the previously-ruled-out
Nikhil Gaurav Kaggle set (same 6 classes) - not new. AnemiaVision (arXiv 2604.22964, a
2026 smartphone-anemia-screening paper) has no accompanying open dataset. **Conclusion
unchanged, now with a third confirming pass**: no usable darker-skin data exists for the
~10 non-pallor color conditions, and no real phone-photo nail dataset (labeled, any skin
tone) was found anywhere. Closing this gap requires generating original photos (a
camera + volunteers across skin tones), not a fourth search.

**Fourth search pass (2026-09-17), also checking a second research AI's leads for accuracy
first:** the same research-AI-provided leads that led us to `nihati`/`anemia` this session
also resurfaced several dead ends without flagging them: "nailsDt1" (confirmed the same
corpus as the removed `nail-disease`), the Nikhil Gaurav/Gurav Kaggle set (license
misreported as CC BY 4.0 - real license is CC BY-NC-SA 4.0, AND its ~3,835-image count
matches the already-confirmed-contaminated corpus above), and Yakimov again (license
misreported as CC0 - we'd already confirmed CC BY-NC-ND 4.0 directly from the host). All
three rejected again on sight, consistent with the pattern above - **do not trust a second
AI's license claim any more than the first; always verify against this file's existing
resolutions before re-evaluating a lead.**

A dedicated follow-up search then targeted six specific new leads:
- **Derm1M** (ICCV 2025) - confirmed real, on HuggingFace (`redlessone/Derm1M`,
  1,029,761 pairs), but CC BY-NC-4.0 (explicitly requires separate permission for
  commercial use) and its full 390-condition list (needed to confirm nail coverage)
  is in supplementary material too large to fetch in this pass. **Not usable without
  a license negotiation, and nail coverage itself is still unconfirmed** - don't treat
  this as a live option without both resolved.
- **PASSION** (MICCAI 2024) - confirmed **no nail/finger imagery at all**: it's
  paediatric eczema/fungal/scabies/impetigo body-lesion photos only. Ruled out
  definitively, not just "unmined."
- **Springer 17-class DenseNet169 paper** - the paper itself (Discover Computing,
  Nov 2025) is real and describes exactly the classes we need, but has no data
  availability statement, GitHub repo, or companion dataset anywhere found - it cites
  *existing* Kaggle sets (likely the same contaminated ones above) rather than
  releasing new data. Would require directly emailing the authors; not a download.
- **Melanonychia, fresh targeted search** - the only paper found using melanonychia
  images (Tan et al., PeerJ 2024) cites arthitaya's Kaggle set (723 images, 245
  melanonychia) - the exact dataset already rejected here for an unresolved "Unknown"
  license. No independent melanonychia source exists anywhere searched (Zenodo,
  Figshare, Mendeley, OSF, GitHub). **This remains a hard zero, not a research gap.**
- **Real phone-camera photos, fresh search** - found two NEW leads, both closed for
  now but worth a future outreach attempt (see Next Actions): a Frontiers 2025 paper
  (909 real smartphone anemia photos, Samsung Galaxy A73, Peru) that states "raw data
  available by request" - not publicly hosted, but a named corresponding author exists
  to ask; and Galmés et al. (2022, Multimedia Tools & Applications) - 348 smartphone
  clinical images for nail-angle/segmentation work, no public release found, same
  request-the-author situation.
- **Lateral/side-profile clubbing photos** - still nothing publicly released anywhere;
  the same Galmés et al. paper above is the closest lead (a 348-image smartphone
  clinical set) but access is unconfirmed and unrequested so far.

**Conclusion, fourth pass:** no new dataset became usable. The gap for melanonychia,
real phone photos, and lateral clubbing photos is confirmed real and not closeable by
searching harder a fifth time. The only two live paths that changed this pass: (a) two
named authors (Frontiers 2025, Galmés et al.) who could plausibly be emailed for direct
data-sharing access - a real, if slow, outreach option, not a dead end like the rest;
(b) accepting these three gaps stay unvalidated on phone photos until original data
collection happens. (Galmés et al. was later ruled out entirely - see below - once their
paper's own text was checked directly.)

**Fifth and sixth passes (2026-09-18/19), institutional/clinical archives instead of
open-data platforms:** two independent research efforts (one agent-run, one a second AI
given the same brief) targeted university/hospital dermatology teaching archives,
national dermatology societies, PubMed Central embedded/supplementary images, NIH's
Open-i biomedical image search, physiotherapy/pulmonology lateral-clubbing education
resources, and LMIC teledermatology programs. **Both produced at least one confident but
false specific claim**, each caught only by direct verification: one pass claimed two PMC
articles were "CC BY licensed, ready to implement" when direct fetch showed one was plain
copyright (no open license) and the other CC BY-NC (not CC BY) with a single patient's
photos; the other pass claimed NIH Open-i had "1 usable CC-BY clubbing photo," which did
not reproduce when the exact search was run through Open-i's actual UI (zero results for
clubbing, melanonychia, leukonychia, onycholysis). Confirmed accurate on independent check:
DermNet NZ's watermarked images are CC BY-NC-ND (NonCommercial + NoDerivatives, the same
license combination that already ruled out Yakimov) - a real, verified dealbreaker, not a
hedge. Also independently confirmed: Galmés et al. (2022) explicitly states in its own
text that its 348-image dataset "belong[s] to the company that conducted the clinical
study" and is not shareable by the authors at all - ruled out as an outreach target,
unlike the still-open Frontiers 2025 lead.

**Conclusion, fifth/sixth passes:** every institutional/clinical archive route is now
confirmed blocked or empty (verified firsthand, not taken on report). This is the sixth
independent search effort overall (four general-platform passes plus these two) to reach
the same result for melanonychia, the tiny-n NIHATI conditions, and real phone/lateral
photos. Stop re-searching this specific question; it is a genuine, thoroughly-confirmed
scarcity. The two live paths remain: author outreach (one sent, to Frontiers 2025,
awaiting reply) and original data collection.

## 2026-10-01 permission and candidate update

The user explicitly authorized KNM despite watermarks and separately confirmed
permission for Arthitaya. This supersedes the earlier permission blocker for
local candidate training. It does not establish public CC licensing, clinical
label correctness or independent patients; permission documents were not inspected.
The record is `data/source_authorizations.json` and attribution is in `ATTRIBUTION.md`.

The isolated `data/raw/goal60_authorized_cls` retains original split membership,
adds 480 supported Arthitaya images, and includes 17 training classes. Mees' lines
and melanoma remain discriminators, not new app findings. Melanonychia has only
3 VALID and 6 TEST images before further adjudication; Lindsay's nails has 6 and
5. These denominators cannot support a robust 60% accuracy claim.

The expanded similarity audit found 84 cross-split candidates involving Arthitaya.
Pixel comparison and visual review confirmed three duplicate pairs, including a
conflicting pallor/melanonychia label. Both sides were quarantined; v3 now excludes
73 crops across the original and expanded pools (TRAIN32, VALID30, TEST11).
Candidate training restarted with that quarantine. Runtime TRAIN crops were copied
and their source rows rechecked against v3; they add no independent patients.

Automated localization and optional user-adjusted nail boxes are being evaluated
separately. Annotation boxes are upper-bound diagnostics, not measured user-crop
accuracy. No new labeled phone cohort or paired geometry benchmark was created.

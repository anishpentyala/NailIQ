# Skin-tone diversity: data sourcing

`ml/eval/audit_skin_tone.py` showed our primary training data (NailCheck / KNM,
Roboflow Universe) is heavily skewed toward light skin: of the ~430 images where a
skin region is even measurable, ~59% fall in the lightest ITA band and the darker
bands are thin and noisy. The color findings are therefore largely **unvalidated on
darker skin tones**. This file tracks the datasets we use or could use to close that
gap. Anything CC BY must be credited per `data/raw/LICENSES.md`.

## Integrated

### Ghana fingernail-anemia set  (`data/raw/fingernails-ghana-anemia`)
- **What:** 4,260 tight nail-plate crops from a Sub-Saharan (predominantly
  darker-skinned) cohort, labelled anemic / non-anemic in the filename, collected with
  Hb values, age, sex per subject.
- **Source:** "Detection of Anemia using Colour of the Fingernails Image Datasets from
  Ghana," Mendeley Data, DOI [10.17632/2xx4j3kjg2.1](https://data.mendeley.com/datasets/2xx4j3kjg2/1).
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
2. **Hemoglobin/skin+nail set.** "Dataset of human skin and fingernails images for
   non-invasive haemoglobin level assessment" - full finger-with-skin images (would
   feed the *classical* pipeline and the ITA audit, unlike the crop-only Ghana set).
   Find via the ResearchGate record (pub. 384572934).
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

## Honest status

Finding and folding in the Ghana data is real progress - the color CNN now sees a
darker-skinned cohort and `pallor` has data - but it does **not** by itself prove the
model is accurate on dark skin. That requires (a) retraining the color ensemble on this
expanded set and (b) a per-tone-band eval on real held-out photos. The retrain is wired
(`discover_classes()` picks up `pallor` automatically; `APP_CONDITIONS` lists it); the
per-tone eval still needs darker-skin finger-with-skin photos we don't yet have (sources
2 and 6 above are the path).

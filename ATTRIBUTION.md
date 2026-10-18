# Dataset attribution

The source registry below records declared licenses and separately reported
permissions. CC BY 4.0 requires crediting the creator, linking the license,
noting changes, and does not imply endorsement. This file is the canonical,
git-tracked attribution record (the
generated `data/raw/LICENSES.md` is gitignored along with the raw data itself,
so this is the copy that ships with the repo).

## Roboflow Universe sources

| Dataset | Creator / workspace | Source | License |
|---|---|---|---|
| NailCheck (`nailcheck-3xvkl`) | nails-btohy | https://universe.roboflow.com/nails-btohy/nailcheck-3xvkl | CC BY 4.0 |
| KNM Nail Disease Detection (`nail-disease-detection-mxoqy`) | knm | https://universe.roboflow.com/knm/nail-disease-detection-mxoqy | CC BY 4.0 |
| LIVERCHECK+ Nail Clubbing (`nail-clubbing`) | livercheck-8v5ig | https://universe.roboflow.com/livercheck-8v5ig/nail-clubbing | CC BY 4.0 |
| Nail Disease Detection (`nail-disease-detection`) | allysoncarmelo07-gmail-com | https://universe.roboflow.com/allysoncarmelo07-gmail-com/nail-disease-detection | CC BY 4.0 |
| Tugas Akhir Nail Disease (`nail-disease`) | tugas-akhir-kx2jl | https://universe.roboflow.com/tugas-akhir-kx2jl/nail-disease | CC BY 4.0 |

**Modifications made:** images from the four detection (YOLO-format) datasets
were cropped to their labeled bounding boxes, padded, size/area-filtered, and
perceptual-hash deduplicated against the eval split before being merged into
the classification training set (`scripts/build_classification_dataset.py`,
`scripts/build_color_classification_dataset.py`). NailCheck's own train/valid/test
split was used as-is for evaluation.

*(`terry-s-nail-cbo00` was attempted but failed to download and is not used.)*

| chaa YOLOv8 Nails Segmentation (`yolov8-nails-segmentation-ckvkd`) | chaa | https://universe.roboflow.com/chaa/yolov8-nails-segmentation-ckvkd | CC BY 4.0 |
| Nail Disease Classification NIHATI (`nail-disease-classification-nihati`) | nihati | Pulled via the Roboflow SDK's public `Project.search()`/`Project.image()` API (no exportable "version" exists for this project) | CC BY 4.0 |
| Anemia Nails Detection (`nails-pceph`, workspace `anemia-hv9cy`, v1) | anemia-hv9cy | https://universe.roboflow.com/anemia-hv9cy/nails-pceph | CC BY 4.0 |

**Modifications (chaa):** segmentation polygons reduced to axis-aligned bounding
boxes, cropped/padded like the detection sources above, then re-split by image
stem (its own split isn't leakage-audited against ours) - see
`scripts/build_color_classification_dataset.py`. Vetted 2026-09-15 (EXIF/
filename-regex/OCR/corner-watermark audit, 0 confirmed contamination) after
replacing the removed `data/raw/nail-disease` source for splinter_hemorrhages.

**Modifications (NIHATI):** already in folder-classification form
(`<split>/<slug>/`); re-split by image id via `bucket_split` since its own split
wasn't leakage-audited. Vetted 2026-09-16 (same audit battery, 0 confirmed
contamination). Restores leukonychia/onycholysis/lindsays_nails CNN coverage
lost when `nail-disease` was removed.

**Modifications (anemia):** only the `anemic_nail` class's boxes are used
(mapped to `pallor`); the dataset's other classes (tongue photos) and its
unlabeled background images (some traceable to Pexels/Unsplash by filename,
not used here) are excluded. Cropped/padded like the detection sources above,
re-split by source-photo key (stripping the Roboflow augmentation suffix) to
keep augmented copies of one photo in one split. Vetted 2026-09-16.

## Ghana fingernail-anemia set

**Detection of Anemia using Colour of the Fingernails Image Datasets from Ghana**
Asare, J.W., Appiahene, P., & Donkoh, E. (2022). Mendeley Data, Version 1.
DOI: [10.17632/2xx4j3kjg2.1](https://data.mendeley.com/datasets/2xx4j3kjg2/1)
License: **CC BY 4.0**

**Modifications made:** images were split by patient/finger id (not by image)
into train/valid/test to prevent subject leakage, then labeled `pallor`
(anemic) or `healthy` (non-anemic) for the color-condition CNN
(`scripts/build_color_classification_dataset.py`). See
[data/DATASETS_DIVERSITY.md](data/DATASETS_DIVERSITY.md) for why this dataset
was added (broadening skin-tone coverage; see `ml/eval/audit_skin_tone.py`).

## Han onychomycosis nail image set (Figshare)

**Han, S.S. et al. (2018).** Onychomycosis nail image datasets (Figshare),
DOI [10.6084/m9.figshare.5398573](https://doi.org/10.6084/m9.figshare.5398573).
License: **CC BY 4.0** (as recorded when downloaded 2026-10-16; confirm on the Figshare record).

**Modifications made:** the dataset is montage sheets by class; individual nails were
cropped, rotated tip-down (`scripts/tag_nail_orientation.py`), filtered to crops whose
labeled sign is visible (`scripts/filter_han_visible_signs.py`), exact/near duplicates
removed, and the `onycholysis` and `normalnail` classes used to train the onycholysis
specialist (`scripts/train_onycholysis_specialist.py`). **The watermark/OCR audit applied
to the Roboflow sets has NOT been run on this set** (deferred by the project owner).

## Permission-authorized candidate data (2026-10-01)

The user explicitly confirmed permission to use KNM despite image watermarks and
separately confirmed that permission covers Arthitaya's Kaggle Nail dataset
([source](https://www.kaggle.com/datasets/arthitaya/nail-dataset)). Arthitaya's
public license remains recorded as Unknown; user-reported permission is a
separate basis, not a replacement public license. Permission documents were not
independently inspected. See `data/source_authorizations.json`.

Arthitaya's community classes are inherited as appearance labels: black line to
melanonychia, white spot to leukonychia, onycholysis, Beau's lines, Terry's nails,
clubbing and normal; Mees' lines is a training discriminator, not an app finding.
Original hash splits are retained. Files are copied into an isolated candidate;
they are not relabeled or redistributed here. No clinical adjudication is implied.

Three additional cross-split duplicate families were visually confirmed after
inclusion, including conflicting pallor/melanonychia labels. Both sides are
quarantined by `data/raw/goal60_exclusions_v3.json`; the first training attempt
was stopped and restarted. Similarity hashes alone do not establish duplication.

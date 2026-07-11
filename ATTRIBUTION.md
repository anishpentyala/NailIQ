# Dataset attribution

All training/eval data below is licensed **CC BY 4.0**, which requires crediting
the creator, linking the license, noting changes made, and does not imply
endorsement. This file is the canonical, git-tracked attribution record (the
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

# Model license check (2026-10-24)

Question: may the trained weights in `hf_space_build/ml/models` be published on a public Hugging Face Space?
This is an engineering review of the project's own records plus what could be verified online today. It is not legal advice.
Public Space files can be downloaded by anyone, so putting weights in a public Space **is distribution of the weights**.

## What ships, and what each model was trained on

| Shipped model | Trained on | Declared license | Status |
|---|---|---|---|
| Shape CNN ensemble (`nail_classifier__*`) | NailCheck (nails-btohy), LIVERCHECK+ nail-clubbing, **KNM** (nail-disease-detection-mxoqy) | CC BY 4.0 each (Roboflow) | KNM: see risk 2 |
| Color CNN ensemble (`nail_color_classifier__*`) | **KNM**, Ghana fingernail-anemia (Mendeley), chaa, NIHATI, anemia-hv9cy | CC BY 4.0 each | KNM, NIHATI, chaa: see risk 2 |
| Specialists: onycholysis, leukonychia, Beau's lines | Han onychomycosis set (Figshare), KNM, chaa, NIHATI, **Arthitaya (Kaggle)**, Ghana healthy patches | CC BY 4.0, except Arthitaya | **Arthitaya: see risk 1** |
| Orientation model (`nail_orientation_resnet18`) | Hand-labelled crops from the Han set | CC BY 4.0 (derived) | OK with attribution |
| Backbones (EfficientNet-B0, MobileNetV3-L, ResNet18) | Start from torchvision ImageNet weights | torchvision code BSD-3; weights follow ImageNet terms | see risk 3 |

Verified today: the Han Figshare record (doi 10.6084/m9.figshare.5398573) reports **CC BY 4.0** via the Figshare API.
Not verifiable today: Roboflow pages returned HTTP 403, so the Roboflow licenses are the ones recorded when downloaded.

Correctly excluded (never used for training): Yakimov Hb set (CC BY-NC-ND, evaluation only), Nikhil Gaurav Kaggle set
(CC BY-NC-SA), Derm1M (CC BY-NC), DermNet (CC BY-NC-ND), the earlier `nail-disease` Roboflow set (watermark-contaminated, removed 2026-09-15).

## Risks, most serious first

1. **Arthitaya (Kaggle "nail-dataset") has license "Unknown".** `data/source_authorizations.json` records only the owner's statement that
   permission exists; the permission documents were never inspected. This data trained (or evaluated) the three specialists
   (Beau's lines was trained with it; onycholysis and leukonychia list it among their real-photo sources). Publishing those
   weights publicly means redistributing something derived from data with no confirmed license. The color and shape CNNs do **not** use it.
2. **Roboflow "CC BY 4.0" is declared by the uploader and may not be valid for the underlying photos.** KNM's images carry visible watermarks
   (the owner authorized use despite that), which suggests third-party content. NIHATI is mostly web images (one has a "Health-Room"
   watermark that the earlier audit missed), and the Han set has not had the watermark audit. The declared license cannot be confirmed either way.
3. **ImageNet starting weights.** The ImageNet terms are non-commercial research; whether that reaches fine-tuned models is unsettled.
   Almost every student project starts here; low practical risk for a free educational app, but be aware.
4. **CC BY attribution is required** wherever the models/app are shared: credit the creator, link the license, note changes.
   `ATTRIBUTION.md` has the record; the Space README and the app should point to it.

## Options

- **A. Keep the weights private (recommended).** Put the weights in a *private* Hugging Face model repo; the public Space downloads them at
  startup with a read token stored as a Space secret. Judges can use the app; nobody can download the weights. Needs a token (yours to create/enter).
- **B. Public Space without the Arthitaya-trained specialists.** Ship only the shape and color CNNs. Removes risk 1, keeps 2-4, and Beau's lines / onycholysis /
  leukonychia fall back to the weaker color-CNN path (the 'Limited validation' sign would lose its stronger model).
- **C. Public Space with everything.** Fastest; accepts risks 1-3. Not recommended while risk 1 is unresolved.

In every option: credit the datasets (Space README + app), keep describing the app as an educational screener, and do not publish the
Hb-set or other NC/ND data.

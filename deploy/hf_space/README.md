---
title: NailIQ
emoji: 💅
colorFrom: green
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# NailIQ

A precautionary screener for nail-based signs of systemic disease, made for the Congressional App Challenge.
You photograph one finger (side view and top-down), and for each sign the app reports only
**within typical range**, **outside typical range**, or **couldn't analyze this photo**. It never gives a diagnosis and
is not a medical device. Anything marked outside the typical range is a reason to ask a doctor, not a conclusion.

- Photos are analyzed in memory and are **not saved**. Only the resulting findings are kept, under an anonymous
  random id stored in your browser, and they disappear when this Space restarts.
- On an iPhone: open this page in Safari, then Share > Add to Home Screen to use it like an app.
- Accuracy on real phone photos has not been measured; results come from models trained on clinical photo datasets.

## Credits and licenses

NailIQ's models were trained on openly shared nail-photo datasets. Credit and thanks to their creators (licenses linked;
images were cropped, resized and relabeled for training, and are not redistributed here):

- NailCheck - nails-btohy, CC BY 4.0 - https://universe.roboflow.com/nails-btohy/nailcheck-3xvkl
- KNM Nail Disease Detection - knm, CC BY 4.0 - https://universe.roboflow.com/knm/nail-disease-detection-mxoqy
- LIVERCHECK+ Nail Clubbing - livercheck-8v5ig, CC BY 4.0 - https://universe.roboflow.com/livercheck-8v5ig/nail-clubbing
- chaa YOLOv8 Nails Segmentation - chaa, CC BY 4.0 - https://universe.roboflow.com/chaa/yolov8-nails-segmentation-ckvkd
- Nail Disease Classification (NIHATI) - nihati, CC BY 4.0 - Roboflow Universe
- Anemia Nails Detection - anemia-hv9cy, CC BY 4.0 - https://universe.roboflow.com/anemia-hv9cy/nails-pceph
- Detection of Anemia using Colour of the Fingernails Image Datasets from Ghana - Asare, Appiahene & Donkoh (2022), CC BY 4.0 - https://doi.org/10.17632/2xx4j3kjg2.1
- Onychomycosis nail image datasets - Han et al. (2018), CC BY 4.0 - https://doi.org/10.6084/m9.figshare.5398573
- Nail dataset (Kaggle, arthitaya) - the uploader did not state a license; used only for model training, images not redistributed

CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ . Model weights are not published; they are stored privately and
loaded by this app at startup. NailIQ is an educational screening tool, not a medical device, and never gives a diagnosis.

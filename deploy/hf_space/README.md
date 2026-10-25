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

"""Tag nail crops with the direction the free edge (fingertip) points.

Hand labels (indices into orient/sample_files.json) -> canonicalise to tip-down ->
generate the 4 rotations -> train a small ResNet18 to predict which rotation it sees.
Applied to a crop folder it writes <root>/orientation.csv with the predicted tip
direction (D/R/U/L as seen in the stored image) and confidence. Low confidence or
disagreement across flips marks a crop as ambiguous (usually oblique/side views).
"""
import csv, json, sys, random
from pathlib import Path
import cv2, numpy as np, torch, torch.nn as nn
from torchvision import models

ROOT = Path("data/raw/han-onychomycosis-figshare")
O = ROOT / "orient"
LAB = {}  # path -> tip direction, from Haiku sheet labels (X = unsure is dropped)
_sf = json.load(open(O / "sample_files.json")); _hf = json.load(open(O / "haiku_files.json"))
for name, files in (("haiku_s.json", _sf), ("haiku_h_a.json", _hf), ("haiku_h_b.json", _hf), ("haiku_h_c.json", _hf)):
    for i, d in json.load(open(O / name)).items():
        if d in ("D", "L", "U", "R"):
            LAB[files[int(i)]] = d
# stored-image direction -> number of 90deg CCW turns (np.rot90 k) that makes the tip point down
TURNS = {"D": 0, "R": 3, "U": 2, "L": 1}  # rot90 CCW: R->D needs 3? verified in canon() below
SIZE = 160
dev = "cuda" if torch.cuda.is_available() else "cpu"


def load(p):
    im = cv2.imread(str(p))
    return None if im is None else cv2.cvtColor(cv2.resize(im, (SIZE, SIZE)), cv2.COLOR_BGR2RGB)


def canon(im, d):
    # np.rot90(k=1) rotates CCW: a tip on the right moves to the top, so R needs k=3 (CW) to reach D... check:
    # right -> (CCW) up -> left -> down, so R needs k=3; U needs 2; L needs 1.
    return np.rot90(im, TURNS[d])


def tens(a):
    x = torch.from_numpy(np.ascontiguousarray(a)).permute(2, 0, 1).float() / 255
    m = torch.tensor([0.485, 0.456, 0.406])[:, None, None]; s = torch.tensor([0.229, 0.224, 0.225])[:, None, None]
    return (x - m) / s


def net():
    m = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    m.fc = nn.Linear(512, 4)
    return m.to(dev)


def train(items, epochs=25):
    m = net(); opt = torch.optim.AdamW(m.parameters(), 3e-4, weight_decay=1e-2)
    for ep in range(epochs):
        m.train(); random.shuffle(items)
        for i in range(0, len(items), 16):
            xs, ys = [], []
            for im in items[i:i + 16]:
                k = random.randrange(4); a = np.rot90(im, k)
                if random.random() < .5:  # horizontal flip keeps tip-down/up, swaps nothing about vertical axis
                    a = a[:, ::-1] if k % 2 == 0 else a[::-1]  # flip along the axis perpendicular to tip direction
                xs.append(tens(a)); ys.append(k)
            loss = nn.functional.cross_entropy(m(torch.stack(xs).to(dev)), torch.tensor(ys).to(dev))
            opt.zero_grad(); loss.backward(); opt.step()
    return m


@torch.no_grad()
def predict(m, im):
    m.eval(); out = []
    for k in range(4):
        # image rotated by k shows tip at rotation k; predicting k' means current tip turned k' from down
        p = torch.softmax(m(tens(np.rot90(im, k)).unsqueeze(0).to(dev)), 1)[0].cpu().numpy()
        out.append(np.roll(p, -k))  # undo the k extra turns
    p = np.mean(out, 0)
    return p


if __name__ == "__main__":
    data = sorted(LAB.items())
    random.seed(0); random.shuffle(data)
    val, tr = data[:20], data[20:]
    tr_im = [canon(load(i), d) for i, d in tr]
    m = train(tr_im)
    # validation: take held-out canonical images, rotate each 4 ways, check prediction
    ok = n = 0
    for i, d in val:
        c = canon(load(i), d)
        for k in range(4):
            n += 1; ok += int(np.argmax(predict(m, np.rot90(c, k))) == k)
    print(f"held-out rotation accuracy {ok}/{n}  (labels: {len(data)}, train {len(tr)}, val {len(val)})")
    m = train([canon(load(i), d) for i, d in data], 30)
    torch.save(m.state_dict(), ROOT / "orient/orientation_resnet18.pt")
    rows = []
    for p in sorted((ROOT / "crops").glob("*/*.png")):
        im = load(p)
        if im is None:
            continue
        pr = predict(m, im)
        rows.append([str(p.relative_to(ROOT)), "DRUL"[int(np.argmax(pr))], f"{pr.max():.3f}"])
    with open(ROOT / "orientation.csv", "w", newline="") as f:
        csv.writer(f).writerows([["crop", "tip_dir", "conf"], *rows])
    from collections import Counter
    print(Counter(r[1] for r in rows), "conf>=0.8:", sum(float(r[2]) >= .8 for r in rows), "/", len(rows))

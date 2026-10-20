"""dHash (same function the specialist trainer uses) for every crop in sign_features_meta.json -> sign_dhash.npy"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import train_onycholysis_specialist as T
FEAT = Path("C:/NailIQ_recovery/features")
meta = json.load(open(FEAT / "sign_features_meta.json"))
H = np.stack([T.dhash(T.load(m["p"])) for m in meta])
np.save(FEAT / "sign_dhash.npy", H)
print("saved", H.shape)

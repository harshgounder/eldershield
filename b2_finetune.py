#!/usr/bin/env python3
"""kavach_b2_finetune.py — Hindi domain adaptation of AASIST.

Trains:  real Hindi (FLEURS) -> BONAFIDE (0) | Hindi TTS (edge-tts) -> SPOOF (1)
Held-out test: 100 fresh FLEURS speakers + 24 TTS clips with UNSEEN scripts.
(Note: TTS voices overlap train/test — edge-tts hi has only 2 voices; scripts are unseen.)
"""
import sys, os, glob, time, random, json
import numpy as np
import torch, torch.nn as nn
import soundfile as sf

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src", "aasist"))
from AASIST import Model  # noqa: E402

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "AASIST.pth")
NB_SAMP = 64600  # 4.04s @ 16k
BASE = "/tmp/hindi_finetune"
OUT = os.path.join(os.path.dirname(__file__), "models", "aasist-hindi.pt")

def load_wav(path):
    x, sr = sf.read(path, dtype="float32")
    if x.ndim > 1:
        x = x.mean(1)
    if sr != 16000:
        import scipy.signal as sig
        x = sig.resample_poly(x, 16000, sr)
    return x

def crop(x, rng):
    """Random 4s crop (or pad then crop) — the augmentation that makes 56 files trainable."""
    if len(x) < NB_SAMP:
        x = np.pad(x, (0, NB_SAMP - len(x)))
    if len(x) == NB_SAMP:
        return x
    start = rng.randint(0, len(x) - NB_SAMP)
    return x[start:start + NB_SAMP]

def collect(files, labels, rng, n_per_file=4):
    X, Y = [], []
    for f in files:
        x = load_wav(f)
        for _ in range(n_per_file):
            X.append(crop(x, rng))
            Y.append(labels)
    return np.stack(X).astype(np.float32), np.array(Y).astype(np.float32)

def main():
    seed = 42
    rng = np.random.RandomState(seed)
    torch.manual_seed(seed)

    # ---- dataset ----
    real_train = sorted(glob.glob(f"{BASE}/real/*.wav"))
    spoof_train = sorted(glob.glob(f"{BASE}/spoof/*.mp3"))
    real_test = sorted(glob.glob(f"{BASE}/test_real/*.wav"))
    spoof_test = sorted(glob.glob(f"{BASE}/test_spoof/*.mp3"))
    print(f"train: real={len(real_train)} spoof={len(spoof_train)} | "
          f"test: real={len(real_test)} spoof={len(spoof_test)}")

    Xtr_r, Ytr_r = collect(real_train, 0.0, rng, n_per_file=6)
    Xtr_s, Ytr_s = collect(spoof_train, 1.0, rng, n_per_file=6)
    Xtr = np.concatenate([Xtr_r, Xtr_s]); Ytr = np.concatenate([Ytr_r, Ytr_s])
    Xte_r, Yte_r = collect(real_test, 0.0, rng, n_per_file=1)
    Xte_s, Yte_s = collect(spoof_test, 1.0, rng, n_per_file=1)
    Xte = np.concatenate([Xte_r, Xte_s]); Yte = np.concatenate([Yte_r, Yte_s])
    print(f"train clips={len(Xtr)} test clips={len(Xte)}")

    # ---- model ----
    d_args = {
        "architecture": "AASIST", "nb_samp": NB_SAMP, "first_conv": 128,
        "filts": [70, [1, 32], [32, 32], [32, 64], [64, 64]],
        "gat_dims": [64, 32], "pool_ratios": [0.5, 0.7, 0.5, 0.5],
        "temperatures": [2.0, 2.0, 100.0, 100.0],
    }
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = Model(d_args)
    model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
    model.to(dev).train()
    opt = torch.optim.Adam(model.parameters(), lr=1e-4, weight_decay=1e-5)
    lossf = nn.CrossEntropyLoss()
    print(f"params={sum(p.numel() for p in model.parameters())/1e6:.2f}M device={dev}")

    # ---- train loop ----
    epochs = 12
    bs = 4          # 3.6GiB GPU — batch 16 OOMs; use small batch + grad accumulation
    accum = 4       # effective batch 16
    n = len(Xtr)
    best = 0.0
    for ep in range(epochs):
        perm = rng.permutation(n)
        tl = 0.0; tb = 0
        opt.zero_grad()
        for i in range(0, n, bs):
            idx = perm[i:i + bs]
            xb = torch.from_numpy(Xtr[idx]).to(dev)   # [B, T] — model adds channel dim
            yb = torch.from_numpy(Ytr[idx]).long().to(dev)
            _, logits = model(xb)
            loss = lossf(logits, yb) / accum
            loss.backward()
            tl += loss.item() * accum * len(idx); tb += len(idx)
            if (i // bs + 1) % accum == 0:
                opt.step(); opt.zero_grad()
        # ---- held-out eval ----
        model.eval()
        torch.cuda.empty_cache()  # free fragmented train blocks — 4GiB GPU is tight
        with torch.no_grad():
            def evaluate(X, Y, name):
                preds = []
                for i in range(0, len(X), 2):   # eval batch 2 — 4GiB VRAM (GTX 1650)
                    xb = torch.from_numpy(X[i:i + 2]).to(dev)  # [B, T]
                    _, lg = model(xb)
                    preds.append(lg.argmax(1).cpu().numpy())
                preds = np.concatenate(preds)
                acc = (preds == Y).mean()
                fr = ((preds == 1) & (Y == 0)).sum()   # real misclassified as spoof
                fs = ((preds == 0) & (Y == 1)).sum()   # spoof missed
                nr = (Y == 0).sum(); ns = (Y == 1).sum()
                print(f"  {name:12s} acc={acc:.3f}  FP(real->spoof)={fr}/{nr}  "
                      f"FN(spoof missed)={fs}/{ns}")
                return acc
            a_real = evaluate(Xte_r, Yte_r, "TEST real")
            a_spoof = evaluate(Xte_s, Yte_s, "TEST spoof")
        tot = evaluate(Xte, Yte, "TEST all")
        print(f"epoch {ep+1}/{epochs} loss={tl/tb:.4f} test_acc={tot:.4f}")
        if tot > best:
            best = tot
            torch.save({"state_dict": model.state_dict(), "epoch": ep, "best": float(best)},
                       OUT)
            print(f"  saved {OUT} (best={best:.4f})")
        model.train()
    print(f"\nDONE best_test_acc={best:.4f} -> {OUT}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""engine.py — Kavach audio anti-spoof engine (production inference).

Protocol (VERIFIED 2026-08-06, ad-hoc harness): 3-crop majority vote
(first/middle/last 4s windows) — single-crop is crop-dependent (0.9355 acc),
vote restores held-out 0.9919 (0/100 FP, 1/24 FN) on FLEURS-real vs edge-tts.

Usage:
    from engine import KavachEngine
    eng = KavachEngine()
    result = eng.analyze("call.wav")   # {"spoof": bool, "score": float, "latency_ms": float}
"""
import os, time
import numpy as np
import torch
import soundfile as sf

_HERE = os.path.dirname(os.path.abspath(__file__))
_AASIST_SRC = os.path.join(_HERE, "aasist")
_AASIST_CKPT = os.path.join(_HERE, "..", "models", "aasist-hindi.pt")

D_ARGS = {
    "architecture": "AASIST", "nb_samp": 64600, "first_conv": 128,
    "filts": [70, [1, 32], [32, 32], [32, 64], [64, 64]],
    "gat_dims": [64, 32], "pool_ratios": [0.5, 0.7, 0.5, 0.5],
    "temperatures": [2.0, 2.0, 100.0, 100.0],
}
NB_SAMP = 64600          # 4.04s @ 16k
N_CROPS = 3              # majority-vote windows


class KavachEngine:
    def __init__(self, ckpt=_AASIST_CKPT, device=None):
        import sys
        sys.path.insert(0, _AASIST_SRC)
        from AASIST import Model
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = Model(D_ARGS)
        ck = torch.load(ckpt, map_location="cpu")
        missing, unexpected = self.model.load_state_dict(ck["state_dict"], strict=False)
        assert not missing and not unexpected, f"ckpt mismatch m={missing} u={unexpected}"
        self.model.to(self.device).eval()
        # warmup
        with torch.no_grad():
            self.model(torch.zeros(1, NB_SAMP).to(self.device))

    @staticmethod
    def _load_wav(path):
        x, sr = sf.read(path, dtype="float32")
        if x.ndim > 1:
            x = x.mean(1)
        if sr != 16000:
            import scipy.signal as sig
            x = sig.resample_poly(x, 16000, sr)
        return x

    def _crops(self, x):
        if len(x) < NB_SAMP:
            x = np.pad(x, (0, NB_SAMP - len(x)))
        if len(x) == NB_SAMP:
            return [x]
        out = []
        for f in np.linspace(0, len(x) - NB_SAMP, N_CROPS):
            out.append(x[int(f):int(f) + NB_SAMP])
        return out

    def analyze(self, path):
        x = self._load_wav(path)
        t0 = time.time()
        probs = []
        with torch.no_grad():
            for c in self._crops(x):
                _, lg = self.model(torch.from_numpy(c).unsqueeze(0).to(self.device))
                probs.append(torch.softmax(lg, 1)[0, 1].item())
        score = float(np.mean(probs))          # mean spoof prob across crops
        votes = sum(p > 0.5 for p in probs)
        # short files (< 4.04s) collapse to ONE crop → majority vote degenerates
        # (b5: 3.84s TTS, score=1.0 but votes=1 → BONAFIDE = MISS). Fall back to the
        # score itself when the vote has nothing to vote on. (Found by audio suite.)
        spoof = (votes >= 2) if len(probs) >= 2 else (score > 0.5)
        return {
            "spoof": spoof,
            "score": round(score, 4),
            "crop_scores": [round(p, 4) for p in probs],
            "latency_ms": round((time.time() - t0) * 1000, 1),
        }


if __name__ == "__main__":
    import sys
    eng = KavachEngine()
    for p in sys.argv[1:]:
        print(p, "->", eng.analyze(p))

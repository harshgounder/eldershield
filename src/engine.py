#!/usr/bin/env python3
"""engine.py - Kavach audio anti-spoof engine (production inference).

Protocol (VERIFIED 2026-08-06, ad-hoc harness): 3-crop majority vote
(first/middle/last 4s windows) - single-crop is crop-dependent (0.9355 acc),
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
        if not np.all(np.isfinite(x)):
            x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
        # quality stats on RAW audio (before normalization: scaling would hide
        # flat-tops from the clipping gate; red-team 2026-08-25)
        clip_frac = float(np.mean(np.abs(x) > 0.995)) if len(x) else 1.0
        std = float(np.std(x)) if len(x) else 0.0
        # peak-normalize before inference (red-team 2026-08-25): AASIST's
        # 64600-sample window is amplitude-sensitive; -6dB attenuation flipped
        # spoof crops to BONAFIDE. Normalize restores the calibrated scale.
        peak = float(np.abs(x).max()) if len(x) else 0.0
        if peak > 1e-6:
            x = x * (0.95 / peak)
        return x, clip_frac, std

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
        x, clip_frac, std = self._load_wav(path)
        # signal-quality gate (red-team 2026-08-25): hard clipping and garbage
        # audio fool the model into confident verdicts; surface it so FUSION
        # never PASSes a clipped/silent/invalid call.
        quality = "clipped" if clip_frac > 0.01 else ("silent" if std < 1e-4 else "ok")
        t0 = time.time()
        probs = []
        with torch.no_grad():
            for c in self._crops_aligned(x):
                _, lg = self.model(torch.from_numpy(c).unsqueeze(0).to(self.device))
                probs.append(torch.softmax(lg, 1)[0, 1].item())
        score = float(np.mean(probs))          # mean spoof prob across crops
        max_crop = float(max(probs)) if probs else 0.0
        votes = sum(p > 0.5 for p in probs)
        # short files (< 4.04s) collapse to ONE crop → majority vote degenerates
        # (b5: 3.84s TTS, score=1.0 but votes=1 → BONAFIDE = MISS). Fall back to the
        # score itself when the vote has nothing to vote on. (Found by audio suite.)
        # red-team 2026-08-25: the vote alone is also broken by silence padding
        # (a 0.9999 crop loses 2-1). OR-rule: any single crop at 0.9+ is spoof.
        spoof = (votes >= 2) or (max_crop > 0.9) or (len(probs) == 1 and score > 0.5)
        return {
            "spoof": spoof,
            "score": round(score, 4),
            "crop_scores": [round(p, 4) for p in probs],
            "max_crop_score": round(max_crop, 4),
            "signal_quality": quality,
            "clip_fraction": round(clip_frac, 6),
            "latency_ms": round((time.time() - t0) * 1000, 1),
        }

    def _crops_aligned(self, x):
        """Crop windows for scoring.

        Files >= 4.04s: first/middle/last windows (3 crops, majority vote).
        Files <  4.04s: 3 ALIGNMENTS of the analysis window (content at the
        start, centered, at the end). Alignment invariance kills the
        weak-window truncation evasion (red-team 2026-08-25: a 4.04s excerpt
        scored 0.17 at one alignment; sliding recovers the strong span).
        """
        if len(x) >= NB_SAMP:
            return self._crops(x)
        L = len(x)
        crops = []
        for p0 in (0, (NB_SAMP - L) // 2, NB_SAMP - L):
            c = np.zeros(NB_SAMP, dtype=np.float32)
            c[p0:p0 + L] = x
            crops.append(c)
        return crops


if __name__ == "__main__":
    import sys
    eng = KavachEngine()
    for p in sys.argv[1:]:
        print(p, "->", eng.analyze(p))

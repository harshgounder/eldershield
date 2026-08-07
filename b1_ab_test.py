#!/usr/bin/env python3
"""eldershield_b1_ab.py — A/B: real Hindi (FLEURS) vs Hindi TTS (edge-tts) through AASIST.

THE make-or-break question: does the pretrained AASIST (trained on English
ASVspoof) generalize to Hindi TTS as SPOOF while passing real Hindi as BONAFIDE?
"""
import sys, os, time, glob
import numpy as np
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src", "aasist"))
from AASIST import Model  # noqa: E402

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "AASIST.pth")
NB_SAMP = 64600

def load_wav(path):
    import soundfile as sf
    x, sr = sf.read(path, dtype="float32")
    if x.ndim > 1:
        x = x.mean(1)
    if sr != 16000:
        import scipy.signal as sig
        x = sig.resample_poly(x, 16000, sr)
    return x

def main():
    d_args = {
        "architecture": "AASIST", "nb_samp": NB_SAMP, "first_conv": 128,
        "filts": [70, [1, 32], [32, 32], [32, 64], [64, 64]],
        "gat_dims": [64, 32], "pool_ratios": [0.5, 0.7, 0.5, 0.5],
        "temperatures": [2.0, 2.0, 100.0, 100.0],
    }
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = Model(d_args)
    sd = torch.load(MODEL_PATH, map_location="cpu")
    model.load_state_dict(sd)
    model.to(dev).eval()
    with torch.no_grad():
        _ = model(torch.zeros(1, NB_SAMP).to(dev))  # warmup

    def classify(path, label):
        x = load_wav(path)
        if len(x) < NB_SAMP:
            x = np.pad(x, (0, NB_SAMP - len(x)))
        x = x[:NB_SAMP]
        t0 = time.time()
        with torch.no_grad():
            _, logits = model(torch.from_numpy(x).unsqueeze(0).to(dev))
        dt = (time.time() - t0) * 1000
        p = torch.softmax(logits, 1)[0]
        verdict = "SPOOF" if p[1] > p[0] else "BONAFIDE"
        print(f"{label:35s} spoof={p[1]:.4f} bonafide={p[0]:.4f} -> {verdict} ({dt:.1f}ms)")
        return verdict, p[1].item()

    print("=== REAL HUMAN HINDI (FLEURS) — must be BONAFIDE ===")
    real = []
    for f in sorted(glob.glob("/tmp/real_hi/*.wav")):
        real.append(classify(f, os.path.basename(f)))
    print("\n=== HINDI TTS (edge-tts) — must be SPOOF ===")
    fake = []
    for f in sorted(glob.glob("/tmp/tts_hi_*.mp3")):
        fake.append(classify(f, os.path.basename(f)))

    real_ok = all(v == "BONAFIDE" for v, _ in real)
    fake_ok = all(v == "SPOOF" for v, _ in fake)
    print("\n" + "=" * 50)
    print(f"REAL as BONAFIDE: {'PASS' if real_ok else 'FAIL'} ({len(real)} clips)")
    print(f"TTS as SPOOF:     {'PASS' if fake_ok else 'FAIL'} ({len(fake)} clips)")
    print("=" * 50)

if __name__ == "__main__":
    main()

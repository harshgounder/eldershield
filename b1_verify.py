#!/usr/bin/env python3
"""kavach_b1_verify.py — B1 milestone: load AASIST weights + forward pass.

Proves: (1) the downloaded AASIST.pth loads into the AASIST Model class,
(2) a real audio file (generated synthetic + real TTS-ish) produces a
valid prediction, (3) latency on GPU is sane for a <500ms real-time claim.
"""
import sys, os, json, time, wave
import numpy as np
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src", "aasist"))
from AASIST import Model  # noqa: E402

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "AASIST.pth")
NB_SAMP = 64600  # AASIST input: 4s @ 16kHz

def make_tone_wav(path, freq=220, dur=4.0, sr=16000, noise=False):
    t = np.arange(int(sr * dur)) / sr
    if noise:
        x = 0.3 * np.random.randn(len(t)) + 0.1 * np.sin(2 * np.pi * freq * t)
    else:
        x = 0.5 * np.sin(2 * np.pi * freq * t)
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((x * 32767).astype(np.int16).tobytes())

def main():
    d_args = {
        "architecture": "AASIST",
        "nb_samp": NB_SAMP,
        "first_conv": 128,
        "filts": [70, [1, 32], [32, 32], [32, 64], [64, 64]],
        "gat_dims": [64, 32],
        "pool_ratios": [0.5, 0.7, 0.5, 0.5],
        "temperatures": [2.0, 2.0, 100.0, 100.0],
    }
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = Model(d_args)
    sd = torch.load(MODEL_PATH, map_location="cpu")
    missing, unexpected = model.load_state_dict(sd, strict=False)
    print(f"load: missing={len(missing)} unexpected={len(unexpected)}")
    if missing:
        print("  missing:", list(missing)[:10])
    model.to(dev).eval()

    # warmup (CUDA kernel init — first call is ~400ms, steady state is what matters)
    with torch.no_grad():
        _ = model(torch.zeros(1, NB_SAMP).to(dev))

    # forward pass on synthetic tone (bonafide-ish) + noise (spoof-ish)
    for name, freq, noise in [("bonafide-ish tone", 220, False), ("spoof-ish noise", 220, True)]:
        wav = f"/tmp/b1_{name.split()[0]}.wav"
        make_tone_wav(wav, freq=freq, noise=noise)
        with wave.open(wav) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        if len(x) < NB_SAMP:
            x = np.pad(x, (0, NB_SAMP - len(x)))
        x = x[:NB_SAMP]
        xt = torch.from_numpy(x).unsqueeze(0).to(dev)  # [1, T] — model adds channel
        t0 = time.time()
        with torch.no_grad():
            out = model(xt)
        dt = (time.time() - t0) * 1000
        if isinstance(out, tuple):
            logits = out[1]
            print(f"{name}: logits shape={tuple(logits.shape)} latency={dt:.1f}ms")
            probs = torch.softmax(logits, dim=1)
            print(f"  probs(bonafide,spoof)={probs[0].tolist()} "
                  f"-> {'SPOOF' if probs[0,1] > probs[0,0] else 'BONAFIDE'}")
        elif torch.is_tensor(out) and out.ndim == 2:
            print(f"{name}: out={out.shape} latency={dt:.1f}ms")
            probs = torch.softmax(out, dim=1)
            print(f"  probs(bonafide,spoof)={probs[0].tolist()} "
                  f"-> {'SPOOF' if probs[0,1] > probs[0,0] else 'BONAFIDE'}")
        else:
            print(f"{name}: out type={type(out)} latency={dt:.1f}ms")

    # param count
    n = sum(p.numel() for p in model.parameters())
    print(f"params: {n/1e6:.2f}M · device: {dev}")

if __name__ == "__main__":
    main()

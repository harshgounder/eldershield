# ElderShield — Real-Time AI Voice-Clone Detection for UPI & Voice Banking

**IIC 3.0 (International Innovation Challenge, Manipal University Jaipur) — Theme: Cybersecurity & Digital Sovereignty**

## The Problem

Voice cloning is now a payment fraud vector. One cloned voice, 10 minutes, ₹1.97 lakh (Hyderabad, 2025). UPI fraud at ₹805 crore across 10.64 lakh incidents (Apr–Nov FY26). Banks warn customers — but no real-time defense exists at the UPI call gate.

## The Solution

ElderShield gives every voice call a **spoof score (0–1) + pass/fail verdict in <500 ms** — before the payment happens. India-first: trained on Hindi + regional-language audio, built for the UPI/voice-banking flow.

## How it works

```
call audio → mel-spectrogram → anti-spoof model (AASIST-hindi, 3-crop majority vote) → spoof score → verdict → PAUSE intervention
```

- **Model:** AASIST (Attention-based Spectrogram Transformer) fine-tuned on Hindi deepfake data
- **Latency:** ~80–350 ms on a GTX 1650 (4 GB) laptop GPU — real-time on call
- **Verdicts:** SPOOF (0.9–1.0) → PAUSE + verify identity · BONAFIDE (0.0–0.1) → PASS
- **Evidence packet:** every detection emits a JSON audit trail (timestamp, score, crop scores, model, latency, chain) for compliance

## Demo

- Live UI: `python demo_ui.py` → Gradio on :7860
- Attack generator: `gen_attack()` — Hindi voice-clone via edge-tts (demo tooling, disclosed)
- Screenshots: `assets/shot_01_landing.png` (UI), `shot_02_attack_detected.png` (SPOOF 1.000 → PAUSE), `shot_03_real_bonafide.png` (BONAFIDE 0.000 → PASS)
- Evidence packets: `assets/evidence_attack.json`, `assets/evidence_real.json`

## Verified results (measured 2026-08-08)

| Input | Verdict | Spoof score | Latency |
|---|---|---|---|
| Hindi voice-clone attack (edge-tts) | SPOOF → PAUSE | 1.000 | 286.4 ms |
| Real Hindi call audio (FLEURS test set) | BONAFIDE → PASS | 0.000 | 352.4 ms |

## Repo layout

```
src/engine.py          — ElderShieldEngine: model load, 3-crop vote, analyze()
demo_ui.py             — Gradio UI: upload/record → verdict + evidence packet
scripts/               — capture + verify scripts (headless playwright)
assets/                — screenshots, evidence packets, sample audio
models/                — AASIST-hindi fine-tune weights
data/                  — evaluation sets
b1_verify.py           — smoke test (weights load, CUDA, latency)
b1_ab_test.py          — A/B evaluation script
```

## References

- RBI/2024-25/105 — voice/SMS fraud safeguards
- CERT-In CIAD-2024-0060 — Deepfakes: threats & countermeasures
- ASVspoof 2021 LA — anti-spoofing benchmark + baselines
- AASIST — clovaai/aasist (github.com/clovaai)

## AI Disclosure

GenAI used for ideation/support only. Model training, evaluation and this submission's technical claims are our own work.

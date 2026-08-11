# ElderShield — Digital-Arrest & Voice-Scam Shield for Indian Families

**IIC 3.0 (International Innovation Challenge, Manipal University Jaipur) — Theme: Cybersecurity & Digital Sovereignty**

## The Problem

India's largest quantified fraud is the **digital-arrest scam**: fake CBI/police calls that coerce victims — mostly elders — into transferring their life savings. **₹4,057.7 crore lost across 297,727 complaints (2022–May 2026).** Losses grew 20× by 2024. Scammers now pair coercion scripts with **AI-cloned voices** ("Dad, I'm in jail, send money") — a clone takes 30–60 seconds of harvested audio, costs pennies, and the call arrives with a spoofed caller ID.

Every bank warns customers. No consumer app defends the phone itself — in Hindi.

## The Solution

ElderShield is a **call-security platform** that fuses six detection departments into one intervention loop:

| Department | Question |
|---|---|
| Spoof | Is this voice real? (AASIST-hindi, 3-crop vote) |
| Coercion | Is this a scam script? (Hindi ASR + 7 vector banks) |
| Threat | Is this caller dangerous? |
| Factcheck | Is this claim true? |
| Payment Tripwire | Is a payment about to happen? (before the PIN) |
| Evidence + Report | Tamper-proof packet → 1930 / Chakshu |

The FUSION core turns all signals into **one verdict → one intervention**: recognize → interrupt → verify → package → report.

**The product loop:** the moment a call shows both spoof AND coercion signals, ElderShield pauses the payment moment — warns the victim in Hindi, alerts a trusted family member, and generates a tamper-proof evidence packet ready for 1930.

## How it works

```
call audio → mel-spectrogram → anti-spoof model (AASIST-hindi, 3-crop majority vote) → spoof score
          → faster-whisper Hindi ASR → coercion state (7 vectors) → FUSION verdict → PAUSE → evidence → 1930
```

- **Model:** AASIST (Attention-based Spectrogram Transformer) fine-tuned on Hindi deepfake data — 0.9919 accuracy, 0/100 false positives on held-out Hindi spoof data
- **Latency:** ~80–350 ms on a GTX 1650 (4 GB) laptop GPU (on-device scoring)
- **Honest platform note:** consumer Android apps cannot record live cellular calls (VOICE_CALL is privileged). ElderShield owns the moments Android permits: pre-ring screening, own-mic analysis burst, the payment tripwire (Play-sanctioned Accessibility for fraud prevention), the evidence capsule, and family escalation. Higher-assurance tiers (CPaaS second number, bank/FRI partnership) are roadmap.

## Repo layout

```
src/engine.py          — ElderShieldEngine: model load, 3-crop vote, analyze()
src/coercion.py        — Hindi coercion detection (7 vectors, fuzzy, rule boosts)
src/evidence.py        — sha256 chain-of-custody packet + 1930-ready PDF
demo_ui.py             — Gradio UI: upload/record → verdict + evidence packet
demo/b3-intervention-mock.html — PAUSE screen + family-challenge UI flow mock (static preview)
scripts/               — capture + verify scripts
assets/                — screenshots, evidence packets, sample audio, deck
b1_verify.py           — smoke test (weights load, CUDA, latency)
b1_ab_test.py          — A/B evaluation script
b2_finetune.py         — Hindi fine-tuning script
```

## Verified results (measured 2026-08-08)

| Input | Verdict | Spoof score | Latency |
|---|---|---|---|
| Hindi voice-clone attack (edge-tts) | SPOOF → PAUSE | 1.000 | 286.4 ms |
| Real Hindi call audio (FLEURS test set) | BONAFIDE → PASS | 0.000 | 352.4 ms |

Evidence packets: every detection emits a sha256-chained JSON audit trail + 1930-ready PDF (12 generated, tamper-verified).

## Build status (honest)

- ✅ B1 spoof engine — built, verified (0.9919 acc, 0/100 FP)
- ✅ B2 coercion layer — built (Hindi ASR + 7 vectors, robustness battery 5/5)
- ✅ B4 evidence packet — built (sha256 chain, tamper-verified)
- 🟡 B3 intervention UI — UI-flow mock (static preview in `demo/`), full build in progress
- 🟡 Demo video — being re-recorded for the C1 story

## References

- RBI/2024-25/105 — voice/SMS fraud safeguards
- CERT-In CIAD-2024-0060 — Deepfakes: threats & countermeasures
- DoT FRI: 1000+ banks · ₹660 crore prevented (Dec 2025)
- SC order (Aug 4 2026) — digital-arrest complaints 1,23,672 → 16,377 (I4C data)
- ASVspoof 2021 LA — anti-spoofing benchmark + baselines
- AASIST — clovaai/aasist (github.com/clovaai)

## AI Disclosure

GenAI used for ideation/support only. Model training, evaluation and this submission's technical claims are our own work.

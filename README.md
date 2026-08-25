# Kavach - Digital-Arrest & Voice-Scam Shield for Indian Families

**IIC 3.0 (International Innovation Challenge, Manipal University Jaipur) - Theme: Cybersecurity & Digital Sovereignty**

## The Problem

India's largest quantified fraud is the **digital-arrest scam**: fake CBI/police calls that coerce victims - mostly elders - into transferring their life savings. **₹4,057.7 crore lost across 297,727 complaints (2022–May 2026).** Losses grew ~10× to 2024 (I4C/NCRP complaint series). Scammers now pair coercion scripts with **AI-cloned voices** ("Dad, I'm in jail, send money") - a clone takes seconds to minutes of harvested audio, costs pennies, and the call arrives with a spoofed caller ID.

Every bank warns customers. No consumer app defends the phone itself - in Hindi.

## The Solution

Kavach is a **call-security platform** that fuses six detection departments into one intervention loop:

| Department | Question |
|---|---|
| Spoof | Is this voice real? (AASIST-hindi, 3-crop vote) |
| Coercion | Is this a scam script? (Hindi ASR + 8 vector banks) |
| Threat | Is this caller dangerous? |
| Factcheck | Is this claim true? |
| Payment Tripwire | Is a payment about to happen? (before the PIN) |
| Evidence + Report | Tamper-evident packet → 1930 / Chakshu |

The FUSION core turns all signals into **one verdict → one intervention**: recognize → interrupt → verify → package → report.

**The product loop:** the moment a call shows both spoof AND coercion signals, Kavach pauses the payment moment - warns the victim in Hindi, alerts a trusted family member, and generates a tamper-evident evidence packet ready for 1930.

## How it works

```
call audio → mel-spectrogram → anti-spoof model (AASIST-hindi, 3-crop majority vote) → spoof score
          → faster-whisper Hindi ASR → coercion state (8 vectors) → FUSION verdict → PAUSE → evidence → 1930
```

- **Model:** AASIST (Attention-based Spectrogram Transformer) fine-tuned on Hindi deepfake data - 0.9919 accuracy, 0/100 false positives on held-out Hindi spoof data (re-verified 2026-08-11)
- **Latency:** ~71 ms mean (max ~100 ms) for the 3-crop spoof verdict alone on a GTX 1650 (4 GB) laptop GPU, warm model; local scoring (laptop-class GPU in the measured build, phone packaging is R2). The full pipeline adds Hindi ASR (faster-whisper small), which takes seconds on CPU (10-19 s on 6-12 s clips; silence trimmed before ASR).
- **Honest platform note:** consumer Android apps cannot record live cellular calls (VOICE_CALL is privileged). Kavach owns the moments Android permits: pre-ring screening, own-mic analysis burst, the payment tripwire (Play-sanctioned Accessibility for fraud prevention), the evidence capsule, and family escalation. Higher-assurance tiers (CPaaS second number, bank/FRI partnership) are roadmap.

## Repo layout

```
v1_loop.py             - THE executable: full product loop (recognize→fuse→interrupt→package→report)
                         run: python v1_loop.py <audio> [--payee-new] [--amount N] [--decision approve|challenge|kill]
                              python v1_loop.py --demo   # 5-scenario battery
src/engine.py          - KavachEngine: AASIST-hindi model load, 3-crop vote, analyze()
src/coercion.py        - Hindi coercion detection (8 vectors, fuzzy, rule boosts)
src/fusion.py          - FUSION core: 6 departments → one verdict ladder (PASS/CAUTION/PAUSE/KILL)
src/evidence.py        - sha256 chain-of-custody packet (KV-) + 1930-ready PDF
demo_ui.py             - Gradio UI: upload/record → verdict + evidence packet
demo/b3-intervention-mock.html - PAUSE screen + family-challenge UI flow mock (static preview)
benchmarks/            - the test battery (all re-runnable): audio 31/31 · stress 226/226
                         · real-cases 29/29 (24 documented incidents) · curated 10/10 · D7 90%
scripts/               - capture + verify scripts
assets/                - screenshots, evidence packets, sample audio, deck (v6 current; v2 = member-filled variant; v1-ARCHIVED = pre-rebrand)
models/                - aasist-hindi.pt + AASIST weights (tracked)
b1_verify.py           - smoke test (weights load, CUDA, latency)
b1_ab_test.py          - A/B evaluation script
b2_finetune.py         - Hindi fine-tuning script
```

## Verified results (measured 2026-08-11)

| Input | Verdict | Spoof score | Latency |
|---|---|---|---|
| Hindi voice-clone attack (edge-tts) | SPOOF → PAUSE | 1.000 | ~70–100 ms |
| Real Hindi call audio (FLEURS test set) | BONAFIDE → PASS | 0.000 | ~70–100 ms |

Full benchmark battery (2026-08-11, all re-runnable): **audio 31/31 · stress 226/226 · real-case registry 29/29 · curated 10/10 · evidence mutation 90% · unit 31 OK**. The real-case registry replays 24 documented Indian scam incidents (BBC/NDTV/IE/TOI/FPJ) - every documented script is flagged. Evidence packets: every detection emits a sha256-chained JSON audit trail + 1930-ready PDF (70 KV- packets, chain-verified).

## Quickstart

```bash
# 1. install deps (Python 3.10+; NVIDIA GPU recommended)
uv venv && uv pip install -r requirements.txt

# 2. run the full product loop on any call audio (real or synthetic)
python v1_loop.py <call.wav|mp3> [--payee-new] [--amount 150000]

# 3. run the 5-scenario demo battery (3 attacks + 2 real calls)
python v1_loop.py --demo

# 4. launch the Gradio UI (upload/record → verdict + evidence packet)
python demo_ui.py        # → http://127.0.0.1:7860

# 5. re-run the test battery
python benchmarks/run_audio.py && python benchmarks/run_stress.py && \
python benchmarks/run_real_cases.py && python benchmarks/run_mutation.py
```

Models ship in `models/` (aasist-hindi.pt + AASIST weights) - no download needed. The first `v1_loop.py` call downloads the faster-whisper small (hi) ASR model (~460 MB, cached).

## Build status (honest)

- ✅ B1 spoof engine - built, verified (0.9919 acc, 0/100 FP, re-verified 2026-08-11)
- ✅ B2 coercion layer - built (Hindi ASR + 8 vectors; audio suite 31/31, stress 226/226, real-case registry 29/29)
- ✅ B4 evidence packet - built (sha256 chain, D7 mutation 90% caught, 70 KV- packets)
- 🟡 B3 intervention UI - UI-flow mock (static preview in `demo/`), full Android build is R2

## Known limitations (measured, red-team 2026-08-25)

- **Spoof-layer evasions:** the 3-crop vote is breakable by silence padding, volume attenuation, hard clipping, and 4.04s truncation. Mitigations shipped: peak normalization, a max-crop-or-vote rule (any 0.9+ crop is a spoof signal), a clipping/silence quality gate (clipped, silent or invalid audio can never PASS), and the coercion layer as backstop (every scripted evasion still ends PAUSE/KILL).
- **Low-confidence verdicts:** files under 4.04 s get one crop; treat single-crop verdicts as provisional (coercion layer still applies).
- **Tamper-evident, not tamper-proof:** the sha256 chain detects edits but a re-computing attacker can re-verify a forged chain. A signed chain (ed25519) is R2.
- **ASR is the latency floor:** spoof verdict ~71 ms, but Hindi ASR takes seconds on CPU; silence is trimmed before ASR (was 55-94 s on padded files, now bounded by the speech span).
- **Attack-clip coverage:** detection is verified against synthesized Hindi speech (edge-tts) and ASVspoof-style artifacts, not real cloned voices; real-voice scams are caught primarily by the coercion layer.
- **Fine-tune reproducibility:** the shipped aasist-hindi.pt weights were produced 2026-08-11 from a Hindi spoof/bonafide corpus that lived in scratch space and is gone; `b2_finetune.py` is the documented recipe but needs your own corpus. The inference-side battery (audio/stress/registries/mutation) is fully clone-runnable.

## References

- RBI/2024-25/105 - voice/SMS fraud safeguards
- CERT-In CIAD-2024-0060 - Deepfakes: threats & countermeasures
- DoT FRI: 1000+ banks · ₹660 crore prevented (Dec 2025)
- SC order (Aug 4 2026) - digital-arrest complaints 1,23,672 → 16,377 (I4C data)
- ASVspoof 2021 LA - anti-spoofing benchmark + baselines
- AASIST - clovaai/aasist (github.com/clovaai)

## AI Disclosure

GenAI used for ideation/support only. Model training, evaluation and this submission's technical claims are our own work.

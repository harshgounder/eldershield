# Kavach · The Hindi-First Call-Security Shield for Indian Families

**Digital-arrest and voice-scam defence built for Hindi, measured like a lab, honest about its limits.**

Kavach is India's first consumer-grade, Hindi-first call-security platform that fuses **six detection departments** into one intervention loop: **recognize → interrupt → verify → package → report**. It catches fake CBI/police "digital-arrest" scripts and AI-synthesized voices BEFORE the payment moment, pauses the transaction, alerts a trusted family member, and produces a tamper-evident, optionally ed25519-signed evidence packet ready for **1930 / Chakshu**.

> The pitch in one sentence: scammers need 30 seconds of your voice and a spoofed caller ID; every incumbent misses the seconds between "scam detected" and "payment made". That gap is Kavach.

**IIC 3.0 (International Innovation Challenge, Manipal University Jaipur) · Cybersecurity & Digital Sovereignty · Team 511**

---

## Why this exists (the numbers wall)

- **₹4,057.7 crore** lost to digital-arrest scams across **2,97,727 complaints** from 2022 to May 2026 (government/I4C data, cumulative).
- Losses grew **~10× to 2024** (I4C/NCRP series). Complaints grew **3×** for digital-arrest alone (39,925 → 1,23,672).
- The **SC order of Aug 4 2026** (I4C data) recorded 1,23,672 digital-arrest complaints; the regime's own enforcement cut fresh cases to 16,377 (till Jun 2026) while losses and AI-voice fraud keep compounding.
- Of **₹56,087 crore** reported cyberfraud losses, **0.37%** was refunded in that window. Prevention is the only answer.
- **47% of Indian adults** have experienced an AI-voice scam or know someone who has; **83% of victims lost money** (McAfee 2023 survey data as reported by ET/CNBC-TV18/Indian Express).
- Cloned voices need **seconds of harvested audio** (McAfee cites ~3s for a clone); attacker tooling (RVC, GPT-SoVITS) runs real-time.
- Elders are the target: 137.9M Indians are 60+ (MoSPI 2021 projection), and household smartphone access is not elder capability.

Every bank warns customers. No consumer app defends the phone itself, in Hindi. That is what Kavach is.

## The six departments (all live in code)

| Department | Question | Status |
|---|---|---|
| Spoof | Is this voice real? (AASIST-hindi, 3-window vote + max-crop rule) | LIVE |
| Coercion | Is this a scam script? (Hindi ASR + 8 vector banks, fuzzy + phonetic norms) | LIVE |
| Threat | Is this caller dangerous? (isolation/secrecy signals) | LIVE (signals) |
| Factcheck | Is this claim true? (arrest/parcel/digital-arrest claims) | LIVE (signals) |
| Payment Tripwire | Is a payment about to happen, before the PIN? (new payee / amount / collect) | LIVE |
| Evidence + Report | Tamper-evident packet → 1930 / Chakshu | LIVE |

**Fusion ladder (deterministic, unit-tested):** PASS → CAUTION → PAUSE → KILL.
Spoof OR high coercion = **PAUSE** (call held, family challenge). Both = **KILL** (hard block + one-tap report). Anything clipped, silent or invalid can never PASS (red-team hard gate). The verdict is one number a family can act on.

## Verified results (measured, re-runnable, 2026-08-11 + red-team re-verified 2026-08-25)

| Metric | Value | How it was measured |
|---|---|---|
| Held-out Hindi spoof accuracy | **0.9919** (123/124; 1/24 FN disclosed) | FLEURS real vs edge-tts synthesized, 3-window vote |
| False positives on real Hindi calls | **0/100** | Real human audio, padded and unpadded |
| Spoof verdict latency | **~71 ms mean, ~66.3 ms median, ≤100 ms** (warm, GTX 1650, local) | 3-window vote; ASR adds seconds on CPU (honest split) |
| Audio battery | **31/31**: 22 scam scripts intercepted, 7 synthesized benign calls flagged for the fake voice (correct), 2 real human calls PASS | benchmarks/run_audio.py |
| Stress battery | **226/226** across 7 suites (S1-S7: ASR-phonetic, dialect, negation, token-merge, noise, 2-level combos, text-channel) | benchmarks/run_stress.py |
| Real-incident registry | **29/29** (24 documented Indian incidents: BBC/NDTV/IE/TOI/FPJ digital-arrest, courier-drugs, utility vishing) | benchmarks/run_real_cases.py |
| Curated pool | **10/10** | benchmarks/curated runner |
| Evidence mutation catch | **90%** (10 mutation classes; key-reorder documented as non-issue by design) | benchmarks/run_mutation.py |
| Evidence packets | **70 tracked packets**, all chain-verified (104/104 after 2026-08-25 migration) | evidence.verify_packet |
| Unit tests | **37 OK** (1 documented skip) | unittest discover -s tests |
| Literature context (honest) | NASK real-fraud: domain-adapted AASIST **4.18% EER** (WACV 2026); ASVspoof 2021 LA leader 1.32% EER; our metric is OUR held-out Hindi set, not a published benchmark | citable papers |

We also publish what failed: the 2026-08-25 red-team run found silence-padding, volume attenuation, hard clipping and weak-window truncation could fool the raw vote. Every class is now closed in code (below) and the evasions are documented in README + this repo's history. A shield that hides its tests is not a shield.

## The 2026-08-25 hardening (red-team closures, all live in code)

1. **Peak normalization** before inference: -6 dB / -16 dB attenuation can no longer hide a spoof (repro: 0.116 → 1.000).
2. **Max-crop-or-vote rule**: any single window scoring 0.9+ is a spoof signal, regardless of the majority vote (kills the 10s silence-pad evasion; 0.9999 crop can no longer lose 2-1).
3. **Signal-quality gate**: hard-clipped (>1% of samples flat-topped), silent or non-finite audio is surfaced and can never PASS (fuse raises to CAUTION minimum).
4. **Alignment invariance for short files**: audio under 4.04 s is scored at 3 alignments (start / center / end) so truncation cannot hide the strong span.
5. **Silence trim before ASR**: dead-air prefixes no longer garble transcripts or balloon ASR latency (55-94 s was measured pre-fix; now bounded by speech).
6. **Phonetic norm bank**: "अटी पी" and friends normalize to OTP, closing the ASR-variance bypass.
7. **Score bands in fusion**: a 0.9+ spoof score is treated as a spoof signal even when the vote boolean is False.
8. **ed25519 signing (R2, implemented)**: packets can be signed so a "recompute-the-chain" forgery fails without the key. Keygen: `python3 scripts/gen-signing-key.py` (private key stays OUTSIDE the repo). Verify: `verify_packet_signed()`.

Re-probe after hardening: all six fabricated evasions now end PAUSE/CAUTION. The full battery was re-run and matched its pre-hardening baseline byte-for-byte (31/31, 226/226, 29/29, 90%, 37 unit tests).

## Quickstart

### Linux (uv)
```bash
uv venv && uv pip install -r requirements.txt
# NVIDIA GPU recommended; CPU works (slower ASR).
# CPU-only torch: uv pip install --index-url https://download.pytorch.org/whl/cpu torch

python b1_verify.py                    # smoke: weights load + forward pass + device
python v1_loop.py <call.wav|mp3>       # full product loop on any audio
python v1_loop.py --demo               # 5-scenario battery (3 attacks + 2 real)
python demo_ui.py                      # Gradio UI at http://127.0.0.1:7860
```

### Windows (one click)
Double-click `run.bat`: creates a venv, installs deps, launches the demo UI. First run takes 5-15 min (deps + ASR model download).

### Re-run the whole battery (all numbers in this README are 1-command reproducible)
```bash
python benchmarks/run_audio.py && python benchmarks/run_stress.py && \
python benchmarks/run_real_cases.py && python benchmarks/run_mutation.py && \
python -m unittest discover -s tests -q
```
Models ship in `models/` (aasist-hindi.pt + AASIST.pth). The first loop call downloads faster-whisper small (hi) (~460 MB, cached).

## Usage

```bash
python v1_loop.py call.wav                     # just analyze
python v1_loop.py call.wav --payee-new --amount 150000   # arm the payment tripwire
python v1_loop.py call.wav --decision approve  # family override path (logged)
```

Every run emits a **KV- evidence packet** (JSON + 1930-ready PDF): sha256 chain over audio → spoof verdict → coercion profile, plus a meta_hash covering packet id / timestamp / model metadata / any injected junk key. Any edit breaks the chain (mutation suite proves it 90% of classes, 100% of value-changing classes). For production issuance, sign with ed25519 (see hardening item 8).

## Repo layout

```
v1_loop.py             - THE executable product loop
src/engine.py          - AASIST-hindi, aligned crops, quality gate
src/coercion.py        - Hindi coercion detection (8 vectors, fuzzy, phonetic norms)
src/fusion.py          - six departments -> PASS/CAUTION/PAUSE/KILL
src/evidence.py        - sha256 chain + meta_hash + ed25519 signing + PDF
demo_ui.py             - Gradio UI (record/upload -> verdict + evidence)
demo/                  - intervention-flow mock (honestly badged as spec screens)
benchmarks/            - the full re-runnable battery (31/31, 226/226, 29/29, 10/10, D7 90%)
scripts/               - capture/verify/signing tools
assets/                - screenshots, sample audio, evidence examples, deck v6
models/                - aasist-hindi.pt + AASIST.pth (tracked, clone-runnable)
tests/                 - 37 unit tests
```

## Known limitations (measured and published, that is the point)

- **Attack-clip coverage:** detection is verified against synthesized Hindi (edge-tts) and ASVspoof-style artifacts, not real cloned voices. Real-voice scams are caught primarily by the coercion layer.
- **Android platform wall:** consumer Android cannot record live cellular calls (VOICE_CALL is privileged). Kavach owns the moments Android permits: pre-ring screening, own-mic burst, payment tripwire (Accessibility, fraud-prevention use), evidence capsule, family escalation. Higher-assurance tiers (CPaaS second number, bank/FRI partnership) are R2 roadmap.
- **ASR is the latency floor:** spoof verdict ~71 ms, Hindi ASR seconds on CPU (silence-trimmed).
- **Tamper-evident by default:** signatures are implemented but production packets should sign (key stays out of repo).
- **Fine-tune reproducibility:** shipped weights were produced 2026-08-11 from a scratch corpus (gone); `b2_finetune.py` is the recipe and needs your own corpus. The inference-side battery is fully clone-runnable.
- **Single-window boundary:** audio at exactly 4.04 s scores one window; the score fallback plus the coercion layer carry it (verified, see hardening item 4).

## Roadmap (R2)

- ed25519 signing: DONE in code (keygen + verify in this repo).
- Alignment invariance: DONE in code.
- Clipping/attenuation augmentation retrain: blocked on corpus (recipe in b2_finetune.py).
- Android: CallScreeningService pre-ring + DPDP consent-first flow + payment-tripwire Accessibility.
- Cloud tiers: cloud-first-answer, FRI/bank partnership rails.

## AI Disclosure

GenAI used for ideation and support only. Model training, evaluation and every technical claim in this repository are our own work, measured in this repo, re-runnable in this repo. We name our failure modes because a security product that hides them is not a security product.

## References

- RBI/2024-25/105 · voice/SMS fraud safeguards (Jan 2025) · rbi.org.in
- RBI Authentication Mechanisms Directions 2025 (RBI/2025-26/79) · 2FA mandatory 1 Apr 2026 · rbi.org.in
- CERT-In CIAD-2024-0060 · Deepfakes: threats and countermeasures · cert-in.org.in
- DoT FRI: 1000+ banks/TPAPs · ~₹660 crore potential losses prevented (reported Dec 2025) · pib.gov.in
- SC order Aug 4 2026 · digital-arrest complaints 1,23,672 → 16,377 (I4C data) · thehindubusinessline.com
- ASVspoof 2021 LA (zenodo) + NASK real-fraud benchmark (WACV 2026, CVF open access; dataset restricted)
- McAfee 2023: 47% of Indian adults exposed to AI voice scams, 83% lost money (ET/CNBC-TV18/Indian Express coverage)
- AASIST · clovaai/aasist (github.com/clovaai)

---
**Team 511 · Manipal University Jaipur · IIC 3.0 Cybersecurity.** The shield every Indian family deserves: Hindi-first, phone-level, evidence-backed.
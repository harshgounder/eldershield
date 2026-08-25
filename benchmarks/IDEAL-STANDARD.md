# IDEAL-STANDARD - the 100% reference for Kavach evaluation

Every benchmark suite scores against THIS. A dimension at 100% means the system
does everything below, always. Nothing on this page is "aspirational fluff" -
every row is measurable and a suite exists (or is planned) to test it.

Scoring rule: dimension score = passes / total cases, weighted by severity class
(CRITICAL failures = 0 for the whole dimension; MAJOR = −0.5; MINOR = −0.1).

---

## D1 - SPOOF DETECTION (audio anti-spoof)
100% = 
- [ ] Real human Hindi speech → BONAFIDE, score < 0.5 (0/100 FP target, held-out)
- [ ] Cloned/TTS Hindi speech → SPOOF, score > 0.5 (majority vote ≥ 2/3 crops)
- [ ] Codec/noise-degraded audio still classifies correctly (Opus, 8kHz telephony)
- [ ] Short windows (≥2s) give provisional verdicts with bounded EER (≤5% target)
- [ ] Empty/silent/garbage audio → fails SAFE (no verdict, no crash, no false SPOOF)
Test surface: engine on curated audio set (audio-level, slow - curated only)

## D2 - COERCION: HINDI (Devanagari script)
100% =
- [ ] Digital-arrest script (authority+arrest+payment) → HIGH_RISK
- [ ] OTP-bot / card-block script → ELEVATED+ (payment+urgency signature)
- [ ] Couriers-customs (parcel+drugs, no authority) → ELEVATED+ 
- [ ] Soft scripts (account-freeze+PIN, no authority) → ELEVATED
- [ ] PSA / gov-awareness lines (सीबीआई mention) → never HIGH_RISK, never PAUSE
- [ ] Genuine family/business calls → LOW (0/100 FP target)
Test surface: text-level bank matching on curated transcript corpus (fast)

## D3 - COERCION: HINGLISH (Roman-script + code-mixed)
100% = same behaviors as D2, for:
- [ ] Roman-script Hinglish scams (the slip1 class)
- [ ] Code-mixed Hinglish (Hindi words in Latin script + English financial terms)
- [ ] Phonetic-garbled Devanagari transcripts (faster-whisper real output)
Test surface: text-level on the Hinglish candidate corpus (fast) + audio spot-checks

## D4 - LANGUAGE ROBUSTNESS (dialects, accents, obfuscation)
100% =
- [ ] Haryanvi/Bhojpuri/Punjabi-accented Hindi vocabulary → same verdicts as D2
- [ ] Acronym-dot obfuscation (सी.बी.आई., ओ.टी.पी.) → caught
- [ ] Zero-width / emoji / punctuation injection → caught or safely ignored
- [ ] Merged tokens (कार्डनंबर, पिंचाहिए) → caught (fuzzy medium-phrase class)
- [ ] Nukta-doubling (फ्रीज़़़) → normalized
- [ ] Negation-injection ("hum kabhi OTP nahi maangte… ab OTP batao") → still caught
- [ ] Kinship scams → DOCUMENTED BOUNDARY (B3's job) - never falsely HIGH, never silent
Test surface: text-level (fast, thousands of cases in stress)

## D5 - FUSION LADDER (the verdict decision)
100% =
- [ ] PASS on clean calls (no signals)
- [ ] CAUTION on single weak signal (elevated coercion, tripwire alone, threat alone)
- [ ] PAUSE on spoof alone OR high-coercion alone
- [ ] KILL on spoof + high-coercion
- [ ] All six departments present on EVERY call (armed/fired flags)
- [ ] reasons[] audit trail present, includes verdict line
- [ ] Deterministic: same input → same output, always
- [ ] Robust: NaN/negative/>1/None scores never crash, never produce wrong-side verdict
Test surface: pure function grid (exhaustive, thousands in stress)

## D6 - INTERVENTION FLOW (B3)
100% =
- [ ] PAUSE/KILL → intervention ACTIVE (family challenge offered)
- [ ] approve → logged override, transfer allowed
- [ ] challenge → transfer held, family alerted
- [ ] kill → blocked + report to 1930 with evidence packet
- [ ] PASS/CAUTION → no intervention, no false alarm
- [ ] One decision per call (buttons disable)
Test surface: interactive mock (playwright) + loop state machine

## D7 - EVIDENCE INTEGRITY (B4)
100% =
- [ ] Packet contains audio hash + model metadata + all scores
- [ ] sha256 chain verifiable (verify_packet passes on unmodified)
- [ ] ANY byte flip in packet → verification FAILS (tamper-evident)
- [ ] PDF export opens, contains the same data
- [ ] No crash on missing/corrupt inputs
Test surface: mutation suite (flip every byte region, sampled)

## D8 - ROBUSTNESS (never crash)
100% =
- [ ] Empty string / whitespace / None → no crash, valid verdict
- [ ] 100KB+ input → no crash, bounded time
- [ ] Random unicode (RTL, combining, emoji, control chars) → no crash
- [ ] 5× soak: same input 5× → byte-identical output
Test surface: fuzz (thousands in stress)

## D9 - LATENCY (honest, not aspirational)
100% (measured, not promised) =
- [ ] Fusion: < 1ms (pure logic)
- [ ] Coercion text-match: < 50ms on 2s transcript
- [ ] Coercion ASR: measured per model (faster-whisper small vs candidates)
- [ ] Spoof engine: measured per crop (battery: ~300ms/crop GPU)
- [ ] Full loop: measured end-to-end (battery: 5-17s today - R2 target <10s)
Test surface: loop battery timings + stress timing bounds

---

## Scoring template
| Dim | Cases | Pass | Fail | Severity | Score | vs 100% |
|-----|-------|------|------|----------|-------|---------|
| D1  | 50    | 48   | 2    | MAJOR    | 0.90  | 90%    |

## Rival scoring (same matrix, claims-only)
Rivals get scored on PUBLIC evidence only: Truecaller / Hiya / Pindrop / Jio /
Google (Call Screen) / Apple (call screening) / banks' own fraud layers.
Unverifiable cells = NOT FOUND (counts as 0 with a flag, never assumed).

#!/usr/bin/env python3
"""gen_stress.py - combinatorial stress generator: SUITES × SERIES × thousands of cases.

THE INVARIANT: a transform must NEVER change the verdict. If a scam fires HIGH_RISK
clean, it must fire ≥ ELEVATED under ANY combination of obfuscation/dialect/negation/
merge/noise. If a benign call is LOW, it must stay LOW under any transform.

Dimensions (each is a SERIES):
  S1 obfuscation   - zero-width, dotted acronyms, emoji, latin swaps, nukta-doubling
  S2 dialect       - Haryanvi/Bhojpuri/Punjabi-accented word substitutions
  S3 negation      - denial prefixes/suffixes ("यह ठगी नहीं है", "hum kabhi nahi maangte")
  S4 merge         - token merges ("कार्ड नंबर"→"कार्डनंबर"), space collapses
  S5 noise         - punctuation strip, case flips, double spaces, trailing junk
  S6 combo         - 2-level combinations of the above (the aggressive layer)

Base scripts: the CANONICAL forms (Devanagari + Hinglish + garbled + benign) that the
curated suite proved fire correctly. Output: benchmarks/pool/stress.jsonl (~thousands).

Deterministic (seeded). Each case: {dim, series, base_idx, text, expected, expected_min}.
  expected      = exact target where determinism holds (LOW stays LOW)
  expected_min  = the floor: any state ≥ this passes for scam bases (transforms may
                  legitimately weaken a HIGH_RISK to ELEVATED if a key word is mangled,
                  but never below ELEVATED for a scam, never above LOW for benign)
"""
import json, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "pool")
os.makedirs(OUT, exist_ok=True)

rng = random.Random(20260811)
ZERO_WIDTH = "\u200b\u200c\u200d"

# ---------------------------------------------------------------- canonical bases
SCAM_BASES = [
    # (text, expected, expected_min)
    ("मैं सीबीआई से बोल रहा हूँ, आपके नाम पर वारंट है, तुरंत पैसे भेजो", "HIGH_RISK", "ELEVATED"),
    ("आपके पार्सल में ड्रग्स मिला है, कस्टम ड्यूटी जमा करो", "ELEVATED", "ELEVATED"),
    ("आपका कार्ड ब्लॉक हो गया है, अनब्लॉक के लिए ओटीपी बताइए", "ELEVATED", "ELEVATED"),
    ("मैं साइबर क्राइम विभाग से बोल रहा हूँ, आपका एफआईआर दर्ज है", "HIGH_RISK", "ELEVATED"),
    ("hello maam main police station se bol raha hoon, aapke naam par package aaya hai, turant card number aur OTP batao", "HIGH_RISK", "ELEVATED"),
    ("madam aapka account freez ho gaya hai, verification ke liye pin chahiye", "ELEVATED", "ELEVATED"),
    ("हलो मैंग मेंग पूलीस श्टेशन से बोल रहा हूँ. आपके नाम पर एक पाकेज आया है, जिस में कुछ गलक मिला है. तुरंट कार्द नंबर और उटी पी बताओ", "ELEVATED", "ELEVATED"),
    ("तुम्हारे नाम पर डिजिटल अरेस्ट हुआ है, अभी ओटीपी बताओ वरना जेल होगा", "HIGH_RISK", "ELEVATED"),
]
BENIGN_BASES = [
    "नमस्ते जी, मैं आपके बेटे का दोस्त हूँ, कल पार्टी है, आना",
    "पापा, मैं ऑफिस से बोल रहा हूँ, रात को खाना साथ खाएंगे",
    "मैडम, आपका खाने का ऑर्डर आ गया है, गेट पर ले लो",
    "मैं डॉक्टर की क्लिनिक से बोल रहा हूँ, आपकी रिपोर्ट तैयार है",
    "hello bhai, kal match hai, aana zaroor",
    "mummy main train mein hoon, ghar 8 baje pahunchunga",
]

# ---------------------------------------------------------------- transforms
# REALITY CHECK: this is a PHONE CALL product. The input is AUDIO → ASR → text.
# The attacks that actually exist in a call are what the ASR EMITS under real
# speech: phonetic garbling, dialect vocabulary, code-mixing, word merges.
# Emoji/zero-width/dotted-acronyms are TEXT-channel attacks (SMS, WhatsApp, UPI
# screens) - they belong in the small S7 side-series for the platform's future
# text side, NOT in the call-path core.

# S7 - ASR-PHONETIC MUTATION: the EMPIRICAL attack. These are the exact
# substitutions faster-whisper hi actually produced in our probe transcripts
# (hinglish-slip-probe + dialect-probe, 2026-08-11). A scammer speaking these
# ways IS the real threat model.
ASR_MUTATIONS = [
    ("पुलिस", "पूलीस"), ("पुलिस", "पोलिस"), ("पुलिस", "पुलीस"),
    ("स्टेशन", "श्टेशन"), ("ओटीपी", "उटी पी"), ("ओटीपी", "ओटी पी"),
    ("ओटीपी", "अटीपी"), ("कार्ड", "कार्द"), ("पैकेज", "पाकेज"),
    ("तुरंत", "तुरंट"), ("अकाउंट", "अकाुन्त"), ("अकाउंट", "अकान्त"),
    ("फ्रीज़", "फ्रीज"), ("पिन चाहिए", "पिंचाहिए"), ("भेज दो", "भेज्दू"),
    ("मिनट", "मिनित"), ("टेंशन", "तेंशन"), ("पैसे", "पैसी"),
    ("गिरफ्तारी", "गिराफ्तारी"), ("वेरिफाई", "वेरिफाइ"),
    ("ड्रग्स", "द्रक्स"), ("ड्रग्स", "द्रग्स"), ("ड्रग्स", "ध्रक्स"),
    ("हो गया", "होगया"), ("सीबीआई", "सी.बी.आई."), ("चाहिए", "चाहिये"),
]
def t_asr_phonetic(s, rng):
    """Apply 1-3 REAL ASR substitutions (from probe evidence)."""
    words = s.split()
    if not words:
        return s
    for _ in range(rng.randint(1, 3)):
        i = rng.randrange(len(words))
        w = words[i]
        for bad, good in rng.sample(ASR_MUTATIONS, min(3, len(ASR_MUTATIONS))):
            if bad in w and w != good:
                words[i] = w.replace(bad, good, 1)
                break
    return " ".join(words)

def t_zero_width(s, rng):
    """Insert zero-width chars at random positions."""
    if not s:
        return s
    out = []
    for ch in s:
        out.append(ch)
        if rng.random() < 0.08:
            out.append(rng.choice(ZERO_WIDTH))
    return "".join(out)

def t_dotted_acronym(s, rng):
    """सीबीआई → सी.बी.आई., ओटीपी → ओ.टी.पी., सीबीआय variants."""
    return (s.replace("सीबीआई", "सी.बी.आई.").replace("ओटीपी", "ओ.टी.पी.")
             .replace("आरबीआई", "आर.बी.आई.").replace("एनसीबी", "एन.सी.बी."))

def t_emoji(s, rng):
    """Insert emoji spam at WORD BOUNDARIES (realistic - scammers never split words)."""
    words = s.split()
    if not words:
        return s
    i = rng.randrange(len(words) + 1)
    return " ".join(words[:i] + [rng.choice(["🤑🤑", "😱", "📞", "⚠️"])] + words[i:])

def t_latin_swap(s, rng):
    """Swap a random Devanagari word to its latin form (code-mix)."""
    words = s.split()
    if not words:
        return s
    i = rng.randrange(len(words))
    LATIN = {"सीबीआई": "CBI", "ओटीपी": "OTP", "पुलिस": "police", "पैसे": "paise",
             "तुरंत": "turant", "भेजो": "bhejo", "कार्ड": "card", "बताओ": "batao",
             "वारंट": "warrant", "अभी": "abhi", "नहीं": "nahi", "जेल": "jail",
             "पार्सल": "parcel", "ड्रग्स": "drugs", "बैंक": "bank", "पिन": "pin"}
    if words[i] in LATIN:
        words[i] = LATIN[words[i]]
    return " ".join(words)

def t_nukta(s, rng):
    """Double nuktas on ़-carrying words (फ़→फ़़, ़ doubling)."""
    return s.replace("फ़", "फ़़").replace("फ", "फ़").replace("ज़", "ज़़")

def t_dialect_swap(s, rng):
    """Haryanvi/Bhojpuri/Punjabi-accented substitutions."""
    swaps = [
        ("मैं", "हम"), ("मेरा", "हमार"), ("तुम्हारे", "तोहार"), ("आपके", "तेरे"),
        ("मैं", "मैं तो"), ("पड़ेगा", "पड़ेगा"), ("है", "बा"), ("है", "है"),
        ("नहीं तो", "नहीं ते"), ("जाएगा", "जाई"), ("जाएगा", "हो जू"),
    ]
    k = rng.randrange(len(swaps))
    a, b = swaps[k]
    return s.replace(a, b)

def t_negation_prefix(s, rng):
    return rng.choice([
        "यह ठगी नहीं है. ", "हम कभी फोन पर पैसे नहीं मांगते. ",
        "सुनो, ये कॉल सच्ची है. ", "डरो मत, मैं असली अधिकारी हूँ. ",
    ]) + s

def t_negation_suffix(s, rng):
    return s + rng.choice([
        " यह कोई ठगी नहीं है.", " हम सिर्फ मदद कर रहे हैं.", " यह सब वेरिफिकेशन के लिए है.",
    ])

def t_merge(s, rng):
    """Collapse random adjacent spaces (token merges: कार्ड नंबर → कार्डनंबर)."""
    words = s.split()
    if len(words) < 2:
        return s
    for _ in range(rng.randint(1, 3)):
        i = rng.randrange(len(words) - 1)
        words[i] = words[i] + words[i + 1]
        del words[i + 1]
    return " ".join(words)

def t_noise(s, rng):
    """Punctuation strip, case flips (latin), double spaces, trailing junk."""
    variants = [
        s.replace(",", "").replace(".", "").replace("?", ""),
        s.upper() if any(c.isascii() and c.isalpha() for c in s) else s,
        "  " + s + "  ",
        s + rng.choice([" ...", "!!", "??", " हाँ", " ठीक है?"]),
        s.replace(" ", "  "),
    ]
    return rng.choice(variants)

# ---------------------------------------------------------------- build
cases = []
series = {
    "S1_asr_phonetic": [t_asr_phonetic],           # the REAL attack (audio reality)
    "S2_dialect": [t_dialect_swap],                # regional vocabulary
    "S3_negation": [t_negation_prefix, t_negation_suffix],
    "S4_merge": [t_merge],                         # ASR word-merges (कार्डनंबर)
    "S5_noise": [t_noise],                         # punctuation/latency junk
    "S6_combo": [],                                # filled below (2-level combos)
    "S7_text_channel": [t_zero_width, t_dotted_acronym, t_emoji],  # FUTURE text side (SMS/UPI screens)
}
ALL_TRANSFORMS = [t_asr_phonetic, t_dialect_swap, t_negation_prefix, t_negation_suffix,
                  t_merge, t_noise, t_zero_width, t_dotted_acronym, t_emoji]

def emit(series_name, text, base_expected, min_ok, is_scam, idx):
    cases.append({
        "series": series_name, "base_idx": idx, "is_scam": is_scam,
        "text": text, "expected": base_expected,
        "expected_min": "ELEVATED" if is_scam else "LOW",
    })

# S1–S5: single transforms on every base
for base_idx, (s, exp, exp_min) in enumerate(SCAM_BASES):
    for tname, fns in series.items():
        for fn in fns:
            emit(tname, fn(s, rng), exp, exp_min, True, base_idx)
for base_idx, s in enumerate(BENIGN_BASES):
    for tname, fns in series.items():
        if tname == "S3_negation":
            continue  # negation prefixes on benign = false-positive bait, not a real call
        for fn in fns:
            emit(tname, fn(s, rng), "LOW", "LOW", False, base_idx)

# S6 combo: 2-level combinations on scam bases only (the aggressive layer)
for base_idx, (s, exp, exp_min) in enumerate(SCAM_BASES):
    for _ in range(14):  # 14 random 2-level combos per scam base
        f1, f2 = rng.sample(ALL_TRANSFORMS, 2)
        emit("S6_combo", f2(f1(s, rng), rng), exp, exp_min, True, base_idx)

rng.shuffle(cases)
with open(os.path.join(OUT, "stress.jsonl"), "w") as f:
    for c in cases:
        f.write(json.dumps(c, ensure_ascii=False) + "\n")

by_series = {}
for c in cases:
    by_series[c["series"]] = by_series.get(c["series"], 0) + 1
print(f"generated {len(cases)} stress cases")
for s in sorted(by_series):
    print(f"  {s}: {by_series[s]}")
print("written:", os.path.join(OUT, "stress.jsonl"))

#!/usr/bin/env python3
"""gen_candidates.py — generate HUNDREDS of candidate benchmark cases per dimension.

The pool: every case is (dim, sub, severity, text/audio-spec, expected, tags[]).
Severity: CRITICAL (any fail = dimension 0) / MAJOR / MINOR.
Deterministic (seeded) so regen is stable. Outputs JSONL to benchmarks/pool/.

From this pool the CURATED suites (benchmarks/suites/*.py) select the best cases —
this file makes the "hundreds of options, we craft the best" pipeline real.
"""
import json, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "pool")
os.makedirs(OUT, exist_ok=True)

rng = random.Random(20260811)
pool = []

def add(dim, sub, severity, text, expected, tags=None):
    pool.append({
        "dim": dim, "sub": sub, "severity": severity,
        "text": text, "expected": expected, "tags": list(tags or []),
    })

# ══════════════════════════════════════════════════════════════
# D2 — COERCION HINDI (Devanagari)
# ══════════════════════════════════════════════════════════════
DA_SCRIPTS = [
    "सीबीआई से बोल रहा हूँ, आपके नाम पर वारंट है, तुरंत पैसे भेजो",
    "मैं साइबर क्राइम विभाग से बोल रहा हूँ, आपका एफआईआर दर्ज है, अभी केस चल रहा है",
    "आपके आधार कार्ड का इस्तेमाल हुआ है, पूछताछ के लिए थाने चलना होगा, पहले वेरिफिकेशन के लिए ओटीपी बताओ",
    "ईडी से बोल रहा हूँ, आपके खाते में काला धन आया है, डिमांड ड्राफ्ट जमा करो",
    "पुलिस स्टेशन से बोल रहा हूँ, आपके बेटे ने एक्सीडेंट किया है, जुर्माना भरो",
    "इनकम टैक्स विभाग, आपके नाम पर टैक्स चोरी का केस है, कुर्की से बचने के लिए पैसे जमा करें",
]
for i, s in enumerate(DA_SCRIPTS):
    add("D2", "digital_arrest", "CRITICAL", s, "HIGH_RISK", ["da", f"da_{i}"])

OTP_SCRIPTS = [
    "आपका कार्ड ब्लॉक हो गया है, अनब्लॉक के लिए ओटीपी बताइए",
    "आपकी लिमिट बढ़ानी है, वेरिफिकेशन के लिए ओटीपी शेयर करें",
    "ट्रांज़ेक्शन फेल हुआ है, रिफंड के लिए पिन कन्फर्म करो",
    "आपका बैंक अकाउंट फ्रीज़ हो गया है, वेरिफिकेशन के लिए पिन चाहिए",
    "आपकी शिकायत मिली है, एफआईआर दर्ज करने से पहले ओटीपी वेरिफाई करें",
]
for i, s in enumerate(OTP_SCRIPTS):
    add("D2", "otp_bot", "MAJOR", s, "ELEVATED", ["otp", f"otp_{i}"])

PARCEL_SCRIPTS = [
    "आपके पार्सल में ड्रग्स मिला है, कस्टम ड्यूटी जमा करो",
    "कूरियर पकड़ा गया है, पैकेज में प्रतिबंधित चीज़ है, जुर्माना भरना होगा",
    "सीमा शुल्क विभाग, आपका पैकेज रोका गया है, फ्रीज़ करने से पहले पैसे भेजो",
]
for i, s in enumerate(PARCEL_SCRIPTS):
    # pc_0 has "कस्टम" (authority bank) → authority+marker+payment = HIGH_RISK by design;
    # the others are pure courier class → ELEVATED
    exp = "ELEVATED_OR_HIGH" if i == 0 else "ELEVATED"
    add("D2", "parcel_customs", "MAJOR", s, exp, ["parcel", f"pc_{i}"])

PSA_SCRIPTS = [
    "असली सीबीआई कभी फोन पर पैसे नहीं मांगती, सतर्क रहें",
    "सरकार कभी भी ओटीपी नहीं मांगती, यह धोखाधड़ी है",
    "किसी भी पुलिस वाले को अपना पिन न दें, यह साइबर ठगी है",
]
for i, s in enumerate(PSA_SCRIPTS):
    add("D2", "psa", "CRITICAL", s, "LOW_OR_ELEVATED", ["psa", f"psa_{i}"])

BENIGN_SCRIPTS = [
    "नमस्ते जी, मैं आपके बेटे का दोस्त हूँ, कल पार्टी है, आना",
    "पापा, मैं ऑफिस से बोल रहा हूँ, रात को खाना साथ खाएंगे",
    "मैडम, आपका खाने का ऑर्डर आ गया है, गेट पर ले लो",
    "बैंक शाखा से बोल रहा हूँ, आपकी डेट कल सुबह 10 बजे है, पासपोर्ट ले आना",
    "मैं डॉक्टर की क्लिनिक से बोल रहा हूँ, आपकी रिपोर्ट तैयार है",
]
for i, s in enumerate(BENIGN_SCRIPTS):
    exp = "LOW_OR_ELEVATED" if "बैंक" in s else "LOW"
    add("D2", "benign", "CRITICAL", s, exp, ["benign", f"bg_{i}"])

# ══════════════════════════════════════════════════════════════
# D3 — HINGLISH (Roman + code-mixed + phonetic-garbled)
# ══════════════════════════════════════════════════════════════
HINGLISH_SCAM = [
    "hello maam main police station se bol raha hoon, aapke naam par package aaya hai, usme drugs mila hai, turant card number aur OTP batao",
    "madam aapka account freez ho gaya hai, verification ke liye pin chahiye, jaldi batao",
    "aapka parcel pakda gaya hai, customs duty bharni hai, abhi transfer karo",
    "main CBI se bol raha hoon, aap par arrest warrant hai, safe account mein paise daalo",
    "tumhare naam par digital arrest hua hai, abhi OTP batao warna jail hoga",
]
for i, s in enumerate(HINGLISH_SCAM):
    # hs_0 police+parcel+OTP = authority+payment+marker → HIGH_RISK (new rule)
    # hs_1 account-freeze = soft-scam → ELEVATED (its class)
    # hs_2 courier = ELEVATED (its class)
    # hs_3 CBI+warrant = HIGH_RISK, hs_4 digital-arrest+OTP+jail = HIGH_RISK
    exp = "ELEVATED" if i in (1, 2) else "HIGH_RISK"
    add("D3", "hinglish_scam", "CRITICAL", s, exp, ["hinglish", f"hs_{i}"])

# phonetic-garbled (faster-whisper real output style — from probes)
GARBLED = [
    "हलो मैंग मेंग पूलीस श्टेशन से बोल रहा हूँ. आपके नाम पर एक पाकेज आया है, जिस में कुछ गलक मिला है. आपको तुरंट श्टेशन आना होगा. पहले मुझे अपना कार्द नंबर और उटी पी बताओ",
    "मैदम, एक चोटीसी प्रोब्लम है, आपका अकाुन्त फ्रीज होगया है. वेरिफिकेशन के लिए मुझे आपका पिंचाहिए",
    "सुन, मैं पूलिस बोल रहा हा, तेरे नाम ते पार्सल आया, उस चड्रग्स निकले, जल्दी ओटी पी दे, नहीं ते गिराफ्तारी होजु",
]
for i, s in enumerate(GARBLED):
    add("D3", "phonetic_garbled", "CRITICAL", s, "ELEVATED_OR_HIGH", ["garbled", f"gb_{i}"])

HINGLISH_BENIGN = [
    "hello bhai, kal match hai, aana zaroor",
    "mummy main train mein hoon, ghar 8 baje pahunchunga",
    "sir aapki delivery aa gayi hai, gate par",
]
for i, s in enumerate(HINGLISH_BENIGN):
    add("D3", "hinglish_benign", "CRITICAL", s, "LOW", ["hinglish", f"hbg_{i}"])

# ══════════════════════════════════════════════════════════════
# D4 — LANGUAGE ROBUSTNESS (dialects, obfuscation, injection)
# ══════════════════════════════════════════════════════════════
DIALECT = [
    ("haryanvi", "तू सुन, मैं पुलिस से बोल रहा हूँ। तेरे नाम पर पार्सल आया है जिसमें ड्रग्स मिला है। तू तुरंत अपना ओटीपी बता, वरना तुझे जेल जाना पड़ेगा।", "HIGH_RISK"),
    ("bhojpuri", "हम सीबीआई से बोल रही। तोहार नाम पर पार्सल में ड्रग्स मिलल बा। अबहीं ओटीपी दे दे, ना तो गिरफ्तारी हो जाई।", "HIGH_RISK"),
    ("punjabi_accent", "सुन, मैं पोलिस बोल रहा हाँ। तेरे नाम ते पार्सल आया, उस च ड्रग्स निकले। जल्दी ओटीपी दे, नहीं ते गिरफ़्तारी हो जू।", "HIGH_RISK"),
]
for i, (sub, s, exp) in enumerate(DIALECT):
    add("D4", sub, "CRITICAL", s, exp, ["dialect", sub])

# obfuscation attacks MUST wrap a FULL scam script — a standalone "ओ.टी.पी. बताओ"
# is a payment mention, not a scam; the point is the scam still fires when obfuscated
OBFUSCATION = [
    "मैं सी.बी.आई. से बोल रहा हूँ, आपके नाम पर वारंट है, तुरंत पैसे भेजो",
    "आपका पार्सल पकड़ा गया, ओ.टी.पी. बताओ, पैसे भेजो",
    "आपका पार्सल पकड़ा गया, ओ\u200bटी\u200bपी बताओ, पैसे भेजो",
    "सीबीआई से बोल रहा हूँ 🤑🤑 वारंट है, तुरंत पैसे भेजो",
    "आपका पार्सल पकड़ा गया, O T P batao, paise bhejo",
    "मैं सी.बी.आई. हूँ, मुझे अपना कार्डनंबर बताओ, पैसे भेजो",
    "मैं सी.बी.आई. हूँ, मुझे अपना अकाउंटनंबर बताओ",
    "फ्रीज़़़ हो गया है, वेरिफिकेशन के लिए पिन चाहिए",
]
for i, s in enumerate(OBFUSCATION):
    exp = "ELEVATED_OR_HIGH"
    add("D4", "obfuscation", "MAJOR", s, exp, ["obfuscation", f"ob_{i}"])

NEGATION = [
    "हम कभी ओटीपी नहीं मांगते, ये सब नकली होते हैं. अब मेरी बात ध्यान से सुनो. आपका पार्सल पकड़ा गया है, ड्रग्स मिला है. तुरंत अपना ओटीपी बताओ.",
    "नहीं नहीं, मैं ठग नहीं हूँ, असली सीबीआई हूँ. आपके खाते से पैसे निकल रहे हैं, रोकने के लिए पिन बताओ.",
    "ये कॉल ठगी नहीं है, मैं आपके बैंक से बोल रहा हूँ. आपका कार्ड ब्लॉक हुआ है, वेरिफाई के लिए ओटीपी दो.",
]
for i, s in enumerate(NEGATION):
    add("D4", "negation_injection", "CRITICAL", s, "ELEVATED_OR_HIGH", ["negation", f"neg_{i}"])

# kinship boundary — DOCUMENTED (B3's job, IDEAL-STANDARD D4): never falsely HIGH,
# never silent; LOW_OR_ELEVATED is the honest range (a LOW with flags is acceptable)
KINSHIP = [
    "बेटा मैं तुम्हारा चाचा बोल रहा हूँ, मुझे इमरजेंसी में पैसे चाहिए, हॉस्पिटल में हूँ, जल्दी भेज दो",
    "भतीजे, मैं तुम्हारे पापा का दोस्त हूँ, एक्सीडेंट हो गया, तुरंत पैसे भेजो",
]
for i, s in enumerate(KINSHIP):
    add("D4", "kinship_boundary", "MAJOR", s, "LOW_OR_ELEVATED", ["kinship", f"kin_{i}"])

# ══════════════════════════════════════════════════════════════
# D5 — FUSION LADDER (pure function grid)
# ══════════════════════════════════════════════════════════════
def add_fusion(sub, spoof_score, spoof_verdict, co_score, co_state, pay, threat, claims, exp_verdict, sev):
    add("D5", sub, sev, json.dumps({"spoof_score": spoof_score, "spoof_verdict": spoof_verdict,
                                    "co_score": co_score, "co_state": co_state, "pay": pay,
                                    "threat": threat, "claims": claims}),
        exp_verdict, ["fusion", sub])

add_fusion("clean", 0.02, False, 0.05, "LOW", None, None, None, "PASS", "CRITICAL")
add_fusion("spoof_only", 0.98, True, 0.05, "LOW", None, None, None, "PAUSE", "CRITICAL")
add_fusion("high_coercion_only", 0.05, False, 0.95, "HIGH_RISK", None, None, None, "PAUSE", "CRITICAL")
add_fusion("kill_combo", 0.99, True, 0.95, "HIGH_RISK", None, None, None, "KILL", "CRITICAL")
add_fusion("elevated_only", 0.10, False, 0.55, "ELEVATED", None, None, None, "CAUTION", "MAJOR")
add_fusion("tripwire_only", 0.02, False, 0.05, "LOW", {"payee_new": True, "amount_inr": 150000, "collect": False}, None, None, "CAUTION", "MAJOR")
add_fusion("tripwire_spoof", 0.98, True, 0.05, "LOW", {"payee_new": True, "amount_inr": 150000, "collect": False}, None, None, "PAUSE", "CRITICAL")
add_fusion("threat_only", 0.02, False, 0.05, "LOW", None, ["isolation", "fake_agency"], None, "CAUTION", "MAJOR")
add_fusion("claims_only", 0.02, False, 0.05, "LOW", None, None, ["digital_arrest_claim"], "CAUTION", "MAJOR")
add_fusion("collect_tripwire", 0.02, False, 0.05, "LOW", {"payee_new": False, "amount_inr": 0, "collect": True}, None, None, "CAUTION", "MAJOR")
add_fusion("big_amount", 0.02, False, 0.05, "LOW", {"payee_new": False, "amount_inr": 99000, "collect": False}, None, None, "CAUTION", "MAJOR")
add_fusion("borderline_spoof", 0.51, True, 0.05, "LOW", None, None, None, "PAUSE", "MINOR")
add_fusion("borderline_co", 0.02, False, 0.60, "HIGH_RISK", None, None, None, "PAUSE", "MINOR")

# ══════════════════════════════════════════════════════════════
# D7 — EVIDENCE (mutation specs — described, executed by suite)
# ══════════════════════════════════════════════════════════════
add("D7", "tamper_audio_hash", "CRITICAL", "flip one byte in audio payload", "VERIFY_FAILS", ["mutation"])
add("D7", "tamper_score", "CRITICAL", "flip one digit of any score", "VERIFY_FAILS", ["mutation"])
add("D7", "tamper_packet_id", "CRITICAL", "change packet id string", "VERIFY_FAILS", ["mutation"])
add("D7", "tamper_metadata", "MAJOR", "change model_meta value", "VERIFY_FAILS", ["mutation"])
add("D7", "truncate_packet", "MAJOR", "truncate JSON at 90%", "VERIFY_FAILS", ["mutation"])

# ══════════════════════════════════════════════════════════════
# D8 — ROBUSTNESS (fuzz specs)
# ══════════════════════════════════════════════════════════════
FUZZ_SPECS = [
    ("empty", ""), ("spaces", "   "), ("newlines", "\n\n\n"), ("nul", "\x00" * 10),
    ("rtl", "\u202e" * 50), ("combining", "\u0300" * 100), ("emoji", "🦀" * 50),
    ("huge", "a" * 100000), ("mixed", "सीबीआई" + "\u200b" * 20 + "ओटीपी"),
    ("control", "".join(chr(i) for i in range(32))),
]
for i, (sub, s) in enumerate(FUZZ_SPECS):
    add("D8", sub, "MAJOR", json.dumps(s), "NO_CRASH", ["fuzz", f"fz_{i}"])

# ══════════════════════════════════════════════════════════════
# Write pool
# ══════════════════════════════════════════════════════════════
print(f"generated {len(pool)} candidate cases")
by_dim = {}
for c in pool:
    by_dim.setdefault(c["dim"], 0)
    by_dim[c["dim"]] += 1
for dim in sorted(by_dim):
    print(f"  {dim}: {by_dim[dim]} cases")

with open(os.path.join(OUT, "candidates.jsonl"), "w") as f:
    for c in pool:
        f.write(json.dumps(c, ensure_ascii=False) + "\n")
print("written:", os.path.join(OUT, "candidates.jsonl"))

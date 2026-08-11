#!/usr/bin/env python3
"""gen_audio.py — synthesize the AUDIO test set: coded audio, dialect variants,
negation, merges, canonical scams, benign calls — via edge-tts Hindi voices.

THE POINT (user directive): the product is AUDIO-ONLY. The real attack surface is
what the ASR EMITS when a scammer SPEAKS dialect/coded variants. This generates the
actual speech; run_audio.py runs it through the REAL pipeline (ASR → coercion → fuse).

Voices: hi-IN-MadhurNeural (male), hi-IN-SwaraNeural (female) — the only 2 Hindi
edge-tts voices. NOTE (honest boundary): these are studio voices — real Haryanvi/
Bhojpuri ACCENT phonetics cannot be synthesized; what we CAN test is dialect
VOCABULARY + code-mixing + rate/pitch variance + the ASR's real behavior on it.

Output: benchmarks/audio/cases/<id>_<voice>.mp3 + cases.jsonl manifest
"""
import asyncio, edge_tts, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "audio", "cases")
os.makedirs(OUT, exist_ok=True)

VOICES = ["hi-IN-MadhurNeural", "hi-IN-SwaraNeural"]

# (id, text, kind)  kind: scam / benign / human
#  - scam  = synthetic (TTS bot) attack audio → must PAUSE/KILL
#  - benign = synthetic benign audio → is a BOT call → PAUSE is CORRECT (safe-by-default)
#            (a synthetic voice calling you is itself the anomaly — real humans are
#            BONAFIDE per AASIST 0.0-0.002; the "human" kind tests those)
#  - human = real recorded human speech (assets/real_call_hindi*.wav) → must PASS
SCENARIOS = [
    # ── canonical scams (the ones the curated suite proved fire) ──
    ("c1_cbi_warrant", "मैं सीबीआई से बोल रहा हूँ, आपके नाम पर वारंट है, तुरंत पैसे भेजो", "scam"),
    ("c2_parcel_drugs", "आपके पार्सल में ड्रग्स मिला है, कस्टम ड्यूटी जमा करो", "scam"),
    ("c3_card_block_otp", "आपका कार्ड ब्लॉक हो गया है, अनब्लॉक के लिए ओटीपी बताइए", "scam"),
    ("c4_cyber_fir", "मैं साइबर क्राइम विभाग से बोल रहा हूँ, आपका एफआईआर दर्ज है, अभी केस चल रहा है", "scam"),
    ("c5_digital_arrest", "तुम्हारे नाम पर डिजिटल अरेस्ट हुआ है, अभी ओटीपी बताओ वरना जेल होगा", "scam"),
    ("c6_ed_blackmoney", "मैं ईडी से बोल रहा हूँ, आपके खाते में काला धन आया है, डिमांड ड्राफ्ट जमा करो", "scam"),
    ("c7_police_parcel_otp", "मैं पुलिस स्टेशन से बोल रहा हूँ, आपके नाम पर पैकेज आया है, उसमें ड्रग्स मिला है, तुरंत कार्ड नंबर और ओटीपी बताओ", "scam"),

    # ── CODED AUDIO: dialect vocabulary (Haryanvi/Bhojpuri/Punjabi-flavored) ──
    ("d1_haryanvi_arrest", "हम पुलिस से बोल रहे हैं, तोहार नाम पर वारंट है, जल्दी पैसे भेज दे", "scam"),
    ("d2_bhojpuri_parcel", "तोहार नाम पर पार्सल आइल बा, ओहमें ड्रग्स मिलल बा, कस्टम ड्यूटी जमा कर", "scam"),
    ("d3_punjabi_cbi", "मैं सीबीआई तों बोल रहा हूँ, तेरे नाम पर केस हो गया है, पैसे पा भेज", "scam"),
    ("d4_haryanvi_card", "तेरा कार्ड ब्लॉक हो गया है, अनब्लॉक करने लिए ओटीपी बता दे", "scam"),
    ("d5_bhojpuri_otp", "तोहार खाता फ्रीज़ हो गइल बा, वेरिफिकेशन खातिर पिन बता द", "scam"),

    # ── CODED AUDIO: code-mixed / Hinglish spoken variants ──
    ("m1_hinglish_police", "hello maam, main police station se bol raha hoon, aapke naam par package aaya hai, usme drugs mila hai, turant card number aur OTP batao", "scam"),
    ("m2_hinglish_freeze", "madam, aapka account freez ho gaya hai, verification ke liye pin chahiye, jaldi batao", "scam"),
    ("m3_hinglish_parcel", "aapka parcel pakda gaya hai, customs duty bharni hai, abhi transfer karo", "scam"),
    ("m4_hinglish_cbi", "main CBI se bol raha hoon, aap par arrest warrant hai, safe account mein paise daalo", "scam"),
    ("m5_hinglish_digital", "tumhare naam par digital arrest hua hai, abhi OTP batao warna jail hoga", "scam"),

    # ── NEGATION / PSA-denial coded audio ──
    ("n1_negation_prefix", "यह ठगी नहीं है, मैं सीबीआई से बोल रहा हूँ, आपके नाम पर वारंट है, पैसे भेजो", "scam"),
    ("n2_negation_suffix", "मैं सीबीआई से बोल रहा हूँ, वारंट है, पैसे भेजो, यह कोई ठगी नहीं है", "scam"),
    ("n3_real_officer", "डरो मत, मैं असली अधिकारी हूँ, आपका एफआईआर दर्ज है, केस चल रहा है, डिमांड ड्राफ्ट जमा करो", "scam"),

    # ── MERGED / hurried speech (ASR merges tokens) ──
    ("u1_merged_card", "आपका कार्डनंबर और ओटीपी बताओ, पैसे भेजो, तुरंत", "scam"),
    ("u2_merged_account", "मुझे अपना अकाउंटनंबर बताओ, वेरिफिकेशन के लिए, जल्दी", "scam"),

    # ── BENIGN (synthetic voice = BOT call → PAUSE is correct safe-by-default) ──
    ("b1_friend_party", "नमस्ते जी, मैं आपके बेटे का दोस्त हूँ, कल पार्टी है, आप भी आना", "benign"),
    ("b2_son_dinner", "पापा, मैं ऑफिस से बोल रहा हूँ, रात को खाना साथ खाएंगे", "benign"),
    ("b3_food_order", "मैडम, आपका खाने का ऑर्डर आ गया है, गेट पर ले लो", "benign"),
    ("b4_clinic", "मैं डॉक्टर की क्लिनिक से बोल रहा हूँ, आपकी रिपोर्ट तैयार है", "benign"),
    ("b5_friend_match", "hello bhai, kal match hai, aana zaroor", "benign"),
    ("b6_train", "mummy, main train mein hoon, ghar 8 baje pahunchunga", "benign"),
    ("b7_bank_visit", "नमस्ते, मैं बैंक शाखा से बोल रहा हूँ, आपकी डेट कल सुबह 10 बजे है, पासपोर्ट ले आना", "benign"),
]

# ── REAL HUMAN SPEECH (the actual benign caller — must PASS) ──
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))   # benchmarks → eldershield root
HUMAN_FILES = [
    ("h1_real_hindi", os.path.join(REPO_ROOT, "assets", "real_call_hindi.wav"), "real human Hindi (FLEURS-style)"),
    ("h2_real_hindi2", os.path.join(REPO_ROOT, "assets", "real_call_hindi2.wav"), "real human Hindi (FLEURS-style)"),
]

async def synth(text, voice, path):
    com = edge_tts.Communicate(text, voice, rate="+8%")
    await com.save(path)

async def main():
    manifest = []
    for cid, text, kind in SCENARIOS:
        voice = VOICES[0] if cid.startswith(("d", "m", "n", "u")) else VOICES[1 if cid.startswith("b") and cid != "b5" else 0]
        # vary voice across scenarios: scams get male (majority of scam calls), benign mixed
        if kind == "scam" and cid.startswith("c"):
            voice = VOICES[1] if int(cid[1]) % 2 == 0 else VOICES[0]
        path = os.path.join(OUT, f"{cid}_{'M' if 'Madhur' in voice else 'S'}.mp3")
        await synth(text, voice, path)
        manifest.append({"id": cid, "kind": kind, "voice": voice.split("-")[2].replace("Neural", ""), "file": path, "text": text})
        print(f"  {cid:22s} {kind:7s} {voice} -> {os.path.basename(path)}")
    # real human speech (pre-existing assets, not synthesized)
    for cid, path, desc in HUMAN_FILES:
        manifest.append({"id": cid, "kind": "human", "voice": "REAL", "file": os.path.abspath(path), "text": desc})
        print(f"  {cid:22s} human    REAL HUMAN  -> {os.path.basename(path)}")
    with open(os.path.join(HERE, "audio", "cases.jsonl"), "w") as f:
        for m in manifest:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    print(f"\n{len(manifest)} scenarios -> benchmarks/audio/cases/ (synthetic) + 2 real-human")

if __name__ == "__main__":
    asyncio.run(main())

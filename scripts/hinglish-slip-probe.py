#!/usr/bin/env python3
"""hinglish-slip-probe.py — does the coercion layer catch Roman-script Hinglish scams?

Three scripts designed to SLIP through (Roman-only phrasing):
  slip1: police/package/card+OTP (classic vishing, no Devanagari keywords)
  slip2: soft account-freeze + PIN ask (no authority ladder, no arrest)
  slip3: kinship emergency (no authority/arrest at all — pure social-engineering)
"""
import sys, os, asyncio, edge_tts
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from coercion import CoercionDetector

SCRIPTS = {
    "slip1_vishing": (
        "Hello ma'am, main police station se bol raha hoon. Aapke naam par ek package aaya hai "
        "jisme kuch galat mila hai. Aapko turant station aana hoga. Pehle mujhe apna card number "
        "aur OTP batao, main verify kar loon. Jaldi karo, time nahi hai."
    ),
    "slip2_soft": (
        "Madam, ek chhoti si problem hai. Aapka account freez ho gaya hai. Verification ke liye "
        "mujhe aapka PIN chahiye. Bas 2 minute ka kaam hai, koi tension nahi."
    ),
    "slip3_kinship": (
        "Beta, main tumhara chacha bol raha hoon. Mujhe emergency mein paise chahiye, hospital "
        "mein hoon. Jaldi bhej do, baad mein sab samjhaunga."
    ),
}


async def gen(text, name):
    tts = edge_tts.Communicate(text, "hi-IN-MadhurNeural")
    await tts.save(f"/tmp/{name}.mp3")


def main():
    for name, s in SCRIPTS.items():
        asyncio.run(gen(s, name))
    det = CoercionDetector()
    for name in SCRIPTS:
        r = det.analyze(f"/tmp/{name}.mp3")
        print(f"{name:14s} {r['risk_state']:10s} score={r['coercion_score']:.2f} "
              f"hits={sorted(r['vector_hits'].keys())}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""test_fusion.py — robustness battery for the B2/B4 fusion layers.

Scenarios:
  A1 digital-arrest (CBI/parcel/drugs)      -> expect SPOOF + HIGH_RISK
  A2 OTP scam (bank caller)                  -> expect HIGH_RISK (payment+urgency+authority)
  A3 parcel scam (courier, no authority)     -> expect ELEVATED/HIGH
  B1 real Hindi call (food)                  -> expect BONAFIDE + LOW
  B2 real Hindi call 2 (FLEURS)              -> expect BONAFIDE + LOW
"""
import asyncio, json, os, sys, time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from engine import KavachEngine
from coercion import CoercionDetector

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "demo", "evidence")
ATTACKS = os.path.join(HERE, "demo", "attacks")

TEXTS = {
    "a2_otp": "नमस्ते, मैं आपके बैंक से बोल रहा हूँ। आपका कार्ड ब्लॉक हो गया है। ओटीपी भेजा है, जल्दी बताइए वरना पैसा कट जाएगा।",
    "a3_parcel": "नमस्ते, यह कूरियर कंपनी है। आपका पार्सल सीमा शुल्क में फंस गया है। तुरंत 2000 रुपये जमा करो, नहीं तो पार्सल वापस चला जाएगा।",
}

def gen(text, name):
    import edge_tts
    out = os.path.join(ATTACKS, f"{name}.mp3")
    async def _run():
        tts = edge_tts.Communicate(text, "hi-IN-MadhurNeural")
        await tts.save(out)
    asyncio.run(_run())
    return out

def main():
    eng = KavachEngine()
    det = CoercionDetector()

    # generate attack variants
    paths = {"a1_digital_arrest": "/tmp/attack_digital_arrest.mp3"}
    for name, text in TEXTS.items():
        paths[name] = gen(text, name)

    paths["b1_real"] = os.path.join(HERE, "assets", "real_call_hindi.wav")
    paths["b2_real"] = os.path.join(HERE, "assets", "real_call_hindi2.wav")

    results = []
    for name, p in paths.items():
        t0 = time.time()
        er = eng.analyze(p)
        cr = det.analyze(p)
        dt = time.time() - t0
        verdict = "SPOOF" if er["spoof"] else "BONAFIDE"
        results.append({
            "scenario": name, "spoof": verdict, "spoof_score": er["score"],
            "coercion": cr["risk_state"], "coercion_score": cr["coercion_score"],
            "cues": sorted(cr["vector_hits"].keys()), "total_s": round(dt, 1),
        })
        print(f"{name:18s} {verdict:9s} {er['score']:.3f}  {cr['risk_state']:10s} {cr['coercion_score']:.2f}  cues={sorted(cr['vector_hits'].keys())}  {dt:.1f}s")

    # save
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "test-fusion-battery.json"), "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\nresults ->", os.path.join(OUT, "test-fusion-battery.json"))

if __name__ == "__main__":
    main()

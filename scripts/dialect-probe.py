#!/usr/bin/env python3
"""dialect-probe.py - how do accents/dialects/slang distort the transcript?

Same digital-arrest scam, spoken 6 ways. Maps what faster-whisper hi emits so
the normalization layer can be built on EVIDENCE, not guesses.

  d1 haryanvi     - "तू म्हारा" / "करा" / "के" (Haryanvi case-marking)
  d2 bhojpuri     - "हम" (I) / "बा" (is) / "अइहा" (come)
  d3 mumbai-hindi - "मैं पुलिस से बोलता हूँ" + "यार" filler + fast
  d4 punjabi-accent - "पोलिस" / "गिरफ़्तार" (retroflex-flap) / "जल्दी करो"
  d5 marathi-accent - "आहे" suffix / "तुरंत" → "तुरांत" / "पैसे" → "पैशे"
  d6 bengali-accent - "बोल्छि" / "पोलिस" / "टाका" (money)
"""
import sys, os, asyncio, edge_tts, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

VOICES = {
    "d1_haryanvi": "hi-IN-MadhurNeural",
    "d2_bhojpuri": "hi-IN-SwaraNeural",
    "d3_mumbai": "hi-IN-MadhurNeural",
    "d4_punjabi": "hi-IN-SwaraNeural",
    "d5_marathi": "hi-IN-MadhurNeural",
    "d6_bengali": "hi-IN-SwaraNeural",
}

SCRIPTS = {
    "d1_haryanvi": "तू सुन, मैं पुलिस से बोल रहा हूँ। तेरे नाम पर पार्सल आया है जिसमें ड्रग्स मिला है। तू तुरंत अपना ओटीपी बता, वरना तुझे जेल जाना पड़ेगा।",
    "d2_bhojpuri": "हम सीबीआई से बोल रही। तोहार नाम पर पार्सल में ड्रग्स मिलल बा। अबहीं ओटीपी दे दे, ना तो गिरफ्तारी हो जाई।",
    "d3_mumbai": "यार सुन ना, मैं पुलिस से बोलता हूँ। तेरे पार्सल में ड्रग्स निकला है। जल्दी कर, ओटीपी भेज, टाइम मत ले।",
    "d4_punjabi": "सुन, मैं पोलिस बोल रहा हाँ। तेरे नाम ते पार्सल आया, उस च ड्रग्स निकले। जल्दी ओटीपी दे, नहीं ते गिरफ़्तारी हो जू।",
    "d5_marathi": "ऐ, मी पोलिस बोलतोय. तुझ्या नावावर पार्सल आलंय, त्यात ड्रग्स सापडलं. तुरांत ओटीपी दे, नाही तर अटक होईल.",
    "d6_bengali": "शुनो, मैं पुलिस बोल्छि। तोमार नामे पार्सल एसेछे, ओते ड्रग्स पेयेछे। तोड़ारी ओटीपी दाओ, नाहोले गिरफ्तारी होबे।",
}


async def gen(text, name, voice):
    tts = edge_tts.Communicate(text, voice)
    await tts.save(f"/tmp/{name}.mp3")


def main():
    from faster_whisper import WhisperModel
    for name, voice in VOICES.items():
        asyncio.run(gen(SCRIPTS[name], name, voice))
    asr = WhisperModel("small", device="cpu", compute_type="int8")
    for name in VOICES:
        segs, _ = asr.transcribe(f"/tmp/{name}.mp3", language="hi")
        txt = " ".join(s.text.strip() for s in segs)
        print(f"=== {name} ===")
        print(json.dumps(txt, ensure_ascii=False))
        print()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""hinglish-slip-probe-transcripts.py - dump what ASR actually produces for the slips."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from faster_whisper import WhisperModel

asr = WhisperModel("small", device="cpu", compute_type="int8")
for name in ["slip1_vishing", "slip2_soft", "slip3_kinship"]:
    segs, info = asr.transcribe(f"/tmp/{name}.mp3", language="hi")
    txt = " ".join(s.text.strip() for s in segs)
    print(f"=== {name} ===")
    print(json.dumps(txt, ensure_ascii=False))
    print()

#!/usr/bin/env python3
"""demo_ui.py — ElderShield R1 demo: attack-gen + detection UI + evidence packet.

Flow: record/upload a wav → engine.analyze() → spoof verdict + score + latency
→ PAUSE intervention (block UPI intent) → evidence packet JSON (audit trail).

Run: ~/r2-venv/bin/python demo_ui.py  → gradio on :7860
"""
import os, sys, json, time, tempfile
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
from engine import ElderShieldEngine  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ATTACK_DIR = os.path.join(HERE, "demo", "attacks")
os.makedirs(ATTACK_DIR, exist_ok=True)

_ENGINE = None
def engine():
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = ElderShieldEngine()
    return _ENGINE

def gen_attack(text: str, voice: str = "hi-IN-MadhurNeural") -> str:
    """Generate a Hindi voice-clone attack via edge-tts (demo tooling, disclosed)."""
    import edge_tts, asyncio
    out = os.path.join(ATTACK_DIR, f"attack_{int(time.time())}.mp3")
    async def _run():
        tts = edge_tts.Communicate(text, voice)
        await tts.save(out)
    asyncio.run(_run())
    return out

def analyze_wav(path: str) -> dict:
    eng = engine()
    res = eng.analyze(path)
    res["verdict"] = "SPOOF" if res["spoof"] else "BONAFIDE"
    res["action"] = "PAUSE — verify caller identity" if res["spoof"] else "PASS — proceed"
    res["evidence_packet"] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "file": os.path.basename(path),
        "score": res["score"],
        "crop_scores": res["crop_scores"],
        "model": "AASIST-hindi (3-crop majority vote)",
        "latency_ms": res["latency_ms"],
        "chain": ["audio_in", "crop_1", "crop_2", "crop_3", "vote", "verdict", "intervention"],
    }
    return res

def ui(audio_path, attack_text):
    """Gradio handler: returns verdict panel + evidence."""
    if audio_path is None:
        return "Upload or record audio first", {}
    res = analyze_wav(audio_path)
    panel = (
        f"## Verdict: **{res['verdict']}** ({res['score']:.3f})\n\n"
        f"- Spoof score: `{res['score']:.4f}` (0=real, 1=clone)\n"
        f"- Crops: `{res['crop_scores']}`\n"
        f"- Latency: `{res['latency_ms']}ms`\n"
        f"- **Action: {res['action']}**"
    )
    return panel, res["evidence_packet"]

if __name__ == "__main__":
    import gradio as gr
    demo = gr.Interface(
        fn=ui,
        inputs=[
            gr.Audio(type="filepath", label="Real call recording (or record live)"),
            gr.Textbox(value="नमस्ते, मैं बैंक से बोल रहा हूँ। आपका OTP क्या है?", label="Attack text (Hindi)"),
        ],
        outputs=[
            gr.Markdown(label="Detection result"),
            gr.JSON(label="Evidence packet (audit trail)"),
        ],
        title="ElderShield — Real-Time Voice-Clone Detection for UPI & Voice Banking",
        description="AASIST-hindi, 3-crop majority vote, <500ms. Spoof score → PAUSE intervention → evidence packet.",
    )
    demo.launch(server_name="127.0.0.1", server_port=7860)

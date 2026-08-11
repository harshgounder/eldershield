#!/usr/bin/env python3
"""verify-shot-content.py — DOM-level proof that the attack/real shots contain
the real verdict. Grabs the rendered output text + evidence JSON after each run."""
import os

ASSETS = os.path.expanduser("~/iic-3/kavach/assets")
BASE = "http://127.0.0.1:7860"

from playwright.sync_api import sync_playwright

def set_file(pg, path):
    pg.set_input_files("input[type=file]", path)
    pg.wait_for_timeout(1500)

def run_case(pg, path, label):
    set_file(pg, path)
    pg.get_by_text("Submit").click()
    pg.wait_for_timeout(15000)
    # grab all visible text (gradio renders markdown + JSON as text nodes)
    txt = pg.inner_text("body")
    print(f"=== {label} ===")
    # print the interesting window
    for key in ["SPOOF", "BONAFIDE", "Verdict", "score", "Latency", "PAUSE", "PASS"]:
        if key in txt:
            idx = txt.index(key)
            print(f"  [{key}] ...{txt[max(0,idx-40):idx+90].strip()[:130]}")
    pg.get_by_text("Clear").first.click()
    pg.wait_for_timeout(1000)

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1360, "height": 900})
    pg.goto(BASE, wait_until="networkidle", timeout=60000)
    pg.wait_for_timeout(2500)
    run_case(pg, os.path.join(ASSETS, "clone_attack.mp3"), "ATTACK")
    run_case(pg, os.path.join(ASSETS, "real_call_hindi.wav"), "REAL")
    b.close()
print("DONE")

#!/usr/bin/env python3
"""capture-detection-shots.py - playwright UI walkthrough for Kavach R1 assets.
Drives the REAL gradio UI (not API): loads page → uploads attack → clicks submit →
screenshots the verdict panel (the money shot) → resets → uploads real call →
screenshots the BONAFIDE state.

Requires: gradio server running on :7860 (demo_ui.py), and playwright installed.
"""
import os

ASSETS = os.path.expanduser("~/iic-3/kavach/assets")
BASE = "http://127.0.0.1:7860"

from playwright.sync_api import sync_playwright

def set_file(pg, selector, path):
    """gradio Audio uses an <input type=file> - set via set_input_files."""
    pg.set_input_files(selector, path)
    pg.wait_for_timeout(1500)

def click_submit_and_wait(pg):
    pg.get_by_text("Submit").click()
    pg.wait_for_timeout(12000)  # model load + inference on first run

def main():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1360, "height": 900})
        pg.goto(BASE, wait_until="networkidle", timeout=60000)
        pg.wait_for_timeout(2500)

        # 1. landing shot (already have, retake for consistency)
        pg.screenshot(path=os.path.join(ASSETS, "shot_01_landing.png"))
        print("shot_01_landing.png saved")

        # 2. ATTACK case - the money shot
        set_file(pg, "input[type=file]", os.path.join(ASSETS, "clone_attack.mp3"))
        click_submit_and_wait(pg)
        pg.screenshot(path=os.path.join(ASSETS, "shot_02_attack_detected.png"))
        print("shot_02_attack_detected.png saved")

        # 3. REAL call case - the contrast
        pg.get_by_text("Clear").first.click()
        pg.wait_for_timeout(800)
        set_file(pg, "input[type=file]", os.path.join(ASSETS, "real_call_hindi.wav"))
        click_submit_and_wait(pg)
        pg.screenshot(path=os.path.join(ASSETS, "shot_03_real_bonafide.png"))
        print("shot_03_real_bonafide.png saved")

        b.close()

if __name__ == "__main__":
    main()

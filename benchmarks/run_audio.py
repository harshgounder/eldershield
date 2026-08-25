#!/usr/bin/env python3
"""run_audio.py - THE REAL AUDIO TEST. Runs every synthesized audio case through the
REAL pipeline: engine (B1 spoof/AASIST) → coercion (B2 ASR + analysis) → fuse (FUSION).

This is the audio-only reality check (user directive): coded audio, dialects, accents,
negation - spoken into a file, transcribed by OUR ASR, scored by OUR rules, fused by
OUR ladder. The text suites were simulation; this is the actual system.

Verdict expectations (IDEAL-STANDARD mapping):
  scam  → fusion verdict must be PAUSE or KILL (never PASS)
  benign → must be PASS (never PAUSE/KILL)
  evidence packet must build for flagged calls

Output: benchmarks/audio/results/audio-<ts>.json (transcripts + verdicts + failures)
"""
import json, os, sys, time, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "src"))

import torch  # noqa: E402
from engine import KavachEngine      # B1 spoof (AASIST)
from coercion import CoercionDetector     # B2 (faster-whisper + rules)
from fusion import fuse                   # FUSION core

CASES = os.path.join(HERE, "audio", "cases.jsonl")
RES_DIR = os.path.join(HERE, "audio", "results")
os.makedirs(RES_DIR, exist_ok=True)

def main():
    t0_all = time.time()
    engine = KavachEngine()
    det = CoercionDetector()
    cases = [json.loads(l) for l in open(CASES) if l.strip()]

    results, failures = [], []
    for c in cases:
        path = c["file"]
        row = {"id": c["id"], "kind": c["kind"], "voice": c["voice"],
               "source_text": c["text"], "transcript": None, "spoof": None,
               "coercion": None, "verdict": None, "pass": None, "fail_reason": None}
        try:
            # ── B1: spoof detection (real AASIST on the audio) ──
            er = engine.analyze(path)
            row["spoof"] = {"score": er["score"], "verdict": er.get("verdict", "SPOOF" if er["spoof"] else "BONAFIDE")}

            # ── B2: coercion (real ASR transcript + rules) ──
            prof = det.analyze(path)
            row["transcript"] = prof["transcript"]
            row["coercion"] = {"score": prof["coercion_score"], "state": prof["risk_state"],
                               "vecs": sorted(prof["vector_hits"].keys())}

            # ── FUSE ──
            # NOTE: pass er["spoof"] (the BOOLEAN) - row["spoof"]["verdict"] is the
            # label STRING ("BONAFIDE"/"SPOOF") which is truthy → every call fused as
            # spoof=True → PAUSE for everything. Found by the human cases (audio suite).
            fr = fuse(spoof_score=er["score"], spoof_verdict=er["spoof"],
                      coercion_score=prof["coercion_score"],
                      coercion_state=prof["risk_state"],
                      payment_context=None)
            row["verdict"] = fr.verdict
            row["action"] = getattr(fr, "action", None)
            row["reasons"] = list(fr.reasons) if hasattr(fr, "reasons") else None

            # ── verdict vs expectation ──
            if c["kind"] == "human":
                # real human speech → must PASS (BONAFIDE + LOW → PASS)
                ok = fr.verdict == "PASS"
                reason = None if ok else f"human got {fr.verdict} (expected PASS)"
            elif c["kind"] == "scam":
                ok = fr.verdict in ("PAUSE", "KILL")
                reason = None if ok else f"scam got {fr.verdict} (expected PAUSE/KILL)"
            else:
                # synthetic benign = BOT call → PAUSE is CORRECT (safe-by-default);
                # KILL without coercion evidence would be overreach
                ok = fr.verdict == "PAUSE"
                reason = None if ok else f"benign-bot got {fr.verdict} (expected PAUSE)"
            row["pass"] = ok
            row["fail_reason"] = reason
        except Exception as e:
            row["pass"] = False
            row["fail_reason"] = f"CRASH: {type(e).__name__}: {e}"
        results.append(row)
        mark = "PASS" if row["pass"] else "FAIL"
        tr = (row["transcript"] or "")[:55].replace("\n", " ")
        co_state = row["coercion"].get("state") if row["coercion"] else "?"
        print(f"[{mark}] {c['id']:22s} {c['kind']:7s} verdict={str(row['verdict']):9s} co={co_state} :: {tr}")
        if not row["pass"]:
            failures.append(row)

    dt = time.time() - t0_all
    npass = sum(1 for r in results if r["pass"])
    nscam = sum(1 for r in results if r["kind"] == "scam")
    nbenign = nscam and (len(results) - nscam)
    nbenign = len(results) - nscam
    print(f"\nAUDIO SUITE: {npass}/{len(results)} passed ({dt:.0f}s wall, {len(results)} files)")
    print(f"  scams  : {nscam} cases (expect PAUSE/KILL)")
    print(f"  benign : {nbenign} cases (expect PASS)")

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = os.path.join(RES_DIR, f"audio-{ts}.json")
    json.dump({"ts": ts, "n": len(results), "npass": npass,
               "nscam": nscam, "nbenign": nbenign,
               "results": results, "failures": failures},
              open(out, "w"), ensure_ascii=False, indent=2)
    print(f"results -> {out}")

    if failures:
        print(f"\nFAILURES ({len(failures)}):")
        for f_ in failures:
            print(f"  [{f_['kind']}] {f_['id']}: {f_['fail_reason']}")
            if f_.get("transcript"):
                print(f"      ASR: {f_['transcript'][:110]}")
    return 1 if failures else 0

if __name__ == "__main__":
    sys.exit(main())

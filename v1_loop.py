#!/usr/bin/env python3
"""v1_loop.py — Kavach v0.1: the FULL product loop, end to end.

recognize → interrupt → verify → package → report

  recognize : B1 spoof (engine.py) + B2 coercion (coercion.py) on the audio
  fuse      : FUSION core (fusion.py) → one verdict + one action
  interrupt : verdict PAUSE/KILL → intervention state (family challenge)
  verify    : trusted-contact decision (simulated: approve / challenge / kill)
  package   : B4 evidence packet (evidence.py, sha256 chain) + 1930-ready PDF
  report    : packet id + report target printed (one-tap handoff)

Usage:
  ~/r2-venv/bin/python v1_loop.py <audio.wav|mp3> [--payee-new] [--amount 150000]
  ~/r2-venv/bin/python v1_loop.py --demo   # runs the 5-scenario battery through the loop

Honesty: family decision is SIMULATED (no real push channel yet). The loop is real.
"""
import argparse, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))

from engine import KavachEngine      # B1
from coercion import CoercionDetector     # B2
from fusion import fuse                   # FUSION core
from evidence import build_and_save       # B4


def run_loop(audio_path, payment_context=None, family_decision="challenge"):
    """One full pass through the loop. Returns the full state dict."""
    eng = KavachEngine()
    det = CoercionDetector()

    # ---- recognize (B1 + B2 in parallel-ish sequence)
    t0 = time.time()
    er = eng.analyze(audio_path)
    cr = det.analyze(audio_path)
    analyze_s = round(time.time() - t0, 2)

    # ---- fuse (the six departments → one verdict)
    threat = [k for k in ("isolation", "fake_agency", "safe_account", "secrecy") if k in cr.get("vector_hits", {})]
    claims = [k for k in ("arrest", "parcel", "digital_arrest") if k in cr.get("vector_hits", {})]
    fr = fuse(spoof_score=er["score"], spoof_verdict=er["spoof"],
              coercion_score=cr["coercion_score"], coercion_state=cr["risk_state"],
              payment_context=payment_context, threat_signals=threat, factcheck_claims=claims)

    # ---- interrupt + verify (family challenge — simulated decision)
    if fr.verdict in ("PAUSE", "KILL"):
        intervention = "ACTIVE"
        if family_decision == "approve":
            outcome = "APPROVED — transfer allowed (family override, logged)"
            action_taken = "continue"
        elif family_decision == "kill":
            outcome = "BLOCKED — transfer stopped, report to 1930"
            action_taken = "blocked"
        else:
            outcome = "CHALLENGED — call family now; transfer on hold"
            action_taken = "held"
    else:
        intervention = "NONE"
        outcome = "no intervention"
        action_taken = "proceed"

    # ---- package (B4) + report
    ev = None
    if fr.verdict in ("PAUSE", "KILL") or True:  # always package — evidence is the differentiator
        ev = build_and_save(audio_path, er, cr, os.path.join(HERE, "demo", "evidence"))

    state = {
        "audio": os.path.basename(audio_path),
        "recognize": {"spoof": er["verdict"] if "verdict" in er else ("SPOOF" if er["spoof"] else "BONAFIDE"),
                      "spoof_score": er["score"], "latency_ms": er["latency_ms"],
                      "coercion": cr["risk_state"], "coercion_score": cr["coercion_score"],
                      "cues": sorted(cr["vector_hits"].keys()), "analyze_s": analyze_s},
        "fusion": fr.to_dict(),
        "intervention": {"state": intervention, "family_decision": family_decision,
                         "outcome": outcome, "action_taken": action_taken},
        "evidence": {"packet_id": ev["packet"]["packet_id"], "chain_ok": ev["chain_ok"],
                     "pdf": ev["pdf"]} if ev else None,
        "report_target": "1930 / NCRP (money lost) · Chakshu (no money lost)" if fr.verdict in ("PAUSE", "KILL") else None,
    }
    return state


SCENARIOS = {
    "a1_digital_arrest": dict(path="demo/attacks/a1_digital_arrest.mp3",
                              pay={"payee_new": True, "amount_inr": 150000, "collect": False},
                              decision="challenge", expect="KILL"),
    "a2_otp":            dict(path="demo/attacks/a2_otp.mp3",
                              pay={"payee_new": False, "amount_inr": 0, "collect": False},
                              decision="approve", expect="KILL"),
    "a3_parcel":         dict(path="demo/attacks/a3_parcel.mp3",
                              pay={"payee_new": True, "amount_inr": 50000, "collect": False},
                              decision="kill", expect="PAUSE"),
    "b1_real":           dict(path="assets/real_call_hindi.wav",
                              pay=None, decision="approve", expect="PASS"),
    "b2_real":           dict(path="assets/real_call_hindi2.wav",
                              pay=None, decision="approve", expect="PASS"),
}


def main():
    ap = argparse.ArgumentParser(description="Kavach v0.1 — full loop")
    ap.add_argument("audio", nargs="?", help="audio file to run through the loop")
    ap.add_argument("--payee-new", action="store_true")
    ap.add_argument("--amount", type=int, default=0)
    ap.add_argument("--decision", choices=["approve", "challenge", "kill"], default="challenge")
    ap.add_argument("--demo", action="store_true", help="run the 5-scenario battery")
    args = ap.parse_args()

    if args.demo:
        results = []
        ok = True
        for name, sc in SCENARIOS.items():
            p = os.path.join(HERE, sc["path"])
            if not os.path.exists(p):
                print(f"SKIP {name}: missing {p}")
                continue
            st = run_loop(p, payment_context=sc["pay"], family_decision=sc["decision"])
            verdict = st["fusion"]["verdict"]
            exp = sc["expect"]
            mark = "PASS" if verdict == exp else f"EXPECTED {exp}"
            if verdict != exp:
                ok = False
            results.append({"scenario": name, "verdict": verdict, "expected": exp,
                            "coercion": st["recognize"]["coercion"], "packet": st["evidence"]["packet_id"]})
            print(f"{name:20s} {verdict:8s} (exp {exp:8s}) {mark}  packet={st['evidence']['packet_id']}")
        with open(os.path.join(HERE, "demo", "evidence", "v1-loop-battery.json"), "w") as f:
            json.dump(results, f, indent=2)
        print("ALL SCENARIOS MATCH" if ok else "MISMATCHES PRESENT")
        return 0 if ok else 1

    if not args.audio:
        ap.error("provide an audio path or --demo")
    pay = None
    if args.payee_new or args.amount:
        pay = {"payee_new": args.payee_new, "amount_inr": args.amount, "collect": False}
    st = run_loop(args.audio, payment_context=pay, family_decision=args.decision)
    print(json.dumps(st, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

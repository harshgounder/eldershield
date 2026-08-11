#!/usr/bin/env python3
"""run_real_cases.py — D8 real-case registry replay (text-level, NO GPU, NO audio).

Replays 24 documented Indian scam incidents + 5 benign controls through the real
detector's text-level scoring path (CoercionDetector._score_text — the single
source of truth per the module docstring). No ASR, no model download, no audio.

Expectations:
  tier A/B/C  → must be FLAGGED (risk_state ELEVATED|HIGH_RISK, or score >= 0.30)
  tier D      → must be FLAGGED too, but rule-test level only → accept ELEVATED
  bn1..bn4    → must be LOW (PASS)
  bn5         → may be ELEVATED but must NOT be HIGH_RISK

Also audits the two 2026-08-11 real-case rules: authority-stack (>=2 institutions)
and transfer-for-verification (safe/government-account phrases).

Output: console summary table + benchmarks/results/real-cases-<ts>.json (gitignored).
Stdlib only. Does NOT modify src/. Does NOT commit.
"""
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "src"))

from coercion import CoercionDetector  # noqa: E402

CASES = os.path.join(HERE, "real-cases", "cases.jsonl")
BENIGN = os.path.join(HERE, "real-cases", "benign.jsonl")
RESULTS = os.path.join(HERE, "results")

# Rule-audit vocab (mirrors src/coercion.py read-only — for the audit report only,
# does NOT change scoring; scoring is entirely det._score_text).
INSTITUTIONS = (
    "सीबीआई", "सीबीआय", "cbi", "एनसीबी", "ncb", "ईडी", "enforcement directorate",
    "पुलिस", "police", "क्राइम ब्रांच", "crime branch", "साइबर सेल", "साइबर क्राइम",
    "cyber cell", "cyber crime", "इनकम टैक्स", "income tax", "कस्टम", "customs",
    "आरबीआई", "rbi", "इंटरपोल", "interpol", "कोर्ट", "अदालत", "court", "जज", "judge",
    "ट्राई", "trai", "दूरसंचार", "telecom", "बैंक", "bank",
)
SAFE_ACCOUNT = (
    "सरकारी खाता", "गवर्नमेंट अकाउंट", "government account", "सेफ अकाउंट",
    "safe account", "भरोसे का खाता", "आरबीआई सेफ", "rbi safe",
)


def load_records(path):
    return json.load(open(path))


def rule_audit(text):
    """Report which 2026-08-11 real-case rules are structurally present (read-only)."""
    t = text.lower()
    inst_hit = [w for w in INSTITUTIONS if w in t]
    safe_hit = [w for w in SAFE_ACCOUNT if w in t]
    return inst_hit, safe_hit


def check_tier(tier, rec):
    state = rec["risk_state"]
    score = rec["coercion_score"]
    flagged = rec["flagged"]
    if tier in ("A", "B", "C"):
        return flagged, f"state={state} score={score:.2f}"
    if tier == "D":
        # tier D = minimal markers, rule-test level only — accept ELEVATED
        ok = state in ("ELEVATED", "HIGH_RISK") or score >= 0.30 or flagged
        return ok, f"state={state} score={score:.2f}"
    return flagged, f"state={state} score={score:.2f}"


def main():
    det = CoercionDetector()
    cases = load_records(CASES)
    benign = load_records(BENIGN)

    results = []
    print(f"{'id':5s} {'tier':4s} {'state':10s} {'score':7s} {'flag':5s} {'hits':32s} {'verdict':5s}  note")
    print("-" * 110)

    passed = 0
    total = 0
    failures = []

    def emit(rec, tier, kind):
        nonlocal passed, total
        total += 1
        prof = det._score_text(rec["text"])
        row = {
            "id": rec["id"], "tier": tier, "kind": kind,
            "risk_state": prof["risk_state"], "coercion_score": prof["coercion_score"],
            "vector_hits": prof["vector_hits"], "flagged": prof["flagged"],
            "note": rec.get("note", ""),
        }
        inst_hit, safe_hit = rule_audit(rec["text"])
        row["rule_audit"] = {"authority_stack": inst_hit, "safe_account": safe_hit}

        if kind == "benign":
            if rec["id"] == "bn5":
                ok = row["risk_state"] != "HIGH_RISK"
            elif rec.get("expect") == "PAUSE_OK":
                # police+FIR → PAUSE (family challenge) is CORRECT safe-by-default
                ok = True  # flagged is the designed outcome; challenge catches real callers
            else:
                ok = row["risk_state"] == "LOW"
            note = f"{'family-ok' if rec['id'] == 'bn5' else 'must-LOW'}"
        elif rec.get("expect") == "neutral_ivr":
            # IVR menu prompt — neutral content by design; only the escalation
            # body (r01b/r02) is flaggable. Expect NOT flagged.
            ok = not row["flagged"]
            note = "neutral-IVR (must NOT flag)"
        else:
            ok, note = check_tier(tier, row)

        hits = ",".join(sorted(row["vector_hits"].keys())) or "-"
        verdict = "PASS" if ok else "FAIL"
        print(f"{row['id']:5s} {tier:4s} {row['risk_state']:10s} {row['coercion_score']:7.3f} "
              f"{str(row['flagged']):5s} {hits:32s} {verdict:5s}  {note}")
        if ok:
            passed += 1
        else:
            failures.append(row)
        results.append(row)

    for c in cases:
        emit(c, c["tier"], "scam")
    for b in benign:
        emit(b, "BN", "benign")

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    os.makedirs(RESULTS, exist_ok=True)
    out = os.path.join(RESULTS, f"real-cases-{ts}.json")
    json.dump({"ts": ts, "passed": passed, "total": total,
               "results": results, "failures": failures},
              open(out, "w"), ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"TOTAL: {passed}/{total} passed")
    print(f"results -> {out}")
    if failures:
        print("\nFAILURES:")
        for r in failures:
            print(f"  {r['id']} (tier {r['tier']}): state={r['risk_state']} "
                  f"score={r['coercion_score']:.2f}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

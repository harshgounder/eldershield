#!/usr/bin/env python3
"""run_curated.py — execute the curated suites against the REAL code, score vs IDEAL-STANDARD.

Pipeline: pool/candidates.jsonl → per-dimension curated selection (all cases, they're all
hand-crafted) → execute → score with severity rules from IDEAL-STANDARD.md:
  CRITICAL fail → dimension score 0
  MAJOR fail   → −0.5
  MINOR fail   → −0.1
Output: benchmarks/results/curated-<ts>.json + console table.

Executes:
  D2/D3/D4 → coercion._match / _normalize (text-level, fast)
  D5       → fusion.fuse (pure function)
  D8       → robustness (no-crash via _normalize+_match)
  D1/D6/D7/D9 → marked SKIPPED (audio-level / interactive / mutation / timing — separate suites)
"""
import json, os, sys, time, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "src"))

from coercion import CoercionDetector
from fusion import fuse

POOL = os.path.join(HERE, "pool", "candidates.jsonl")
RESULTS = os.path.join(HERE, "results")
os.makedirs(RESULTS, exist_ok=True)

SEV_WEIGHT = {"CRITICAL": 1.0, "MAJOR": 0.5, "MINOR": 0.1}

def load_pool():
    return [json.loads(l) for l in open(POOL) if l.strip()]

def score_dim(cases, results):
    """Severity-weighted: score = 1 − weighted_fail/total_weight."""
    total_w = sum(SEV_WEIGHT[c["severity"]] for c in cases)
    fail_w = sum(SEV_WEIGHT[c["severity"]] for c, r in zip(cases, results) if not r["pass"])
    if any(c["severity"] == "CRITICAL" and not r["pass"] for c, r in zip(cases, results)):
        return 0.0  # any critical fail = dimension 0
    return round(max(0.0, 1.0 - fail_w / total_w), 3) if total_w else 1.0

def check_coercion(det, case):
    """UNUSED — kept for reference. The real path is det._score_text (single source of truth)."""
    return det._score_text(case["text"])["risk_state"], 0.0, {}

def expected_ok(actual, expected):
    """expected may be a single value or an OR-set ('LOW_OR_ELEVATED')."""
    if "_OR_" in expected:
        # normalize: "HIGH" in an OR-set means the actual state "HIGH_RISK"
        parts = [("HIGH_RISK" if e == "HIGH" else e) for e in expected.split("_OR_")]
        return any(actual == e for e in parts)
    return actual == expected

def main():
    det = CoercionDetector()
    cases = load_pool()
    print(f"{'dim':5s} {'sub':20s} {'sev':9s} {'expected':18s} {'actual':12s} result")
    print("-" * 90)
    per_dim = {}
    failures = []
    for c in cases:
        dim = c["dim"]
        if dim in ("D1", "D6", "D7", "D9"):
            per_dim.setdefault(dim, []).append(
                {"case": c, "pass": None, "note": "SKIPPED — separate suite"})
            continue
        try:
            if dim == "D5":
                d = json.loads(c["text"])
                r = fuse(spoof_score=d["spoof_score"], spoof_verdict=d["spoof_verdict"],
                         coercion_score=d["co_score"], coercion_state=d["co_state"],
                         payment_context=d["pay"], threat_signals=d["threat"],
                         factcheck_claims=d["claims"])
                actual = r.verdict
                ok = expected_ok(actual, c["expected"])
                note = ""
            elif dim == "D8":
                t = json.loads(c["text"])
                det._normalize(t)
                det._match(t)
                actual = "NO_CRASH"
                ok = True
                note = ""
            else:  # D2, D3, D4
                prof = det._score_text(c["text"])
                actual = prof["risk_state"]
                ok = expected_ok(actual, c["expected"])
                note = f"score={prof['coercion_score']:.2f} hits={sorted(prof['vector_hits'].keys())[:4]}"
        except Exception as e:
            actual = f"CRASH: {e}"
            ok = False
            note = ""
        print(f"{dim:5s} {c['sub']:20s} {c['severity']:9s} {c['expected']:18s} {actual:12s} "
              f"{'PASS' if ok else 'FAIL'} {note}")
        if not ok:
            failures.append((dim, c["sub"], c["expected"], actual, c["severity"]))
        per_dim.setdefault(dim, []).append({"case": c, "pass": ok, "note": note})

    # dimension scores
    print("\n" + "=" * 50)
    print("DIMENSION SCORES vs IDEAL-STANDARD")
    print("=" * 50)
    dim_scores = {}
    for dim, items in sorted(per_dim.items()):
        run = [i for i in items if i["pass"] is not None]
        if not run:
            dim_scores[dim] = None
            print(f"{dim}: SKIPPED")
            continue
        s = score_dim([i["case"] for i in run], run)
        dim_scores[dim] = s
        print(f"{dim}: {s:.2f} ({sum(1 for i in run if i['pass'])}/{len(run)} passed)")

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = os.path.join(RESULTS, f"curated-{ts}.json")
    json.dump({"ts": ts, "dim_scores": dim_scores, "failures": failures,
               "results": [{**i["case"], "pass": i["pass"], "note": i["note"]} for i in per_dim.values() for i in i]},
              open(out, "w"), ensure_ascii=False, indent=2)
    print(f"\nresults -> {out}")
    if failures:
        print(f"\nFAILURES ({len(failures)}):")
        for dim, sub, exp, act, sev in failures:
            print(f"  [{sev}] {dim}/{sub}: expected {exp}, got {act}")
    return 1 if failures else 0

if __name__ == "__main__":
    sys.exit(main())

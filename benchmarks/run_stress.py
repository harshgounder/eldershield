#!/usr/bin/env python3
"""run_stress.py — execute the stress suites against the REAL code.

Invariant (IDEAL-STANDARD D4):
  scam  bases: transformed state must be ≥ expected_min (ELEVATED for scams) — never
               falls below the floor, never crashes
  benign bases: transformed state must be EXACTLY LOW — a transform must never create
               a false positive

Severity: any benign→non-LOW = CRITICAL (false positive = worst failure).
          any scam→LOW = CRITICAL (missed scam). scam→ELEVATED when HIGH expected = MAJOR.
Output: benchmarks/results/stress-<ts>.json
"""
import json, os, sys, time, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "src"))
from coercion import CoercionDetector

POOL = os.path.join(HERE, "pool", "stress.jsonl")
RESULTS = os.path.join(HERE, "results")
os.makedirs(RESULTS, exist_ok=True)

SEV = {"LOW": 0, "ELEVATED": 1, "HIGH_RISK": 2}

def main():
    det = CoercionDetector()
    cases = [json.loads(l) for l in open(POOL) if l.strip()]
    t0 = time.time()
    results, failures = [], []
    for c in cases:
        try:
            prof = det._score_text(c["text"])
            actual = prof["risk_state"]
        except Exception as e:
            actual = f"CRASH: {e}"
        # verdict
        sev = None
        if actual.startswith("CRASH"):
            ok, sev = False, "CRITICAL"
        elif c["is_scam"]:
            if SEV[actual] < SEV[c["expected_min"]]:
                ok, sev = False, "CRITICAL" if actual == "LOW" else "MAJOR"
            else:
                ok = True
        else:  # benign
            ok = actual == "LOW"
            if not ok:
                sev = "CRITICAL"
        results.append({**c, "actual": actual, "pass": ok, "severity": sev})
        if not ok:
            failures.append((c["series"], c["base_idx"], c["is_scam"],
                             c["expected_min"], actual, sev, c["text"][:70]))

    dt = time.time() - t0
    npass = sum(1 for r in results if r["pass"])
    by_series = {}
    for r in results:
        by_series.setdefault(r["series"], {"pass": 0, "total": 0, "fails": 0})
        by_series[r["series"]]["total"] += 1
        if r["pass"]:
            by_series[r["series"]]["pass"] += 1
        else:
            by_series[r["series"]]["fails"] += 1

    print(f"STRESS: {npass}/{len(results)} passed in {dt:.1f}s")
    for s, v in sorted(by_series.items()):
        print(f"  {s}: {v['pass']}/{v['total']} ({v['fails']} fails)")

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = os.path.join(RESULTS, f"stress-{ts}.json")
    json.dump({"ts": ts, "n": len(results), "npass": npass, "by_series": by_series,
               "failures": failures, "results": results},
              open(out, "w"), ensure_ascii=False, indent=2)
    print(f"results -> {out}")

    if failures:
        print(f"\nFAILURES ({len(failures)}):")
        for ser, bidx, scam, exp_min, act, sev, txt in failures[:30]:
            kind = "SCAM" if scam else "BENIGN"
            print(f"  [{sev}] {ser}/base{bidx} {kind}: floor={exp_min} got={act} :: {txt}")
        if len(failures) > 30:
            print(f"  ... and {len(failures) - 30} more")
    return 1 if failures else 0

if __name__ == "__main__":
    sys.exit(main())

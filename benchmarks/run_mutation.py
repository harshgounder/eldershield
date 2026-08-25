#!/usr/bin/env python3
"""run_mutation.py - execute the D7 mutation suite against verify_packet.

THE INVARIANT (IDEAL-STANDARD D7, 100%): any mutation MUST make
verify_packet FAIL (return False or raise). Plus the baseline control:
an UNMUTATED packet MUST pass. If a mutation is not caught it's a
MISSED_TAMPER; if the baseline fails the whole suite is invalid.

Score = fraction of mutation cases caught.
Output: benchmarks/results/mutation-<ts>.json
"""
import json, os, sys, time, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "src"))
import evidence

POOL = os.path.join(HERE, "pool", "mutation.jsonl")
EVIDENCE_DIR = os.path.join(REPO, "demo", "evidence")
RESULTS = os.path.join(HERE, "results")
os.makedirs(RESULTS, exist_ok=True)

SEV = {"PASS": 0, "MISSED_TAMPER": 1, "BASELINE_BROKEN": 2}


# ---------------------------------------------------------------- corruption
def corrupt(case):
    """Apply the case's mutation to a fresh copy of its packet.

    M10 is applied at the raw-JSON text level (a Python dict cannot hold
    duplicate keys), the rest on the parsed object. Returns (packet, is_raw).
    """
    path = os.path.join(EVIDENCE_DIR, case["file"])
    if case["mutation"] == "M10_duplicate":
        return _dup_key_raw(path), True

    with open(path, encoding="utf-8") as f:
        pkt = json.load(f)
    m = case["mutation"]
    if m == "M1_transcript":
        pkt["chain"][2]["data"]["transcript"] += " [tampered]"
    elif m == "M2_spoof_score":
        pkt["chain"][1]["data"]["spoof_score"] = 0.5
    elif m == "M3_coercion":
        cur = pkt["chain"][2]["data"].get("risk_state")
        pkt["chain"][2]["data"]["risk_state"] = "LOW" if cur == "HIGH_RISK" else "HIGH_RISK"
    elif m == "M4_chain":
        pkt["root_hash"] = "0" * 64
    elif m == "M5_model_meta":
        pkt["model_meta"]["version"] = "9.9"
    elif m == "M6_timestamp":
        pkt["generated_at"] = "2099-01-01T00:00:00+00:00"
    elif m == "M7_junk_key":
        pkt["_mutation_junk"] = "tampered"
    elif m == "M8_truncate":
        del pkt["chain"][-1]
    elif m == "M9_reorder":
        link = pkt["chain"][2]["data"]
        pkt["chain"][2]["data"] = dict(reversed(list(link.items())))
    return pkt, False


def _dup_key_raw(path):
    """Duplicate the 'spoof' key in chain[1].data at the raw-JSON level.

    Injects a literal duplicate key whose value is FLIPPED. Raw JSON now
    carries two 'spoof' keys (the duplicate-key corruption); Python's
    json.loads keeps the LAST, so the parsed spoof is tampered and the
    re-computed chain hash no longer matches -> verify_packet must reject.
    """
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    marker = '"name": "spoof_verdict"'
    start = raw.find(marker)
    if start == -1:
        return raw
    key = '"spoof":'
    ki = raw.find(key, start)
    if ki == -1:
        return raw
    end = raw.find(",", ki)
    if end == -1:
        return raw
    original = raw[ki:end]                      # e.g. "spoof": false
    val = original.split(":", 1)[1].strip()
    flipped = "true" if val != "true" else "false"
    # literal duplicate key, injected AFTER the original; json.loads keeps the
    # LAST occurrence, so the flipped value wins -> parsed spoof is tampered.
    dup = f', {key} {flipped}'
    return raw[:ki] + original + dup + raw[end:]


def main():
    cases = [json.loads(l) for l in open(POOL) if l.strip()]
    t0 = time.time()
    results, failures = [], []

    # baseline control first: every unmutated packet must pass
    baselines = {}
    for c in cases:
        if c["file"] not in baselines:
            with open(os.path.join(EVIDENCE_DIR, c["file"]), encoding="utf-8") as f:
                pkt = json.load(f)
            try:
                ok, _ = evidence.verify_packet(pkt)
            except Exception as e:
                ok = f"CRASH: {e}"
            baselines[c["file"]] = ok

    for c in cases:
        if baselines.get(c["file"]) is not True:
            # baseline broken - suite invalid for this packet, can't trust verdicts
            pass_ = False
            verdict, sev = "BASELINE_BROKEN", "CRITICAL"
        else:
            try:
                pkt, is_raw = corrupt(c)
                if is_raw:
                    ok = False
                    try:
                        pkt2 = json.loads(pkt)
                        ok, _ = evidence.verify_packet(pkt2)
                    except Exception:
                        ok = False  # unparseable raw JSON => caught
                    verdict, sev = ("FAIL", "PASS") if not ok else ("PASSED", "MISSED_TAMPER")
                    pass_ = not ok
                else:
                    try:
                        ok, _ = evidence.verify_packet(pkt)
                        verdict = "FAIL" if not ok else "PASSED"
                        sev = "PASS" if not ok else "MISSED_TAMPER"
                    except Exception as e:
                        ok, verdict, sev = False, f"CRASH: {e}", "PASS"  # raised = caught
                    pass_ = not ok
            except Exception as e:
                ok, verdict, sev, pass_ = False, f"CRASH: {e}", "PASS", True

        results.append({**c, "baseline_ok": baselines.get(c["file"]),
                        "verdict": verdict, "pass": pass_, "severity": sev})
        if not pass_:
            failures.append((c["mutation"], c["file"], verdict, sev))

    dt = time.time() - t0
    npass = sum(1 for r in results if r["pass"])
    by_mut = {}
    for r in results:
        by_mut.setdefault(r["mutation"], {"pass": 0, "total": 0, "missed": 0, "baseline_broken": 0})
        by_mut[r["mutation"]]["total"] += 1
        if r["pass"]:
            by_mut[r["mutation"]]["pass"] += 1
        elif r["severity"] == "BASELINE_BROKEN":
            by_mut[r["mutation"]]["baseline_broken"] += 1
        else:
            by_mut[r["mutation"]]["missed"] += 1

    score = npass / len(results) if results else 0.0
    print(f"MUTATION (D7): {npass}/{len(results)} caught ({score:.1%}) in {dt:.1f}s")
    for m, v in sorted(by_mut.items()):
        flag = "  <-- MISSED" if v["missed"] else ("  <-- BASELINE" if v["baseline_broken"] else "")
        print(f"  {m}: {v['pass']}/{v['total']} caught{flag}")

    bad_baseline = {f: v for f, v in baselines.items() if v is not True}
    print(f"  baselines OK: {sum(1 for v in baselines.values() if v is True)}/{len(baselines)} packets")

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = os.path.join(RESULTS, f"mutation-{ts}.json")
    json.dump({"ts": ts, "n": len(results), "npass": npass, "score": score,
               "by_mutation": by_mut, "baselines": {k: (v if isinstance(v, bool) else str(v))
                                                     for k, v in baselines.items()},
               "failures": failures, "results": results},
              open(out, "w"), ensure_ascii=False, indent=2)
    print(f"results -> {out}")

    if failures:
        print(f"\nMISSED/BROKEN ({len(failures)}):")
        for mut, file, verdict, sev in failures[:30]:
            print(f"  [{sev}] {mut} :: {file} :: {verdict}")
        if len(failures) > 30:
            print(f"  ... and {len(failures) - 30} more")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

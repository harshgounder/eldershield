#!/usr/bin/env python3
"""Ensure all demo evidence packets (KV-*) are meta_hash-consistent + verified.

The meta_hash layer (D7 hardening, 2026-08-11) is recomputed for any packet
missing it or out of sync - e.g. packets written before the schema change or
hand-edited. The sha256 CHAIN (audio/spoof/coercion links) is never touched:
if the chain is broken the packet is reported as tampered, not "repaired".

Idempotent: a fully consistent set is a no-op ("0 packets").
"""
import glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
EVID = os.path.join(REPO, "demo", "evidence")
sys.path.insert(0, os.path.join(REPO, "src"))
from evidence import sha256_str, verify_packet  # noqa: E402

n = 0
for f in sorted(glob.glob(os.path.join(EVID, "KV-*.json"))):
    p = json.load(open(f))
    ok, why = verify_packet(p)
    if not ok:
        print(f"TAMPERED (chain broken, NOT repaired): {os.path.basename(f)} :: {why}")
        continue
    _meta_src = {k: v for k, v in p.items() if k not in ("chain", "meta_hash")}
    want = sha256_str(p["root_hash"] + json.dumps(_meta_src, ensure_ascii=False, sort_keys=True))
    if p.get("meta_hash") == want:
        continue
    p["meta_hash"] = want
    json.dump(p, open(f, "w"), ensure_ascii=False, indent=2)
    n += 1
print(f"repaired meta_hash on {n} packets")

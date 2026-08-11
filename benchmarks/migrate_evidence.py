#!/usr/bin/env python3
"""Migrate legacy evidence packets to the meta_hash schema (2026-08-11).

The chain itself is untouched (still verifies); meta_hash is ADDED, covering
packet_id / generated_at / model_meta / junk keys. Run once.
"""
import json, glob, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from evidence import sha256_str  # noqa: E402

files = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "demo", "evidence", "ES-*.json")))
n = 0
for f in files:
    p = json.load(open(f))
    if "meta_hash" in p:
        continue
    _meta_src = {k: v for k, v in p.items() if k not in ("chain", "meta_hash")}
    p["meta_hash"] = sha256_str(
        p["root_hash"] + json.dumps(_meta_src, ensure_ascii=False, sort_keys=True)
    )
    json.dump(p, open(f, "w"), ensure_ascii=False, indent=2)
    n += 1
print(f"migrated {n} packets (+meta_hash)")

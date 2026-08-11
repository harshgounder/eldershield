#!/usr/bin/env python3
"""gen_mutation.py — D7 evidence-packet mutation generator (tamper-evidence suite).

THE INVARIANT (IDEAL-STANDARD D7, 100%):
  ANY byte/field corruption in a packet must make verify_packet FAIL
  (return False or raise). The sha256 chain is the tamper-evident core:
  a single edit — transcript, spoof_score, coercion fields, chain ids,
  model_meta, timestamps, a junk key, truncation, key-reorder, duplicate
  key — MUST break verification.

  Baseline control: an UNMUTATED packet MUST verify TRUE. If the baseline
  fails, the suite is invalid (we were given a broken packet), not a pass.

Mutations (10 categories), one case each applied to every curated packet:
  M1 transcript   — tamper chain[2].data.transcript
  M2 spoof_score  — tamper chain[1].data.spoof_score
  M3 coercion     — tamper coercion_score / risk_state / vector_hits
  M4 chain        — tamper packet_id / audio_sha256 / a link hash / root_hash
  M5 model_meta   — tamper top-level model_meta.version
  M6 timestamp    — tamper generated_at / chain[1].data.timestamp
  M7 junk key     — inject a stray key at packet root
  M8 truncate     — drop a chain link (JSON truncation of the chain)
  M9 reorder      — reorder chain link data keys (canonical order must hold)
  M10 duplicate   — duplicate a key inside a link's data (raw-JSON level)

Output: benchmarks/pool/mutation.jsonl — each case:
  {id, mutation, file, operation} describing how to corrupt.
Deterministic (seeded). Uses only stdlib (json/os/random).
The corruption logic lives in run_mutation.py (this emits the spec).
"""
import json, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
EVIDENCE_DIR = os.path.join(REPO, "demo", "evidence")
OUT = os.path.join(HERE, "pool")
os.makedirs(OUT, exist_ok=True)

rng = random.Random(20260811)

# (mutation_id, human operation string)
MUTATIONS = [
    ("M1_transcript", "append '[tampered]' to chain[2].data.transcript"),
    ("M2_spoof_score", "set chain[1].data.spoof_score = 0.5"),
    ("M3_coercion", "flip chain[2].data.risk_state to the opposite of current"),
    ("M4_chain", "overwrite root_hash with 64 zeros"),
    ("M5_model_meta", "set model_meta.version = '9.9'"),
    ("M6_timestamp", "set generated_at = '2099-01-01T00:00:00+00:00'"),
    ("M7_junk_key", "inject top-level junk key '_mutation_junk'"),
    ("M8_truncate", "drop last chain link (JSON truncation of the chain)"),
    ("M9_reorder", "reverse key order of chain[2].data (canonical order broken)"),
    ("M10_duplicate", "duplicate 'spoof' key in chain[1].data with a tampered value (raw JSON)"),
]

def curated_packets():
    """All valid, self-consistent KV-*.json demo packets (baseline must verify)."""
    return sorted(p for p in os.listdir(EVIDENCE_DIR)
                  if p.startswith("KV-") and p.endswith(".json"))

cases = []
packets = curated_packets()
for file in packets:
    for mid, op in MUTATIONS:
        cases.append({
            "id": f"{file.split('.')[0]}.{mid}",
            "mutation": mid,
            "file": file,
            "operation": op,
        })

rng.shuffle(cases)
with open(os.path.join(OUT, "mutation.jsonl"), "w") as f:
    for c in cases:
        f.write(json.dumps(c, ensure_ascii=False) + "\n")

by_mut = {}
for c in cases:
    by_mut[c["mutation"]] = by_mut.get(c["mutation"], 0) + 1
print(f"generated {len(cases)} mutation cases across {len(packets)} packets")
for m in sorted(by_mut):
    print(f"  {m}: {by_mut[m]}")
print("written:", os.path.join(OUT, "mutation.jsonl"))

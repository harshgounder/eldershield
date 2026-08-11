#!/usr/bin/env python3
"""Rename demo evidence packets ES-* → KV-* (Kavach rebrand, 2026-08-11).

The packet_id participates in meta_hash (D7 hardening), so renaming must
recompute meta_hash; the sha256 CHAIN (audio/spoof/coercion links) is untouched
and stays valid. PDFs are regenerated from the updated JSON.
"""
import glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
EVID = os.path.join(REPO, "demo", "evidence")
sys.path.insert(0, os.path.join(REPO, "src"))
from evidence import sha256_str, verify_packet, export_pdf  # noqa: E402

n = 0
for f in sorted(glob.glob(os.path.join(EVID, "ES-*.json"))):
    p = json.load(open(f))
    assert p["packet_id"].startswith("ES-")
    p["packet_id"] = "KV-" + p["packet_id"][3:]
    # chain links keep their original data (audio/spoof/coercion) — untouched.
    # meta_hash must be recomputed over the new packet_id.
    _meta_src = {k: v for k, v in p.items() if k not in ("chain", "meta_hash")}
    p["meta_hash"] = sha256_str(
        p["root_hash"] + json.dumps(_meta_src, ensure_ascii=False, sort_keys=True)
    )
    ok, why = verify_packet(p)
    assert ok, f"re-hash failed for {f}: {why}"
    newf = os.path.join(EVID, os.path.basename(f).replace("ES-", "KV-"))
    json.dump(p, open(newf, "w"), ensure_ascii=False, indent=2)
    # regenerate PDF from the renamed JSON
    pdff = newf.replace(".json", ".pdf")
    try:
        export_pdf(p, pdff)
    except Exception as e:
        print(f"PDF skip {pdff}: {e}")
    os.remove(f)
    oldpdf = f.replace(".json", ".pdf")
    if os.path.exists(oldpdf):
        os.remove(oldpdf)
    n += 1
print(f"renamed+rehashed {n} packets to KV-")

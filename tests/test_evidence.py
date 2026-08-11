#!/usr/bin/env python3
"""Evidence-packet integrity tests — the D7 class (found by the mutation suite).

Covers: tamper-evidence on every packet field, backward compatibility with
pre-meta_hash packets, and the hash-chain semantics.
"""
import json, os, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from evidence import build_packet, verify_packet, sha256_str  # noqa: E402


def _make_packet():
    tmp = tempfile.mktemp(suffix=".wav")
    with open(tmp, "wb") as f:
        f.write(b"\x00" * 1024)
    eng = {"spoof": True, "score": 0.99, "crop_scores": [0.99, 0.98, 1.0],
           "latency_ms": 12.3}
    coer = {"transcript": "main CBI se bol raha hoon, paise bhejo",
            "language": "hi", "coercion_score": 0.7, "risk_state": "HIGH_RISK",
            "vector_hits": {"authority": ["cbi"]}, "asr_latency_ms": 800.0}
    return build_packet(tmp, eng, coer), tmp


class TestEvidenceIntegrity(unittest.TestCase):
    def setUp(self):
        self.packet, self.audio = _make_packet()

    def tearDown(self):
        if os.path.exists(self.audio):
            os.remove(self.audio)

    def test_fresh_packet_verifies(self):
        ok, link = verify_packet(self.packet)
        self.assertTrue(ok, f"fresh packet failed at {link}")

    def test_has_meta_hash(self):
        self.assertIn("meta_hash", self.packet)

    def test_chain_tamper_detected(self):
        for link in self.packet["chain"]:
            p2 = json.loads(json.dumps(self.packet))
            p2["chain"][link["link"] - 1]["data"]["transcript"] = "tampered"
            ok, _ = verify_packet(p2)
            self.assertFalse(ok, f"chain link {link['link']} tamper undetected")

    def test_packet_id_tamper_detected(self):
        p2 = json.loads(json.dumps(self.packet))
        p2["packet_id"] = "ES-XXXXXXXXXXXX"
        self.assertFalse(verify_packet(p2)[0])

    def test_generated_at_tamper_detected(self):
        p2 = json.loads(json.dumps(self.packet))
        p2["generated_at"] = "2026-01-01T00:00:00+00:00"
        self.assertFalse(verify_packet(p2)[0])

    def test_model_meta_tamper_detected(self):
        p2 = json.loads(json.dumps(self.packet))
        p2["model_meta"]["model"] = "fake-model"
        self.assertFalse(verify_packet(p2)[0])

    def test_junk_key_detected(self):
        p2 = json.loads(json.dumps(self.packet))
        p2["evil_key"] = "injected"
        self.assertFalse(verify_packet(p2)[0])

    def test_key_reorder_still_valid(self):
        # sort_keys canonicalization → reordering is NOT tampering by design
        p2 = json.loads(json.dumps(self.packet))
        chain = p2.pop("chain")
        p2["chain"] = chain  # same dict, rebuilt to prove order-independence
        # rebuild with reversed top-level key insertion order
        ordered = {}
        for k in reversed(list(p2.keys())):
            ordered[k] = p2[k]
        self.assertTrue(verify_packet(ordered)[0])

    def test_old_schema_packet_backward_compatible(self):
        # simulate a pre-meta_hash packet (chain intact, no meta_hash)
        p2 = json.loads(json.dumps(self.packet))
        del p2["meta_hash"]
        ok, _ = verify_packet(p2)
        self.assertTrue(ok, "old-schema packet must still verify")


if __name__ == "__main__":
    unittest.main()

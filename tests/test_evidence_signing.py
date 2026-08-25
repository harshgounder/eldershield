#!/usr/bin/env python3
"""test_evidence_signing.py - R2 ed25519 signing (2026-08-25 red-team closure):
sign_packet + verify_packet_signed round trip, tamper rejection, unsigned
rejection, and backward compat with unsigned packets."""

import base64, json, os, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from evidence import (build_packet, sign_packet, verify_packet,
                      verify_packet_signed, sha256_str)  # noqa: E402

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    HAVE_CRYPTO = True
except ImportError:
    HAVE_CRYPTO = False


def make_packet():
    import tempfile, wave
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(b"\x00\x00" * 16000)
    eng = {"spoof": True, "score": 0.99, "crop_scores": [0.99, 0.99, 0.99],
           "latency_ms": 71.0, "max_crop_score": 0.99, "signal_quality": "ok"}
    coer = {"transcript": "सीबीआई से बोल रहा हूँ, पैसे भेजो", "language": "hi",
            "coercion_score": 0.9, "risk_state": "HIGH_RISK",
            "vector_hits": {"authority": ["CBI"]}, "asr_latency_ms": 1200}
    return build_packet(path, eng, coer, model_meta={"test": "signing"})


@unittest.skipUnless(HAVE_CRYPTO, "cryptography package not installed")
class TestSigning(unittest.TestCase):
    def setUp(self):
        self.key = Ed25519PrivateKey.generate()

    def test_roundtrip(self):
        p = make_packet()
        sign_packet(p, self.key)
        ok, bad = verify_packet_signed(p, self.key.public_key())
        self.assertTrue(ok, bad)
        # plain chain verify still passes with signature present
        ok2, bad2 = verify_packet(p)
        self.assertTrue(ok2, bad2)

    def test_tamper_rejected(self):
        p = make_packet()
        sign_packet(p, self.key)
        p["chain"][1]["data"]["spoof_score"] = 0.0  # flip the verdict score
        ok, bad = verify_packet_signed(p, self.key.public_key())
        self.assertFalse(ok)

    def test_signature_swapped_rejected(self):
        p = make_packet()
        sign_packet(p, self.key)
        other = Ed25519PrivateKey.generate()
        ok, bad = verify_packet_signed(p, other.public_key())
        self.assertFalse(ok, bad)

    def test_unsigned_rejected(self):
        p = make_packet()
        ok, bad = verify_packet_signed(p, self.key.public_key())
        self.assertFalse(ok)
        self.assertEqual(bad, "unsigned")

    def test_signature_excluded_from_meta_hash(self):
        p = make_packet()
        mh_before = p["meta_hash"]
        sign_packet(p, self.key)
        # adding the signature must NOT invalidate meta_hash
        ok, bad = verify_packet(p)
        self.assertTrue(ok, bad)
        self.assertEqual(p["meta_hash"], mh_before)

    def test_signature_b64_fresh(self):
        p = make_packet()
        sign_packet(p, self.key)
        raw = base64.b64decode(p["signature"])
        self.assertEqual(len(raw), 64)  # ed25519 signatures are 64 bytes


if __name__ == "__main__":
    unittest.main()
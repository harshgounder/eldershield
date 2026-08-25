#!/usr/bin/env python3
"""test_fusion_core.py - unit tests for the FUSION verdict ladder (src/fusion.py).

Covers the 4 verdicts + the boundary cases a judge would probe:
  PASS     - clean call, no signals
  CAUTION  - single elevated coercion, no spoof
  PAUSE    - spoof alone / HIGH coercion alone
  KILL     - spoof AND HIGH coercion
  payment tripwire alone triggers CAUTION; tripwire + spoof → PAUSE
"""
import os, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from fusion import fuse, VERDICTS


class TestFusion(unittest.TestCase):

    def test_pass_clean_call(self):
        r = fuse(spoof_score=0.02, spoof_verdict=False,
                 coercion_score=0.05, coercion_state="LOW")
        self.assertEqual(r.verdict, "PASS")
        self.assertEqual(r.action, "✅ PASS - no intervention")

    def test_caution_single_elevated(self):
        r = fuse(spoof_score=0.10, spoof_verdict=False,
                 coercion_score=0.55, coercion_state="ELEVATED")
        self.assertEqual(r.verdict, "CAUTION")

    def test_pause_spoof_alone(self):
        r = fuse(spoof_score=0.98, spoof_verdict=True,
                 coercion_score=0.10, coercion_state="LOW")
        self.assertEqual(r.verdict, "PAUSE")

    def test_pause_high_coercion_alone(self):
        r = fuse(spoof_score=0.05, spoof_verdict=False,
                 coercion_score=0.95, coercion_state="HIGH_RISK")
        self.assertEqual(r.verdict, "PAUSE")

    def test_kill_spoof_plus_high(self):
        r = fuse(spoof_score=0.99, spoof_verdict=True,
                 coercion_score=0.95, coercion_state="HIGH_RISK")
        self.assertEqual(r.verdict, "KILL")

    def test_tripwire_alone_caution(self):
        r = fuse(spoof_score=0.02, spoof_verdict=False,
                 coercion_score=0.05, coercion_state="LOW",
                 payment_context={"payee_new": True, "amount_inr": 150000, "collect": False})
        self.assertEqual(r.verdict, "CAUTION")

    def test_tripwire_plus_spoof_pause(self):
        r = fuse(spoof_score=0.98, spoof_verdict=True,
                 coercion_score=0.05, coercion_state="LOW",
                 payment_context={"payee_new": True, "amount_inr": 150000, "collect": False})
        self.assertEqual(r.verdict, "PAUSE")

    def test_threat_signals_alone_caution(self):
        r = fuse(spoof_score=0.02, spoof_verdict=False,
                 coercion_score=0.05, coercion_state="LOW",
                 threat_signals=["isolation", "fake_agency"])
        self.assertEqual(r.verdict, "CAUTION")

    def test_verdicts_exhaustive(self):
        self.assertEqual(VERDICTS, ("PASS", "CAUTION", "PAUSE", "KILL"))

    def test_reasons_include_verdict(self):
        r = fuse(spoof_score=0.99, spoof_verdict=True,
                 coercion_score=0.95, coercion_state="HIGH_RISK")
        self.assertTrue(any("verdict: KILL" in x for x in r.reasons))

    def test_departments_all_present(self):
        r = fuse(spoof_score=0.02, spoof_verdict=False,
                 coercion_score=0.05, coercion_state="LOW")
        for dept in ("spoof", "coercion", "payment", "threat", "factcheck", "evidence"):
            self.assertIn(dept, r.departments)


if __name__ == "__main__":
    unittest.main(verbosity=2)

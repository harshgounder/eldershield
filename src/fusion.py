#!/usr/bin/env python3
"""fusion.py — Kavach FUSION core (B1 spoof + B2 coercion → one verdict → one intervention).

The product claim from the pitch: "six departments, one fusion verdict, one intervention."
This module is that claim made executable. Pure logic — no audio I/O, fully unit-testable.

Verdict ladder (deterministic, documented):
  PASS     — bonafide voice, no coercion            → no action
  CAUTION  — any single risk signal                 → warn, verify before payment
  PAUSE    — spoof OR HIGH coercion                 → full intervention (family challenge)
  KILL     — spoof AND HIGH coercion                → hard block recommendation + 1930

Departments (the six from 01-VISION.md):
  spoof / coercion / threat / factcheck / payment / evidence
  - spoof & coercion: live (engine + detector)
  - threat/factcheck/payment: scored from signals when present (stub-able, honest)
  - evidence: emitted by the loop (B4), referenced here for the chain state
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


# ------------------------------------------------------------------ verdicts
VERDICTS = ("PASS", "CAUTION", "PAUSE", "KILL")


@dataclass
class FusionResult:
    verdict: str
    action: str
    spoof_score: float
    coercion_score: float
    coercion_state: str
    departments: Dict[str, dict] = field(default_factory=dict)
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def fuse(spoof_score: float,
         spoof_verdict: bool,
         coercion_score: float,
         coercion_state: str,
         payment_context: Optional[dict] = None,
         threat_signals: Optional[List[str]] = None,
         factcheck_claims: Optional[List[str]] = None) -> FusionResult:
    """Combine all department signals into ONE verdict + ONE action.

    spoof_score: 0..1 (0=real, 1=clone)
    coercion_state: LOW / ELEVATED / HIGH_RISK (from coercion.py)
    payment_context: {"payee_new": bool, "amount_inr": float, "collect": bool} when the tripwire fires
    threat_signals: e.g. ["isolation", "fake_agency", "safe_account"]
    factcheck_claims: e.g. ["digital_arrest_claim", "parcel_drugs_claim"]
    """
    reasons: List[str] = []
    dept: Dict[str, dict] = {}

    # --- spoof department
    dept["spoof"] = {"score": round(spoof_score, 4), "verdict": spoof_verdict}
    if spoof_verdict:
        reasons.append(f"voice spoof {spoof_score:.3f}")

    # --- coercion department
    dept["coercion"] = {"score": round(coercion_score, 4), "state": coercion_state}
    if coercion_state in ("ELEVATED", "HIGH_RISK"):
        reasons.append(f"coercion {coercion_state} ({coercion_score:.2f})")

    # --- payment tripwire department (armed always, fires when context present)
    pay_risk = False
    if payment_context:
        pay_risk = bool(payment_context.get("payee_new")) or bool(payment_context.get("collect")) \
            or (payment_context.get("amount_inr") or 0) >= 50000
        dept["payment"] = {"armed": True, "fired": pay_risk, **payment_context}
        if pay_risk:
            reasons.append(f"payment tripwire ({payment_context})")
    else:
        dept["payment"] = {"armed": True, "fired": False, "note": "tripwire active, no payment context seen"}

    # --- threat department (armed always, fires when signals present)
    threat = list(threat_signals or [])
    dept["threat"] = {"armed": True, "fired": bool(threat), "signals": threat}
    if threat:
        reasons.append(f"threat signals: {', '.join(threat)}")

    # --- factcheck department (armed always, fires when claims present)
    claims = list(factcheck_claims or [])
    dept["factcheck"] = {"armed": True, "fired": bool(claims), "claims": claims}
    if claims:
        reasons.append(f"unverified claims: {', '.join(claims)}")

    # --- evidence department (chain state, filled by the loop)
    dept["evidence"] = {"armed": True, "chain": "pending"}

    # ---------------------------------------------------------------- verdict ladder
    spoof = spoof_verdict
    high_coercion = coercion_state == "HIGH_RISK"
    any_signal = spoof or coercion_state in ("ELEVATED", "HIGH_RISK") or pay_risk or bool(threat) or bool(claims)

    if spoof and high_coercion:
        verdict = "KILL"
        action = "🛑 HARD BLOCK — end call + one-tap report to 1930 with evidence packet"
    elif spoof or high_coercion:
        verdict = "PAUSE"
        action = "🚨 PAUSE — family challenge before any payment; trusted contact alerted"
    elif any_signal:
        verdict = "CAUTION"
        action = "⚠️ CAUTION — verify identity + payment before proceeding"
    else:
        verdict = "PASS"
        action = "✅ PASS — no intervention"

    reasons.append(f"verdict: {verdict}")
    return FusionResult(verdict=verdict, action=action,
                        spoof_score=round(spoof_score, 4),
                        coercion_score=round(coercion_score, 4),
                        coercion_state=coercion_state,
                        departments=dept, reasons=reasons)

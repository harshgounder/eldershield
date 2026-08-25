#!/usr/bin/env python3
"""evidence.py - B4 layer: tamper-evident evidence packet + 1930-ready PDF export.

Every Kavach detection emits a chain-of-custody packet:
  sha256 hash chain (audio -> transcript -> verdict) + timestamp + model versions
  -> JSON (machine-readable) + PDF (human-readable, 1930/CERT-In-shaped).

The hash chain makes the packet tamper-evident: any edit breaks the chain.
Nothing is uploaded anywhere - the packet is generated locally (sovereignty story).
"""
import hashlib, json, os, time, uuid
from datetime import datetime, timezone


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def sha256_str(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def build_packet(audio_path, engine_result, coercion_result, model_meta=None):
    """Build the full evidence packet with hash chain.

    engine_result: from KavachEngine.analyze() (spoof score, verdict, latency)
    coercion_result: from CoercionDetector.analyze() (transcript, coercion score, state)
    model_meta: dict with model names/versions (defaults provided)
    """
    audio_hash = sha256_file(audio_path)
    ts = datetime.now(timezone.utc).isoformat()
    packet_id = "KV-" + uuid.uuid4().hex[:12].upper()

    meta = {
        "model": "AASIST-hindi (3-crop majority vote)",
        "asr": "faster-whisper small (hi)",
        "version": "1.0",
        "processor": "elder-shield-b2-b4",
    }
    if model_meta:
        meta.update(model_meta)

    # ---- chain link 1: audio ----
    link_audio = {
        "packet_id": packet_id,
        "timestamp": ts,
        "audio_file": os.path.basename(audio_path),
        "audio_sha256": audio_hash,
    }

    # ---- chain link 2: spoof verdict ----
    link_spoof = {
        "spoof": engine_result.get("spoof"),
        "spoof_score": engine_result.get("score"),
        "crop_scores": engine_result.get("crop_scores"),
        "latency_ms": engine_result.get("latency_ms"),
        "model": meta["model"],
    }

    # ---- chain link 3: coercion profile ----
    link_coercion = {
        "transcript": coercion_result.get("transcript"),
        "language": coercion_result.get("language"),
        "coercion_score": coercion_result.get("coercion_score"),
        "risk_state": coercion_result.get("risk_state"),
        "vector_hits": coercion_result.get("vector_hits"),
        "asr_latency_ms": coercion_result.get("asr_latency_ms"),
        "asr_model": meta["asr"],
    }

    # ---- the chain: each link hashes the previous link's hash ----
    h1 = sha256_str(json.dumps(link_audio, ensure_ascii=False, sort_keys=True))
    h2 = sha256_str(h1 + json.dumps(link_spoof, ensure_ascii=False, sort_keys=True))
    h3 = sha256_str(h2 + json.dumps(link_coercion, ensure_ascii=False, sort_keys=True))

    packet = {
        "packet_id": packet_id,
        "generated_at": ts,
        "chain": [
            {"link": 1, "name": "audio", "hash": h1, "data": link_audio},
            {"link": 2, "name": "spoof_verdict", "hash": h2, "data": link_spoof},
            {"link": 3, "name": "coercion_profile", "hash": h3, "data": link_coercion},
        ],
        "root_hash": h3,
        "chain_algorithm": "sha256(hash_prev + canonical_json(link))",
        "model_meta": meta,
    }
    # meta_hash - closes the D7 gaps (found by the mutation suite, 2026-08-11):
    # the chain alone covers the 3 data links; packet_id/generated_at/model_meta
    # and ANY injected top-level junk key were invisible to verify_packet.
    # Hash everything except the chain + this field itself (sort_keys → order-
    # independent, so key reordering stays a non-issue by design).
    _meta_src = {k: v for k, v in packet.items() if k not in ("chain", "meta_hash")}
    packet["meta_hash"] = sha256_str(
        packet["root_hash"] + json.dumps(_meta_src, ensure_ascii=False, sort_keys=True)
    )
    return packet


def verify_packet(packet):
    """Re-compute the chain; return (ok, mismatch_link).

    Backward compatible: packets without meta_hash (pre-2026-08-11 schema)
    verify on the chain alone; packets with meta_hash must also match it
    (covers packet_id, generated_at, model_meta, and any junk-key injection).
    """
    links = packet.get("chain", [])
    prev = ""
    for link in links:
        h = sha256_str(prev + json.dumps(link["data"], ensure_ascii=False, sort_keys=True))
        if h != link["hash"]:
            return False, link["link"]
        prev = h
    if prev != packet.get("root_hash"):
        return False, None
    if "meta_hash" in packet:
        _meta_src = {k: v for k, v in packet.items() if k not in ("chain", "meta_hash")}
        mh = sha256_str(
            packet["root_hash"] + json.dumps(_meta_src, ensure_ascii=False, sort_keys=True)
        )
        if mh != packet["meta_hash"]:
            return False, "meta"
    return True, None


def save_json(packet, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(packet, f, ensure_ascii=False, indent=2)
    return path


def export_pdf(packet, path):
    """1930-ready PDF: human-readable incident summary + chain + transcript."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    doc = SimpleDocTemplate(path, pagesize=A4,
                            rightMargin=15 * mm, leftMargin=15 * mm,
                            topMargin=15 * mm, bottomMargin=15 * mm)
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=16, textColor=colors.HexColor("#1C0731"))
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=12, textColor=colors.HexColor("#1C0731"))
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=9, leading=13)

    story = []
    story.append(Paragraph("Kavach - Voice-Fraud Detection Evidence Packet", h1))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(f"Packet ID: <b>{packet['packet_id']}</b>", body))
    story.append(Paragraph(f"Generated: {packet['generated_at']}", body))
    story.append(Paragraph("This packet is tamper-evident: any edit breaks the sha256 chain. Generated locally - no audio or transcript uploaded.", body))
    story.append(Spacer(1, 4 * mm))

    links = {l["name"]: l["data"] for l in packet["chain"]}
    spoof = links.get("spoof_verdict", {})
    coer = links.get("coercion_profile", {})

    story.append(Paragraph("1. Detection Result", h2))
    verdict = "SPOOF - PAUSE" if spoof.get("spoof") else "BONAFIDE - PASS"
    story.append(Paragraph(f"Verdict: <b>{verdict}</b>", body))
    story.append(Paragraph(f"Spoof score: {spoof.get('spoof_score')} (0=real, 1=clone) · crops: {spoof.get('crop_scores')} · latency: {spoof.get('latency_ms')}ms", body))

    story.append(Paragraph("2. Coercion Profile", h2))
    story.append(Paragraph(f"Risk state: <b>{coer.get('risk_state')}</b> · coercion score: {coer.get('coercion_score')} · language: {coer.get('language')}", body))
    hits = coer.get("vector_hits") or {}
    for vec, phrases in hits.items():
        story.append(Paragraph(f"• {vec}: {', '.join(phrases)}", body))
    if coer.get("transcript"):
        story.append(Paragraph("Transcript:", h2))
        story.append(Paragraph(coer["transcript"], body))

    story.append(Paragraph("3. Chain of Custody", h2))
    rows = [["Link", "Name", "sha256"]]
    for l in packet["chain"]:
        rows.append([str(l["link"]), l["name"], l["hash"][:32] + "…"])
    t = Table(rows, colWidths=[15 * mm, 40 * mm, 110 * mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2EEFA")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(f"Root hash: {packet['root_hash']}", body))
    story.append(Paragraph(f"Chain algorithm: {packet['chain_algorithm']}", body))

    story.append(Paragraph("4. How to act on this", h2))
    story.append(Paragraph("If this packet marks a SPOOF/coercion: do NOT transfer money. Call 1930 (cyber-fraud helpline) or report at cybercrime.gov.in (NCRP). Keep this PDF as evidence. If a family member is involved, verify with the family challenge phrase.", body))

    doc.build(story)
    return path


def build_and_save(audio_path, engine_result, coercion_result, out_dir, model_meta=None):
    """One-call: build packet, save JSON + PDF, verify chain. Returns paths dict."""
    os.makedirs(out_dir, exist_ok=True)
    packet = build_packet(audio_path, engine_result, coercion_result, model_meta)
    ok, bad = verify_packet(packet)
    assert ok, f"chain broken at link {bad}"

    base = packet["packet_id"]
    json_path = save_json(packet, os.path.join(out_dir, base + ".json"))
    pdf_path = export_pdf(packet, os.path.join(out_dir, base + ".pdf"))
    return {"packet": packet, "json": json_path, "pdf": pdf_path, "chain_ok": ok}


if __name__ == "__main__":
    import sys
    # demo: run against an audio file with both engines and emit both artifacts
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from engine import KavachEngine
    from coercion import CoercionDetector

    audio = sys.argv[1] if len(sys.argv) > 1 else "assets/attack_digital_arrest.mp3"
    out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/es-evidence"

    eng = KavachEngine()
    det = CoercionDetector()
    er = eng.analyze(audio)
    cr = det.analyze(audio)
    res = build_and_save(audio, er, cr, out)
    print("packet:", res["packet"]["packet_id"], "| verdict:", er["spoof"], "| coercion:", cr["risk_state"])
    print("json:", res["json"])
    print("pdf:", res["pdf"])
    print("chain_ok:", res["chain_ok"])

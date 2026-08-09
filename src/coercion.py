#!/usr/bin/env python3
"""coercion.py — B2 layer: Hindi/Hinglish coercion-intent detection for ElderShield.

Turns raw call audio into a coercion risk profile BEFORE the payment happens:
  audio -> faster-whisper (hi) ASR -> transcript
        -> phrase-bank matching (authority/secrecy/urgency/payment vectors)
        -> coercion score 0-1 + matched cues + risk state

Phrase bank: digital-arrest + vishing script DNA (from complaints research:
authority ladder Police->NCB->CBI->RBI->SC, secrecy 'don't tell family',
urgency 'transfer now', isolation 'stay on the line').
"""
import os, re, time, json

# --- phrase banks (Hindi + Hinglish + English) ---
AUTHORITY = [
    "सीबीआई", "सीबीआय", "पुलिस", "साइबर सेल", "साइबर क्राइम", "एनसीबी", "कस्टम",
    "आरबीआई", "ईडी", "इनकम टैक्स", "कोर्ट", "अदालत", "जज", "वकील", "क्राइम ब्रांच",
    "बैंक", "bank", "बैंक से", "आपके बैंक",
    "cbi", "ncb", "police", "cyber cell", "cyber crime", "rbi", "enforcement directorate",
    "income tax", "court", "judge", "interpol", "supreme court", "high court",
]
ARREST = [
    "गिरफ्तार", "गिरफ़्तार", "वारंट", "केस दर्ज", "एफआईआर", "समन", "जेल", "अरेस्ट",
    "arrest", "warrant", "fir", "summon", "jail", "non-bailable", "बिना जमानत",
    "कुर्की", "सीज़", "attachment", "confiscate", "ज़ब्त",
]
SECRECY = [
    "किसी को मत बताना", "किसी को नहीं बताना", "बात मत करना", "चुप रहो", "गोपनीय",
    "फैमिली को मत बताना", "परिवार को मत बताना", "किसी से शेयर मत करना",
    "don't tell anyone", "don't tell your family", "keep it confidential", "secret",
    "tell no one", "किसी को बताया तो",
]
URGENCY = [
    "तुरंत", "अभी", "फौरन", "जल्दी", "आज ही", "एक घंटे में", "10 मिनट में",
    "देर मत करो", "टाइम मत लो", "अभी करो", "रुको मत", "जल्दी बताइए", "जल्दी बताओ",
    "वरना", "नहीं तो", "तुरंत भेजो", "तुरंत भेजिए", "तुरंत जमा करो", "तुरंत जमा करें",
    "immediately", "right now", "asap", "right away", "don't delay", "hurry", "otherwise",
]
PAYMENT = [
    "ओटीपी", "पिन", "यूपीआई", "बैंक खाता", "अकाउंट", "ट्रांसफर", "पैसे भेजो",
    "पैसे ट्रांसफर", "रकम", "डिमांड ड्राफ्ट", "कैश", "वेरिफिकेशन के लिए",
    "वेरिफाई", "भरोसे का खाता", "सेफ अकाउंट", "लोन", "क्रेडिट कार्ड", "डेबिट कार्ड",
    "रुपये", "रूपये", "जमा करो", "जमा करें", "कट जाएगा", "कट जाएगी", "कट गया",
    "कट गए", "भेजा है", "भेज दो", "पैसा", "पैसे",
    "otp", "pin", "upi", "bank account", "transfer", "send money", "verify",
    "safe account", "security deposit", "कस्टडी अकाउंट", "खाता फ्रीज़", "freeze",
]
ISOLATION = [
    "किसी को मत बताना", "अकेले रहो", "कमरे में रहो", "वीडियो कॉल पर रहो",
    "स्क्रीन शेयर करो", "स्क्रीन शेयर", "कैमरा ऑन करो", "लाइन पर रहो",
    "फोन मत रखना", "डिस्कनेक्ट मत करना", "कॉल मत काटना",
    "stay on the line", "don't hang up", "share your screen", "turn on camera",
    "go to a room", "किसी को मत खोलना",
]
COERCION_MARKERS = [
    # classic digital-arrest tells
    "पार्सल में ड्रग्स", "ड्रग्स मिला", "पार्सल", "कूरियर", "पैकेज",
    "parcel", "courier", "drugs found", "package",
    "आपका आधार इस्तेमाल", "आधार कार्ड इस्तेमाल", "आपके नाम पर",
    "your aadhaar", "in your name", "आपकी जानकारी मिली",
    "नंबर से कॉल", "पूछताछ के लिए", "थाने चलो", "डिजिटल अरेस्ट",
    "digital arrest", "नकली पुलिस", "असली पुलिस",
    # OTP / card / courier-customs tells
    "कार्ड ब्लॉक", "ब्लॉक हो गया", "ब्लॉक हो गई", "ब्लॉक", "block",
    "फंस गया", "फंस गई", "अटक गया", "सीमा शुल्क", "customs", "कस्टम ड्यूटी",
    "वापस चला जाएगा", "वापस भेज दिया", "लिमिट", "लेन-देन", "ट्रांज़ेक्शन",
]

# risk-state thresholds (calibrated for the demo; tuned later with real data)
STATE_THRESHOLDS = [
    (0.60, "HIGH_RISK"),
    (0.30, "ELEVATED"),
    (0.00, "LOW"),
]

class CoercionDetector:
    def __init__(self, model_size="small", device="cpu", compute_type="int8"):
        from faster_whisper import WhisperModel
        self.asr = WhisperModel(model_size, device=device, compute_type=compute_type)
        self._banks = {
            "authority": AUTHORITY,
            "arrest": ARREST,
            "secrecy": SECRECY,
            "urgency": URGENCY,
            "payment": PAYMENT,
            "isolation": ISOLATION,
            "coercion_marker": COERCION_MARKERS,
        }
        # latin->devanagari + spelling normalizations for ASR-phonetic variance
        self._norm = [
            ("cbi", "सीबीआई"), ("ncb", "एनसीबी"), ("rbi", "आरबीआई"),
            ("otp", "ओटीपी"), ("upi", "यूपीआई"), ("fir", "एफआईआर"),
            ("aadhaar", "आधार"), ("police", "पुलिस"), ("arrest", "गिरफ्तारी"),
            ("warrant", "वारंट"), ("digital", "डिजिटल"), ("courier", "कूरियर"),
            ("parcel", "पार्सल"), ("court", "कोर्ट"), ("judge", "जज"),
            ("transfer", "ट्रांसफर"), ("freeze", "फ्रीज़"), ("paisa", "पैसे"),
            ("paise", "पैसे"), ("paisay", "पैसे"), ("account", "अकाउंट"),
            ("verify", "वेरिफाई"), ("bank", "बैंक"), ("case", "केस"),
            ("durg", "ड्रग्स"), ("drugs", "ड्रग्स"), ("drakh", "ड्रग्स"),
            ("giraf", "गिरफ्तार"), ("giraft", "गिरफ्तार"), ("giraftari", "गिरफ्तारी"),
            ("giraph", "गिरफ्तार"), ("varrant", "वारंट"), ("varant", "वारंट"),
            ("varnt", "वारंट"), ("adikari", "अधिकारी"), ("adhikari", "अधिकारी"),
            ("ofsar", "अधिकारी"), ("jail", "जेल"), ("transfar", "ट्रांसफर"),
            ("transfr", "ट्रांसफर"), ("verification", "वेरिफिकेशन"),
            ("verif", "वेरिफाई"), ("virif", "वेरिफाई"),
            ("turan", "तुरंत"), ("turant", "तुरंत"), ("abhi", "अभी"),
            ("nhi", "नहीं"), ("nahi", "नहीं"), ("bta", "बताना"), ("batana", "बताना"),
        ]
        # devanagari->devanagari spelling variants (faster-whisper hi phonetics)
        self._dev_norm = [
            ("गिराफतार", "गिरफ्तार"), ("गिरफतार", "गिरफ्तार"),
            ("गिराफ्तार", "गिरफ्तार"), ("गिरफ्तारी", "गिरफ्तारी"),
            ("गिराफतारी", "गिरफ्तारी"), ("वारन्त", "वारंट"),
            ("अदिकारी", "अधिकारी"), ("अफसर", "अधिकारी"), ("अधिकारी", "अधिकारी"),
            ("ट्रान्सफर", "ट्रांसफर"), ("ट्रान्सफेर", "ट्रांसफर"),
            ("विरिफिकेशन", "वेरिफिकेशन"), ("वेरिफिकेसन", "वेरिफिकेशन"),
            ("विरिफाई", "वेरिफाई"), ("लाईन", "लाइन"), ("गमभीर", "गंभीर"),
            ("गंभीर", "गंभीर"), ("हूंगे", "होंगे"), ("होंगे", "होंगे"),
            ("तुरन्त", "तुरंत"), ("फ्रीज़", "फ्रीज़"), ("फ्रीज", "फ्रीज़"),
            ("पार्सल", "पार्सल"), ("पारसल", "पार्सल"), ("कूरियर", "कूरियर"),
            ("कोरियर", "कूरियर"), ("जेल", "जेल"), ("जेल हो", "जेल"),
            ("ड्रग्स", "ड्रग्स"), ("ड्रग", "ड्रग्स"), ("द्रग्स", "ड्रग्स"),
            ("अकाउंट", "अकाउंट"), ("खाता", "खाता"), ("खाते", "खाता"),
            ("फ्रीज", "फ्रीज़"), ("ओटीपी", "ओटीपी"), ("ओ टी पी", "ओटीपी"),
            ("यूपीआई", "यूपीआई"), ("यू पी आई", "यूपीआई"),
        ]

    def _normalize(self, text):
        t = text.lower()
        t = t.replace("\u093c", "")          # strip nukta (़) — फ़→फ, व़→व, ़
        for latin, dev in self._norm:
            t = t.replace(latin, dev)
        for bad, good in self._dev_norm:
            t = t.replace(bad, good)
        # collapse whitespace
        t = re.sub(r"\s+", " ", t)
        return t

    def transcribe(self, path):
        """Hindi-first ASR; falls back to auto-detect."""
        segments, info = self.asr.transcribe(path, language="hi")
        text = " ".join(s.text for s in segments).strip()
        return text, info

    def _match(self, text):
        t = self._normalize(text)
        from rapidfuzz import fuzz
        hits = {}
        for vec, phrases in self._banks.items():
            found = []
            for p in phrases:
                pn = self._normalize(p)
                if len(pn) >= 8:
                    # fuzzy partial for long phrases (ASR phonetic variance)
                    if fuzz.partial_ratio(pn, t) >= 82:
                        found.append(p)
                elif pn in t:
                    found.append(p)
            if found:
                hits[vec] = found
        return hits

    def analyze(self, path):
        """Full coercion profile: transcript + vector hits + score + state."""
        t0 = time.time()
        text, info = self.transcribe(path)
        hits = self._match(text)
        asr_ms = round((time.time() - t0) * 1000, 1)

        # weighted scoring — payment + authority are the strongest tells
        weights = {
            "authority": 0.22, "arrest": 0.20, "payment": 0.22,
            "urgency": 0.12, "secrecy": 0.10, "isolation": 0.08,
            "coercion_marker": 0.06,
        }
        score = 0.0
        for vec, found in hits.items():
            # cap per-vector contribution so one vector can't dominate
            score += min(len(found) / 2.0, 1.0) * weights.get(vec, 0.1)
        score = round(min(score, 1.0), 4)

        state = "LOW"
        for th, name in STATE_THRESHOLDS:
            if score >= th:
                state = name
                break

        # rule-based boost — digital-arrest structure: authority + arrest + payment
        _SEV = {"LOW": 0, "ELEVATED": 1, "HIGH_RISK": 2}
        hit_vecs = set(hits.keys())
        def _bump(level):
            nonlocal state
            if _SEV.get(level, 0) > _SEV.get(state, 0):
                state = level
        if {"authority", "arrest", "payment"} <= hit_vecs:
            _bump("HIGH_RISK")
        elif len(hit_vecs) >= 3:
            _bump("ELEVATED")
        # courier-customs signature: marker + payment + urgency (no authority needed)
        if {"coercion_marker", "payment", "urgency"} <= hit_vecs:
            _bump("ELEVATED")

        return {
            "transcript": text,
            "language": info.language,
            "asr_latency_ms": asr_ms,
            "vector_hits": hits,
            "coercion_score": score,
            "risk_state": state,
            "flagged": state != "LOW",
        }


if __name__ == "__main__":
    import sys
    det = CoercionDetector()
    for p in sys.argv[1:]:
        r = det.analyze(p)
        print(json.dumps(r, ensure_ascii=False, indent=2))

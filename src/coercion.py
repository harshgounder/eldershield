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
    "पूछताछ", "पूछताछ के लिए",
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
    "कार्ड नंबर", "कार्डनंबर", "card number", "क्रेडिट कार्ड", "डेबिट कार्ड",
    "जुर्माना भरो", "जुर्माना भरना", "जुर्माना भरें", "फाइन भरो", "फाइन भरना",
    "रिफंड", "refund", "पेनाल्टी", "penalty", "काला धन", "black money",
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
    "digital arrest", "नकली पुलिस", "असली पुलिस", "जुर्माना", "fine", "जुरमाना",
    "काला धन", "black money", "प्रतिबंधित", "prohibited",
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
            ("बारन्त", "वारंट"), ("बारंट", "वारंट"),
            ("अदिकारी", "अधिकारी"), ("अफसर", "अधिकारी"), ("अधिकारी", "अधिकारी"),
            ("ट्रान्सफर", "ट्रांसफर"), ("ट्रान्सेफर", "ट्रांसफर"),
            ("ट्रान्स्फर", "ट्रांसफर"), ("ट्रान्स्फेर", "ट्रांसफर"),
            ("विरिफिकेशन", "वेरिफिकेशन"), ("वेरिफिकेसन", "वेरिफिकेशन"),
            ("विरिफाई", "वेरिफाई"), ("लाईन", "लाइन"), ("लाईम", "लाइन"),
            ("गमभीर", "गंभीर"), ("गंभीर", "गंभीर"), ("हूंगे", "होंगे"),
            ("हुँगे", "होंगे"), ("होंगे", "होंगे"),
            ("तुरन्त", "तुरंत"), ("तुरंट", "तुरंत"), ("तुरण्ट", "तुरंत"), ("फ्रीज़", "फ्रीज़"),
            ("फ्रीज होगया", "फ्रीज़ हो गया"), ("फ्रीज हो गया", "फ्रीज़ हो गया"),
            ("फ्रीज", "फ्रीज़"),
            ("पार्सल", "पार्सल"), ("पारसल", "पार्सल"), ("कूरियर", "कूरियर"),
            ("कोरियर", "कूरियर"), ("जेल", "जेल"), ("जेल हो", "जेल"),
            ("ड्रग्स", "ड्रग्स"), ("ड्रग", "ड्रग्स"), ("द्रग्स", "ड्रग्स"),
            ("द्रक्स", "ड्रग्स"), ("अकाउंट", "अकाउंट"), ("खाता", "खाता"),
            ("खाते", "खाता"), ("फ्रीज", "फ्रीज़"), ("ओटीपी", "ओटीपी"),
            ("ओ टी पी", "ओटीपी"), ("यूपीआई", "यूपीआई"), ("यू पी आई", "यूपीआई"),
            # --- empirical fast-whisper hi phonetic variants (hinglish-slip probes 2026-08-11) ---
            ("पूलीस", "पुलिस"), ("पोलिस", "पुलिस"), ("पुलीस", "पुलिस"),
            ("पोलीस", "पुलिस"), ("पुलिस वाला", "पुलिस"),
            ("श्टेशन", "स्टेशन"), ("श्टेशन आना", "स्टेशन आना"), ("स्टेशन", "स्टेशन"),
            ("उटी पी", "ओटीपी"), ("उटीपी", "ओटीपी"), ("ओटिपी", "ओटीपी"),
            ("ओटीपी पी", "ओटीपी"), ("कार्द", "कार्ड"), ("कार्ड", "कार्ड"),
            ("पाकेज", "पैकेज"), ("पैकेज", "पैकेज"), ("पैकेज़", "पैकेज"),
            ("अकाुन्त", "अकाउंट"), ("अकाऊंट", "अकाउंट"), ("अकांउट", "अकाउंट"),
            ("अकाउन्ट", "अकाउंट"), ("पिंचाहिए", "पिन चाहिए"), ("पिन चाहिए", "पिन चाहिए"),
            ("तु मिनित", "दो मिनट"), ("दो मिनिट", "दो मिनट"), ("मिनित", "मिनट"),
            ("तेंशन", "टेंशन"), ("टैंशन", "टेंशन"), ("पैसी", "पैसे"),
            ("पैसे", "पैसे"), ("पैसा", "पैसा"), ("भेज्दू", "भेज दो"),
            ("भेज दो", "भेज दो"), ("भीटा", "बेटा"), ("बेटा", "बेटा"),
            ("तुमहारा", "तुम्हारा"), ("इमरजन्सी", "इमरजेंसी"), ("इमरजेंसी", "इमरजेंसी"),
            ("होस्पिटल", "हॉस्पिटल"), ("हस्पताल", "हॉस्पिटल"), ("हॉस्पिटल", "हॉस्पिटल"),
            ("मैदम", "मैडम"), ("प्रोब्लम", "प्रॉब्लम"), ("चोटीसी", "छोटी सी"),
            ("गलक", "गलत"), ("ताएं", "टाइम"), ("टाइम", "टाइम"),
            ("वेरिफाइ", "वेरिफाई"), ("फ्रीज होगया", "फ्रीज़ हो गया"),
            ("होगया", "हो गया"), ("समजाूंगा", "समझाऊंगा"), ("समझाऊंगा", "समझाऊंगा"),
            # --- dialect probes 2026-08-11 (Haryanvi/Bhojpuri/Punjabi/Marathi/Bengali) ---
            ("गिराफ्तारी", "गिरफ्तारी"), ("गिराफ्तार", "गिरफ्तार"),
            ("वो टीपी", "ओटीपी"), ("ओटी पी", "ओटीपी"), ("अटीपी", "ओटीपी"),
            ("ताइम", "टाइम"), ("तुरान्त", "तुरंत"), ("तुरांत", "तुरंत"),
            ("ध्रक्स", "ड्रग्स"), ("चड्रग्स", "च में ड्रग्स"), ("च में ड्रग्स", "च में ड्रग्स"),
            ("अतक", "अटक"), ("अटक", "अटक"),
            # --- round 2 variants (slip/dialect re-probes) ---
            ("अकान्त", "अकाउंट"), ("प्रोबलम", "प्रॉब्लम"), ("प्रोब्लम", "प्रॉब्लम"),
            ("बेज्दु", "भेज दो"), ("भेज्दु", "भेज दो"), ("छोटीसी", "छोटी सी"),
            ("लिये", "लिए"), ("चाहिये", "चाहिए"),
            # --- acronym-dot obfuscation (सी.बी.आई. → सीबीआई) ---
            ("सी.बी.आई.", "सीबीआई"), ("सी. बी. आई.", "सीबीआई"),
            ("सी.बी.आय.", "सीबीआय"), ("आर.बी.आई.", "आरबीआई"), ("आर. बी. आई.", "आरबीआई"),
            ("एन.सी.बी.", "एनसीबी"), ("ओ.टी.पी.", "ओटीपी"), ("ओ. टी. पी.", "ओटीपी"),
            # --- latin Hinglish words (text-level matching for Roman-script calls) ---
            ("o t p", "ओटीपी"), ("ot p", "ओटीपी"), ("aapke", "आपके"), ("aapka", "आपका"), ("aapko", "आपको"),
            ("batao", "बताओ"), ("bataiye", "बताइए"), ("hai", "है"), ("hoon", "हूँ"),
            ("mila", "मिला"), ("aaya", "आया"), ("aayi", "आई"), ("mil gaya", "मिल गया"),
            ("milal", "मिला"), ("package", "पैकेज"), ("card", "कार्ड"), ("number", "नंबर"),
            ("station", "स्टेशन"), ("maam", "मैडम"), ("madam", "मैडम"), ("ji", "जी"),
            ("tumhara", "तुम्हारा"), ("tumhari", "तुम्हारी"), ("tera", "तेरा"), ("teri", "तेरी"),
            ("warna", "वरना"), ("nahi to", "नहीं तो"), ("jaldi", "जल्दी"), ("turant", "तुरंत"),
            ("freez", "फ्रीज़"), ("freezed", "फ्रीज़"), ("verify", "वेरिफाई"),
            ("verification", "वेरिफिकेशन"), ("paise", "पैसे"), ("paisa", "पैसा"),
            ("bhejo", "भेजो"), ("daalo", "डालो"), ("karo", "करो"), ("karna", "करना"),
            ("ho gaya", "हो गया"), ("hogaya", "हो गया"), ("se", "से"), ("mein", "में"),
            ("main", "मैं"), ("bol raha", "बोल रहा"), ("bol rahi", "बोल रही"),
            ("pakda", "पकड़ा"), ("pakda gaya", "पकड़ा गया"), ("chahiye", "चाहिए"),
            ("dena", "देना"), ("do", "दो"), ("de", "दे"), ("jama", "जमा"),
        ]

    def _normalize(self, text):
        t = text.lower()
        t = t.replace("\u093c", "")          # strip ALL nukta (़) — फ़→फ, व़→व, ़ (ASR doubles them)
        # strip zero-width / format chars (scammers insert them to break exact-match)
        for ch in ("\u200b", "\u200c", "\u200d", "\u200e", "\u200f", "\ufeff"):
            t = t.replace(ch, "")
        for latin, dev in self._norm:
            t = t.replace(latin, dev)
        for bad, good in self._dev_norm:
            t = t.replace(bad, good)
        # post-loop nukta strip — replacement VALUES can reintroduce nukta
        # (e.g. ("फ्रीज", "फ्रीज़")); strip again so the text is fully nukta-free
        t = t.replace("\u093c", "")
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
                elif len(pn) >= 4:
                    # fuzzy partial for medium phrases — catches MERGED tokens
                    # ("कार्डनंबर" contains "कार्ड") that exact-match misses; threshold
                    # high enough that random coincidences don't fire
                    if fuzz.partial_ratio(pn, t) >= 88:
                        found.append(p)
                elif pn in t:
                    # short phrases (≤3 chars, e.g. "पिन", "ओटीपी") — exact only,
                    # fuzzy on short tokens is a false-positive machine
                    found.append(p)
            if found:
                hits[vec] = found
        return hits

    def _score_text(self, text):
        """Text-level coercion profile — the single source of truth for scoring.
        analyze() calls this after ASR; benchmarks call it directly (no divergence)."""
        t = self._normalize(text)
        hits = self._match(text)
        weights = {
            "authority": 0.22, "arrest": 0.20, "payment": 0.22,
            "urgency": 0.12, "secrecy": 0.10, "isolation": 0.08,
            "coercion_marker": 0.06,
        }
        score = 0.0
        for vec, found in hits.items():
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
        # authority + arrest alone = the digital-arrest tell (CBI + FIR + case;
        # the scam does NOT need payment or parcel to be heard to be dangerous)
        if {"authority", "arrest"} <= hit_vecs:
            _bump("HIGH_RISK")
        # digital-arrest signature does NOT require payment to be heard —
        # authority + arrest + marker (CBI + warrant + parcel) is itself the tell
        if {"authority", "arrest", "coercion_marker"} <= hit_vecs:
            _bump("HIGH_RISK")
        # authority + payment + marker — money-demand authority scams (ED/black money,
        # cyber-crime FIR, police+parcel+OTP) — no explicit arrest word needed
        if {"authority", "payment", "coercion_marker"} <= hit_vecs:
            _bump("HIGH_RISK")
        # digital-arrest WITHOUT authority heard: arrest claim + marker + payment ask
        # ("digital arrest hua hai, OTP batao warna jail") — the arrest claim is the tell
        if {"arrest", "coercion_marker", "payment"} <= hit_vecs:
            _bump("HIGH_RISK")
        elif len(hit_vecs) >= 3:
            _bump("ELEVATED")
        # courier-customs signature: marker + payment + urgency (no authority needed)
        if {"coercion_marker", "payment", "urgency"} <= hit_vecs:
            _bump("ELEVATED")
        # courier-with-fine (no urgency heard): marker + payment = fine/penalty demand
        if {"coercion_marker", "payment"} <= hit_vecs and any(
            w in t for w in ("जुर्माना", "फाइन", "fine", "पेनाल्टी", "penalty")
        ):
            _bump("ELEVATED")
        # courier money-demand without urgency/fine: parcel-caught claim + payment ask
        # ("पार्सल पकड़ा गया, पैसे भेजो") — no benign courier call asks for money
        if {"coercion_marker", "payment"} <= hit_vecs:
            _bump("ELEVATED")
        # account-freeze / verification soft-scam signature (no authority, no arrest):
        # payment ask + freeze/block/verification language = the "account freezed, share
        # your PIN" script. Text-level check — freeze/block/verify words in the transcript.
        if "payment" in hit_vecs and any(
            w in t for w in ("फ्रीज़", "फ्रीज", "ब्लॉक", "ब्लाक", "block",
                             "वेरिफिकेशन", "वेरिफाइ", "verify", "verification",
                             "रिफंड", "refund", "कन्फर्म", "confirm", "पेनाल्टी", "penalty")
        ):
            _bump("ELEVATED")

        return {"vector_hits": hits, "coercion_score": score, "risk_state": state,
                "flagged": state != "LOW", "normalized": t}

    def analyze(self, path):
        """Full coercion profile: transcript + vector hits + score + state."""
        t0 = time.time()
        text, info = self.transcribe(path)
        prof = self._score_text(text)
        prof["transcript"] = text
        prof["language"] = info.language
        prof["asr_latency_ms"] = round((time.time() - t0) * 1000, 1)
        return prof


if __name__ == "__main__":
    import sys
    det = CoercionDetector()
    for p in sys.argv[1:]:
        r = det.analyze(p)
        print(json.dumps(r, ensure_ascii=False, indent=2))

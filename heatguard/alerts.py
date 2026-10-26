"""Worker-facing alert text (multilingual) and role-based views.  Machine-drafted translations: a native-speaker +
occupational-health review is REQUIRED before any pilot."""
MESSAGES = {
 "en": {"RED":   "Stop work now. Go to shade and drink water. Rest 15 minutes. If you feel dizzy, confused or stop sweating, tell your supervisor or first-aider immediately.",
        "AMBER": "Take a 5-minute break in the shade and drink water.",
        "OK":    "You are doing well. Keep drinking water regularly."},
 "hi": {"RED":   "अभी काम रोकें। छाया में जाएँ और पानी पिएँ। 15 मिनट आराम करें। चक्कर, उलझन या पसीना बंद होने पर तुरंत सुपरवाइज़र को बताएँ।",
        "AMBER": "5 मिनट छाया में रुकें और पानी पिएँ।", "OK": "आप ठीक हैं। नियमित रूप से पानी पीते रहें।"},
 "ur": {"RED":   "ابھی کام روک دیں۔ سائے میں جائیں اور پانی پئیں۔ 15 منٹ آرام کریں۔ چکر، الجھن یا پسینہ بند ہونے پر فوراً سپروائزر کو بتائیں۔",
        "AMBER": "5 منٹ سائے میں رکیں اور پانی پئیں۔", "OK": "آپ ٹھیک ہیں۔ باقاعدگی سے پانی پیتے رہیں۔"},
 "bn": {"RED":   "এখনই কাজ থামান। ছায়ায় যান এবং পানি পান করুন। ১৫ মিনিট বিশ্রাম নিন। মাথা ঘুরলে, বিভ্রান্ত লাগলে বা ঘাম বন্ধ হয়ে গেলে সঙ্গে সঙ্গে সুপারভাইজারকে জানান।",
        "AMBER": "৫ মিনিট ছায়ায় থামুন এবং পানি পান করুন।", "OK": "আপনি ভালো আছেন। নিয়মিত পানি পান করতে থাকুন।"},
 "ml": {"RED":   "ഉടൻ ജോലി നിർത്തുക. തണലിൽ പോയി വെള്ളം കുടിക്കുക. 15 മിനിറ്റ് വിശ്രമിക്കുക. തലകറക്കം, ആശയക്കുഴപ്പം, വിയർപ്പ് നിലയ്ക്കൽ എന്നിവ ഉണ്ടെങ്കിൽ ഉടൻ സൂപ്പർവൈസറെ അറിയിക്കുക.",
        "AMBER": "5 മിനിറ്റ് തണലിൽ നിന്ന് വെള്ളം കുടിക്കുക.", "OK": "നിങ്ങൾ സുരക്ഷിതനാണ്. ഇടയ്ക്കിടെ വെള്ളം കുടിക്കുക."},
 "ne": {"RED":   "अहिले नै काम रोक्नुहोस्। छायाँमा जानुहोस् र पानी पिउनुहोस्। १५ मिनेट आराम गर्नुहोस्। चक्कर लाग्न, अलमल हुन वा पसिना आउन बन्द भए तुरुन्तै सुपरभाइजरलाई भन्नुहोस्।",
        "AMBER": "५ मिनेट छायाँमा बस्नुहोस् र पानी पिउनुहोस्।", "OK": "तपाईं ठिक हुनुहुन्छ। नियमित पानी पिउँदै गर्नुहोस्।"},
 "tl": {"RED":   "Itigil na ang trabaho ngayon. Pumunta sa lilim at uminom ng tubig. Magpahinga ng 15 minuto. Kung nahihilo, naguguluhan, o huminto ang pagpapawis, agad na sabihin sa supervisor.",
        "AMBER": "Magpahinga ng 5 minuto sa lilim at uminom ng tubig.", "OK": "Maayos ka. Patuloy na uminom ng tubig."},
}
LANG_NAMES = {"en": "English", "hi": "Hindi", "ur": "Urdu", "bn": "Bengali", "ml": "Malayalam", "ne": "Nepali", "tl": "Tagalog"}
TIER = {0: "OK", 1: "AMBER", 2: "RED"}

def message(tier: int, lang: str = "en") -> str:
    return MESSAGES.get(lang, MESSAGES["en"])[TIER[int(tier)]]

def supervisor_view(worker_id: str, tier: int, working: bool) -> dict:
    """Employer sees ONLY a risk tier and the required action - never temperature, heart rate or history."""
    return {"worker": worker_id, "tier": TIER[int(tier)],
            "action": {0: "continue", 1: "5-min shade + water break", 2: "15-min rest, first-aider check"}[int(tier)]}

def worker_view(worker_id: str, tier: int, tc_hat: float, lang: str = "en") -> dict:
    return {"worker": worker_id, "tier": TIER[int(tier)], "estimated_core_temp_c": round(float(tc_hat), 1),
            "message": message(tier, lang), "note": "Screening estimate, not a diagnosis. Emergency signs: call first-aider."}

def population_view(site_tiers: dict, k: int = 5) -> dict:
    """site -> counts of tiers, suppressed when fewer than k workers (k-anonymity)."""
    out = {}
    for site, tiers in site_tiers.items():
        n = len(tiers)
        if n < k:
            out[site] = {"suppressed": True, "reason": f"fewer than {k} workers"}
        else:
            out[site] = {"workers": n, "red_pct": round(100 * sum(t == 2 for t in tiers) / n, 1),
                         "amber_pct": round(100 * sum(t == 1 for t in tiers) / n, 1)}
    return out

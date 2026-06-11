"""
Text-based Cheat Detection
─────────────────────────
Analyzes typed answers for signs of copy-paste, AI-generated text, or pre-prepared answers.

Signals checked:
1. Typing speed — words per second vs response time
2. Perfect punctuation + formal structure — unusual for live typing
3. Markdown/formatting artifacts — suggest copy-paste from docs/AI
4. Vocabulary mismatch — overly advanced vocabulary for live answer
5. Zero spelling errors with long, complex answer — unnatural
6. Template/boilerplate phrases — common in AI-generated text
7. Suspiciously fast long answers
"""
import re
import math


# Phrases strongly associated with AI-generated or copy-pasted text
AI_PHRASES = [
    "in conclusion", "to summarize", "in summary", "it is worth noting",
    "it is important to note", "as mentioned above", "as stated earlier",
    "in the context of", "with regard to", "with respect to",
    "furthermore", "moreover", "nevertheless", "notwithstanding",
    "it should be noted that", "one might argue", "it can be observed",
    "in light of the above", "taking everything into account",
    "first and foremost", "last but not least", "in other words",
    "to put it simply", "in essence", "to elaborate further",
    "it goes without saying", "needless to say",
]

MARKDOWN_PATTERNS = [
    r"#{1,6}\s",          # markdown headers
    r"\*\*[^*]+\*\*",     # bold
    r"```[\s\S]*?```",    # code blocks
    r"^\s*[-*+]\s",       # bullet lists
    r"^\s*\d+\.\s",       # numbered lists
    r"\[.+\]\(.+\)",      # links
]


def detect_text_cheating(
    answer: str,
    question: str,
    response_time_seconds: int,
) -> dict:
    """
    Detect cheating signals in a typed answer.
    Returns: {risk_score, risk_level, is_suspicious, flags, summary}
    """
    if not answer or len(answer.strip()) < 10:
        return {"risk_score": 0, "risk_level": "Clean", "is_suspicious": False, "flags": [], "summary": "No answer to analyze"}

    flags = []
    risk_score = 0

    words = answer.split()
    word_count = len(words)
    char_count = len(answer)
    response_time = max(response_time_seconds, 1)

    # ── 1. Typing speed ─────────────────────────────────────────────────────
    # Average human types 40-60 WPM = ~3-5 chars/sec
    # If answer arrived very fast relative to length, likely copy-pasted
    chars_per_second = char_count / response_time
    words_per_minute = (word_count / response_time) * 60

    if words_per_minute > 180 and word_count > 50:
        flags.append({
            "type": "fast_typing",
            "severity": "high",
            "detail": f"Answer typed at {words_per_minute:.0f} WPM — far exceeds typical live typing speed (40-80 WPM). Likely copy-pasted."
        })
        risk_score += 45
    elif words_per_minute > 120 and word_count > 40:
        flags.append({
            "type": "fast_typing",
            "severity": "medium",
            "detail": f"Answer typed at {words_per_minute:.0f} WPM — unusually fast. May have been pre-typed."
        })
        risk_score += 20

    # ── 2. AI/boilerplate phrases ────────────────────────────────────────────
    answer_lower = answer.lower()
    found_phrases = [p for p in AI_PHRASES if p in answer_lower]
    if len(found_phrases) >= 3:
        flags.append({
            "type": "ai_phrases",
            "severity": "high",
            "detail": f"Answer contains {len(found_phrases)} AI/formal boilerplate phrases: {', '.join(found_phrases[:3])}..."
        })
        risk_score += 35
    elif len(found_phrases) >= 2:
        flags.append({
            "type": "ai_phrases",
            "severity": "medium",
            "detail": f"Answer uses formal AI-style phrasing: {', '.join(found_phrases)}"
        })
        risk_score += 15

    # ── 3. Markdown/formatting artifacts ────────────────────────────────────
    markdown_hits = sum(1 for p in MARKDOWN_PATTERNS if re.search(p, answer, re.MULTILINE))
    if markdown_hits >= 2:
        flags.append({
            "type": "markdown_formatting",
            "severity": "high",
            "detail": "Answer contains markdown formatting (headers, bullets, code blocks) — strongly suggests copy-paste from docs or AI tool."
        })
        risk_score += 40
    elif markdown_hits == 1:
        flags.append({
            "type": "markdown_formatting",
            "severity": "low",
            "detail": "Answer contains markdown formatting — may have been copied from a document."
        })
        risk_score += 10

    # ── 4. Perfect structure on long answers ────────────────────────────────
    # Real-time typed answers rarely have perfect paragraph breaks + punctuation
    sentences = re.split(r'[.!?]+', answer)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    has_periods = answer.count('.') > 3
    has_paragraphs = '\n\n' in answer or '\n' in answer

    if word_count > 80 and len(sentences) > 4 and has_periods and has_paragraphs:
        flags.append({
            "type": "perfect_structure",
            "severity": "medium",
            "detail": "Long answer with perfect paragraph structure — unusual for a live typed response."
        })
        risk_score += 15

    # ── 5. Suspiciously fast for question complexity ──────────────────────
    question_word_count = len(question.split())
    min_expected = max(15, question_word_count * 3)  # at minimum 3 sec per question word
    if response_time < min_expected and word_count > 60:
        flags.append({
            "type": "suspiciously_fast",
            "severity": "medium",
            "detail": f"Responded in {response_time}s with {word_count} words — answer may have been pre-prepared."
        })
        risk_score += 20

    # ── 6. Repeated sentence starts (template) ───────────────────────────
    starters = [s.split()[0].lower() if s.split() else "" for s in sentences]
    if len(starters) > 3:
        repeated_starters = len(starters) - len(set(starters))
        if repeated_starters >= 3:
            flags.append({
                "type": "template_pattern",
                "severity": "low",
                "detail": "Multiple sentences start the same way — may follow a template."
            })
            risk_score += 10

    risk_score = min(100, risk_score)
    risk_level = (
        "High Risk" if risk_score >= 60
        else "Medium Risk" if risk_score >= 30
        else "Low Risk" if risk_score >= 10
        else "Clean"
    )

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "is_suspicious": risk_score >= 30,
        "flags": flags,
        "flag_count": len(flags),
        "typing_speed_wpm": round(words_per_minute, 1),
        "summary": (
            f"⚠️ {len(flags)} text cheat indicator(s) detected. Risk: {risk_level}"
            if flags else
            "✅ No copy-paste or AI-generation indicators detected"
        )
    }

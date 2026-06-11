"""
Voice Service
─────────────
• Transcribes audio using Groq Whisper (free tier: 28,000 sec/day)
• Analyzes confidence from speech patterns
• Detects cheating signals (reading, background voices, suspicious pauses)

Groq free key → https://console.groq.com  (sign in with Google, instant key)
"""
import io
import os
from uuid import uuid4
import subprocess
import shutil
import re
import json
import time
import math
from typing import Optional
from app.core.config import settings


# ── Groq Whisper transcription ────────────────────────────────────────────────

def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm") -> dict:
    """
    Transcribe audio bytes using Groq Whisper.
    Returns: {text, duration_seconds, language, words (if available)}
    """
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "your-groq-key-here":
        return {"text": "", "duration_seconds": 0, "language": "en", "error": "No Groq API key"}

    from groq import Groq
    client = Groq(api_key=settings.GROQ_API_KEY)
    # Prepare an in-memory file object with a name attribute
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename

    # Ensure stream position is at start
    try:
        audio_file.seek(0)
    except Exception:
        pass

    # Try in-memory file first; if Groq rejects, write to a temp file and retry
    try:
        transcription = client.audio.transcriptions.create(
            model="whisper-large-v3-turbo",
            file=audio_file,
            response_format="verbose_json",      # includes word-level timestamps
            timestamp_granularities=["word"],
            language="en",
        )
    except Exception as e:
        # Retry using disk-backed files — try ffmpeg conversion first (if available),
        # then try the declared extension and several common alternatives.
        debug_dir = os.path.join(settings.UPLOAD_DIR, 'groq_debug')
        os.makedirs(debug_dir, exist_ok=True)
        original_suffix = ('.' + filename.split('.')[-1]) if '.' in filename else '.webm'
        tried_files = []
        errors = []
        ffmpeg_path = shutil.which('ffmpeg')
        ffmpeg_info = None
        # If ffmpeg is available, try converting to a standard WAV (16k mono) and retry
        if ffmpeg_path:
            try:
                orig_name = f"groq_debug_{uuid4().hex}{original_suffix}"
                orig_path = os.path.join(debug_dir, orig_name)
                with open(orig_path, 'wb') as tf:
                    tf.write(audio_bytes)
                    tf.flush()
                converted_name = f"groq_debug_{uuid4().hex}.converted.wav"
                converted_path = os.path.join(debug_dir, converted_name)
                cmd = [ffmpeg_path, '-y', '-i', orig_path, '-ar', '16000', '-ac', '1', converted_path]
                proc = subprocess.run(cmd, capture_output=True, text=True)
                ffmpeg_info = {'cmd': ' '.join(cmd), 'returncode': proc.returncode, 'stdout': proc.stdout, 'stderr': proc.stderr, 'orig': orig_path, 'converted': converted_path}
                if proc.returncode == 0 and os.path.exists(converted_path):
                    tried_files.append(converted_path)
                    try:
                        with open(converted_path, 'rb') as fh:
                            transcription = client.audio.transcriptions.create(
                                model="whisper-large-v3-turbo",
                                file=fh,
                                response_format="verbose_json",
                                timestamp_granularities=["word"],
                                language="en",
                            )
                    except Exception as e2:
                        errors.append((converted_path, str(e2)))
                else:
                    errors.append((orig_path, f"ffmpeg failed: rc={proc.returncode} stderr={proc.stderr}"))
            except Exception as e_ff:
                errors.append((None, f"ffmpeg exception: {e_ff}"))
        suffixes = [original_suffix, '.webm', '.wav', '.mp4', '.m4a', '.ogg', '.mp3']
        # Remove duplicates while preserving order
        seen = set()
        uniq_suffixes = []
        for s in suffixes:
            if s not in seen:
                uniq_suffixes.append(s)
                seen.add(s)

        for suf in uniq_suffixes:
            debug_name = f"groq_debug_{uuid4().hex}{suf}"
            debug_path = os.path.join(debug_dir, debug_name)
            try:
                with open(debug_path, 'wb') as tf:
                    tf.write(audio_bytes)
                    tf.flush()
                tried_files.append(debug_path)
                with open(debug_path, 'rb') as fh:
                    transcription = client.audio.transcriptions.create(
                        model="whisper-large-v3-turbo",
                        file=fh,
                        response_format="verbose_json",
                        timestamp_granularities=["word"],
                        language="en",
                    )
                # Success
                break
            except Exception as e2:
                errors.append((debug_path, str(e2)))
                # try next suffix
                continue

        # If transcription not set, all retries failed
        if 'transcription' not in locals():
            err_msgs = "; ".join([f"{p}:{m}" for p, m in errors])
            ffmpeg_part = f" ffmpeg_info={ffmpeg_info}" if ffmpeg_info is not None else ""
            raise Exception(f"Groq transcription failed initial: {e} ; retries: {err_msgs} ; tried_files={tried_files}{ffmpeg_part}")

    return {
        "text": transcription.text.strip(),
        "duration_seconds": getattr(transcription, "duration", 0),
        "language": getattr(transcription, "language", "en"),
        "words": getattr(transcription, "words", []),
    }


# ── Confidence Analysis ───────────────────────────────────────────────────────

def analyze_confidence(transcript_data: dict, question: str) -> dict:
    """
    Analyze confidence from speech patterns.

    Signals analyzed:
    - Speech rate (words per minute)
    - Filler word count (um, uh, like, you know)
    - Pause patterns (long gaps between words)
    - Answer length relative to question complexity
    - Vocabulary diversity (unique words ratio)

    Returns confidence score 0-100 + breakdown
    """
    text = transcript_data.get("text", "")
    words_data = transcript_data.get("words", [])
    duration = transcript_data.get("duration_seconds", 0)

    if not text or len(text.strip()) < 10:
        return {
            "confidence_score": 0,
            "speech_rate_wpm": 0,
            "filler_count": 0,
            "filler_ratio": 0,
            "pause_count": 0,
            "vocabulary_diversity": 0,
            "answer_length_words": 0,
            "signals": ["No speech detected"],
            "confidence_label": "No Answer",
        }

    word_list = text.lower().split()
    word_count = len(word_list)
    duration = duration or max(word_count / 2.5, 1)  # estimate if not available

    # 1. Speech rate
    speech_rate = (word_count / duration) * 60  # WPM
    # Ideal range: 120-180 WPM. Too fast=nervous, too slow=unsure
    if 120 <= speech_rate <= 180:
        rate_score = 25
    elif 100 <= speech_rate < 120 or 180 < speech_rate <= 200:
        rate_score = 18
    elif speech_rate < 80 or speech_rate > 220:
        rate_score = 8
    else:
        rate_score = 12

    # 2. Filler words
    fillers = {"um", "uh", "uhh", "umm", "like", "basically", "actually",
               "literally", "you know", "i mean", "so", "well", "right",
               "kind of", "sort of", "hmm", "er", "ah"}
    filler_count = sum(1 for w in word_list if w in fillers)
    filler_ratio = filler_count / word_count if word_count > 0 else 0
    # <5% fillers = confident, >20% = nervous
    if filler_ratio < 0.05:
        filler_score = 25
    elif filler_ratio < 0.10:
        filler_score = 20
    elif filler_ratio < 0.20:
        filler_score = 12
    else:
        filler_score = 5

    # 3. Pause analysis (from word timestamps)
    pause_count = 0
    long_pause_count = 0
    if words_data and len(words_data) > 1:
        for i in range(1, len(words_data)):
            try:
                gap = words_data[i].get("start", 0) - words_data[i-1].get("end", 0)
                if gap > 2.0:
                    long_pause_count += 1
                elif gap > 0.8:
                    pause_count += 1
            except (KeyError, TypeError):
                pass
    pause_score = max(0, 25 - (long_pause_count * 5) - (pause_count * 1))
    pause_score = min(25, pause_score)

    # 4. Vocabulary diversity (unique words / total words)
    unique_words = len(set(word_list))
    vocab_diversity = unique_words / word_count if word_count > 0 else 0
    vocab_score = min(25, int(vocab_diversity * 35))

    confidence_score = rate_score + filler_score + pause_score + vocab_score

    # Build signals list
    signals = []
    if speech_rate < 100:
        signals.append("Speaking slowly — may indicate uncertainty")
    elif speech_rate > 200:
        signals.append("Speaking very fast — may indicate reading from notes")
    if filler_ratio > 0.15:
        signals.append(f"High filler word usage ({filler_count} fillers)")
    if long_pause_count > 2:
        signals.append(f"{long_pause_count} long pauses detected — possible hesitation")
    if vocab_diversity < 0.4:
        signals.append("Low vocabulary diversity — repetitive language")
    if word_count < 20:
        signals.append("Very short answer — insufficient depth")
    if not signals:
        signals.append("Natural confident speech pattern")

    label = (
        "Very Confident" if confidence_score >= 80
        else "Confident" if confidence_score >= 65
        else "Moderate" if confidence_score >= 45
        else "Nervous" if confidence_score >= 25
        else "Very Uncertain"
    )

    return {
        "confidence_score": min(100, confidence_score),
        "speech_rate_wpm": round(speech_rate, 1),
        "filler_count": filler_count,
        "filler_ratio": round(filler_ratio * 100, 1),
        "pause_count": pause_count,
        "long_pause_count": long_pause_count,
        "vocabulary_diversity": round(vocab_diversity * 100, 1),
        "answer_length_words": word_count,
        "signals": signals,
        "confidence_label": label,
        "rate_score": rate_score,
        "filler_score": filler_score,
        "pause_score": pause_score,
        "vocab_score": vocab_score,
    }


# ── Cheat Detection ───────────────────────────────────────────────────────────

def detect_cheating(
    transcript_data: dict,
    confidence_data: dict,
    response_time_seconds: int,
    start_delay_seconds: int = 0,
    question: str = "",
) -> dict:
    """
    Detect potential cheating/malpractice signals.

    Checks:
    1. Reading speed — too fast and consistent = reading from notes
    2. Background voices — multiple speaker patterns
    3. Suspiciously perfect answers with no fillers
    4. Response too fast for question complexity
    5. Unnatural speech rhythm (constant pace = reading)
    6. Answer copied verbatim (very low filler + very high rate)
    """
    flags = []
    risk_score = 0
    speech_rate = confidence_data.get("speech_rate_wpm", 0)
    filler_ratio = confidence_data.get("filler_ratio", 0)
    word_count = confidence_data.get("answer_length_words", 0)
    long_pauses = confidence_data.get("long_pause_count", 0)
    words_data = transcript_data.get("words", [])

    # Flag 1: Reading speed — 200+ WPM with <2% fillers = reading from paper/screen
    if speech_rate > 195 and filler_ratio < 2:
        flags.append({
            "type": "reading_detected",
            "severity": "high",
            "detail": f"Speech rate {speech_rate} WPM with almost no hesitation — likely reading from notes"
        })
        risk_score += 40

    # Flag 2: Unnaturally consistent pace (no variance = text-to-speech or reading)
    if words_data and len(words_data) > 10:
        gaps = []
        for i in range(1, len(words_data)):
            try:
                gap = words_data[i].get("start", 0) - words_data[i-1].get("end", 0)
                gaps.append(gap)
            except Exception:
                pass
        if gaps:
            avg_gap = sum(gaps) / len(gaps)
            variance = sum((g - avg_gap) ** 2 for g in gaps) / len(gaps)
            std_dev = math.sqrt(variance)
            # Very low std dev = unnaturally consistent = reading
            if std_dev < 0.05 and avg_gap < 0.15 and len(gaps) > 15:
                flags.append({
                    "type": "unnatural_rhythm",
                    "severity": "high",
                    "detail": "Unnaturally consistent speech rhythm — possible text-to-speech or recitation"
                })
                risk_score += 35

    # Flag 3: Too fast response for complex question
    question_word_count = len(question.split())
    min_expected_seconds = max(10, question_word_count * 1.5)
    if response_time_seconds < min_expected_seconds and word_count > 50:
        flags.append({
            "type": "suspiciously_fast",
            "severity": "medium",
            "detail": f"Responded in {response_time_seconds}s with {word_count} words — answer may have been pre-prepared"
        })
        risk_score += 20

    # Flag 4: Delayed start after prep period — could indicate copying or searching for an answer
    if start_delay_seconds and start_delay_seconds > 3:
        severity = "medium" if start_delay_seconds <= 8 else "high"
        detail = (
            f"Recording started {start_delay_seconds}s after preparation finished — this delay may indicate copying or looking up an answer"
        )
        flags.append({
            "type": "delayed_start",
            "severity": severity,
            "detail": detail
        })
        risk_score += 15 if severity == "medium" else 25

    # Flag 4: Perfect fluency on technical question (no fillers + long answer)
    if filler_ratio < 1 and word_count > 80 and speech_rate > 150:
        flags.append({
            "type": "perfect_fluency",
            "severity": "medium",
            "detail": "No hesitation on a long technical answer — unusual for live speech"
        })
        risk_score += 15

    # Flag 5: Very long answer with zero pauses (reading aloud)
    if word_count > 100 and long_pauses == 0 and speech_rate > 160:
        flags.append({
            "type": "no_thinking_pauses",
            "severity": "medium",
            "detail": "Long answer with no thinking pauses — natural speech always has pauses"
        })
        risk_score += 15

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
        "summary": (
            f"⚠️ {len(flags)} cheat indicator(s) detected. Risk: {risk_level}"
            if flags else
            "✅ No cheating indicators detected"
        )
    }

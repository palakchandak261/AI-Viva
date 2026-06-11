"""
Voice Routes
────────────
POST /api/voice/transcribe          — transcribe audio, analyze confidence + cheating
POST /api/voice/submit-voice-answer — transcribe + submit answer in one shot
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.api.deps import get_current_student
from app.models.user import User
from app.models.viva_session import VivaSession, VivaExchange, SessionStatus
from app.services.voice_service import transcribe_audio, analyze_confidence, detect_cheating
from app.services.viva_engine import viva_engine
from app.core.config import settings
from fastapi.responses import FileResponse
import os
from pathlib import Path

router = APIRouter(prefix="/voice", tags=["Voice"])

MAX_AUDIO_MB = 25


@router.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    question: str = Form(default=""),
    response_time_seconds: int = Form(default=0),
    blob_type: str = Form(default=""),
    current_user: User = Depends(get_current_student),
):
    """
    Transcribe audio and return:
    - transcript text
    - confidence analysis
    - cheat detection report
    """
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "your-groq-key-here":
        raise HTTPException(
            status_code=503,
            detail="Voice transcription not configured. Add GROQ_API_KEY to .env."
        )

    audio_bytes = await audio.read()
    if len(audio_bytes) > MAX_AUDIO_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Audio too large. Max {MAX_AUDIO_MB}MB.")
    if len(audio_bytes) < 1000:
        raise HTTPException(status_code=400, detail="Audio too short or empty.")

    # Debug: log incoming upload details to help diagnose invalid-media issues
    try:
        print(f"[voice.transcribe] file={audio.filename} size={len(audio_bytes)} blob_type={blob_type}")
    except Exception:
        pass

    # Transcribe
    try:
        transcript_data = transcribe_audio(audio_bytes, filename=audio.filename or "audio.webm")
    except Exception as e:
        # Log full exception for debugging (includes temp_file path when available)
        try:
            print(f"[voice.transcribe] transcription exception: {e}")
        except Exception:
            pass
        message = str(e)
        if "could not process file" in message.lower() or "invalid media file" in message.lower():
            raise HTTPException(status_code=400, detail="Invalid audio file. Please re-record and try again.")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {message}")

    if not transcript_data.get("text"):
        return {
            "transcript": "",
            "confidence": None,
            "cheat_detection": None,
            "error": "No speech detected in audio"
        }

    # Analyze confidence
    confidence = analyze_confidence(transcript_data, question)

    # Detect cheating
    cheat = detect_cheating(
        transcript_data=transcript_data,
        confidence_data=confidence,
        response_time_seconds=response_time_seconds,
        question=question,
    )

    return {
        "transcript": transcript_data["text"],
        "duration_seconds": transcript_data.get("duration_seconds", 0),
        "confidence": confidence,
        "cheat_detection": cheat,
    }


@router.post("/submit-voice-answer")
async def submit_voice_answer(
    audio: UploadFile = File(...),
    session_id: str = Form(...),
    exchange_id: str = Form(...),
    response_time_seconds: int = Form(default=0),
    start_delay_seconds: int = Form(default=0),
    blob_type: str = Form(default=""),
    question: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_student),
):
    """
    All-in-one: transcribe audio → analyze → submit answer → get next question.
    Frontend calls this instead of the separate transcribe + submit flow.
    """
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "your-groq-key-here":
        raise HTTPException(status_code=503, detail="Voice not configured. Add GROQ_API_KEY to .env.")

    # Validate session ownership
    sess_result = await db.execute(
        select(VivaSession).where(VivaSession.id == session_id)
    )
    session = sess_result.scalar_one_or_none()
    if not session or str(session.student_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.status != SessionStatus.in_progress:
        raise HTTPException(status_code=400, detail="Session is not active.")

    # Read audio
    audio_bytes = await audio.read()
    if len(audio_bytes) < 1000:
        raise HTTPException(status_code=400, detail="Audio too short.")

    # Debug: record basic upload info (size, declared blob type, start delay)
    try:
        print(f"[voice.submit] file={audio.filename} size={len(audio_bytes)} blob_type={blob_type} start_delay={start_delay_seconds}")
    except Exception:
        pass

    # Transcribe
    try:
        transcript_data = transcribe_audio(audio_bytes, filename=audio.filename or "audio.webm")
    except Exception as e:
        # Log exception (includes temp_file path when available) so dev can fetch saved file
        try:
            print(f"[voice.submit] transcription exception: {e}")
        except Exception:
            pass
        message = str(e)
        if "could not process file" in message.lower() or "invalid media file" in message.lower():
            raise HTTPException(status_code=400, detail="Invalid audio file. Please re-record and try again.")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {message}")

    answer_text = transcript_data.get("text", "").strip()
    if not answer_text:
        raise HTTPException(status_code=400, detail="No speech detected. Please speak clearly and try again.")

    # Analyze confidence + cheating
    confidence = analyze_confidence(transcript_data, question)
    cheat = detect_cheating(
        transcript_data=transcript_data,
        confidence_data=confidence,
        response_time_seconds=response_time_seconds,
        start_delay_seconds=start_delay_seconds,
        question=question,
    )

    # Persist voice analysis on the exchange BEFORE submitting answer
    ex_result = await db.execute(
        select(VivaExchange).where(VivaExchange.id == exchange_id)
    )
    exchange = ex_result.scalar_one_or_none()
    if exchange:
        exchange.voice_transcript = answer_text
        exchange.confidence_score = confidence["confidence_score"]
        exchange.confidence_label = confidence["confidence_label"]
        exchange.confidence_data = confidence
        exchange.cheat_risk_score = cheat["risk_score"]
        exchange.cheat_risk_level = cheat["risk_level"]
        exchange.cheat_flags = cheat["flags"]
        exchange.speech_rate_wpm = confidence["speech_rate_wpm"]
        exchange.start_delay_seconds = max(0, start_delay_seconds)
        await db.flush()

    # Submit answer through existing viva engine
    result = await viva_engine.submit_answer(
        db=db,
        session_id=session_id,
        exchange_id=exchange_id,
        student_answer=answer_text,
        response_time_seconds=response_time_seconds,
    )

    # Attach voice analysis to the response
    result["voice_analysis"] = {
        "transcript": answer_text,
        "confidence": confidence,
        "cheat_detection": cheat,
    }

    return result


@router.get('/debug-files')
async def list_debug_files(current_user: User = Depends(get_current_student)):
    """List saved groq debug audio files for inspection."""
    debug_dir = Path(settings.UPLOAD_DIR) / 'groq_debug'
    if not debug_dir.exists():
        return {"files": []}
    files = []
    for p in sorted(debug_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.is_file():
            files.append({"name": p.name, "size": p.stat().st_size, "path": str(p)})
    return {"files": files}


@router.get('/debug-files/{filename}')
async def get_debug_file(filename: str, current_user: User = Depends(get_current_student)):
    debug_dir = Path(settings.UPLOAD_DIR) / 'groq_debug'
    file_path = debug_dir / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=str(file_path), filename=filename)

"""
Analytics Routes — per-student and faculty-level performance data.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.api.deps import get_current_user, get_current_faculty
from app.models.user import User, UserRole
from app.models.viva_session import VivaSession, VivaExchange, SessionStatus
from app.models.submission import Submission

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/me")
async def my_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Personal analytics dashboard for a student."""
    sessions_result = await db.execute(
        select(VivaSession)
        .where(VivaSession.student_id == current_user.id)
        .where(VivaSession.status == SessionStatus.completed)
        .order_by(VivaSession.completed_at.desc())
    )
    sessions = sessions_result.scalars().all()

    if not sessions:
        return {"message": "No completed sessions yet.", "data": {}}

    scores = [s.overall_score for s in sessions if s.overall_score is not None]
    avg_score = sum(scores) / len(scores) if scores else 0

    # Aggregate topic scores across all sessions
    topic_totals: dict[str, list[float]] = {}
    for s in sessions:
        if s.topic_scores:
            for topic, score in s.topic_scores.items():
                topic_totals.setdefault(topic, []).append(score)
    topic_averages = {t: round(sum(v) / len(v), 1) for t, v in topic_totals.items()}

    # Score trend (chronological)
    score_trend = [
        {
            "session_id": str(s.id),
            "score": s.overall_score,
            "date": s.completed_at.isoformat() if s.completed_at else None,
        }
        for s in reversed(sessions)
        if s.overall_score is not None
    ]

    return {
        "total_sessions": len(sessions),
        "average_score": round(avg_score, 1),
        "best_score": max(scores) if scores else 0,
        "latest_score": scores[0] if scores else 0,
        "topic_averages": topic_averages,
        "score_trend": score_trend,
        "recent_sessions": [
            {
                "id": str(s.id),
                "score": s.overall_score,
                "analytics": s.analytics,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            }
            for s in sessions[:5]
        ]
    }


@router.get("/session/{session_id}")
async def session_analytics(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detailed analytics for a single completed session."""
    session_result = await db.execute(
        select(VivaSession).where(VivaSession.id == session_id)
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Students can only see their own; faculty can see all
    if current_user.role == UserRole.student and str(session.student_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied.")

    exchanges_result = await db.execute(
        select(VivaExchange)
        .where(VivaExchange.session_id == session.id)
        .where(VivaExchange.student_answer.isnot(None))
        .order_by(VivaExchange.sequence_number)
    )
    exchanges = exchanges_result.scalars().all()

    # Per-question breakdown
    question_breakdown = [
        {
            "sequence": e.sequence_number,
            "topic": e.topic,
            "type": e.question_type,
            "difficulty": e.difficulty,
            "score": e.answer_score,
            "is_weak": bool(e.is_weak_answer),
            "response_time": e.response_time_seconds,
            "confidence_score": e.confidence_score,
            "confidence_label": e.confidence_label,
            "cheat_risk_score": e.cheat_risk_score,
            "cheat_risk_level": e.cheat_risk_level,
            "cheat_flags": e.cheat_flags or [],
            "speech_rate_wpm": e.speech_rate_wpm,
            "start_delay_seconds": e.start_delay_seconds,
            "voice_transcript": e.voice_transcript,
        }
        for e in exchanges
    ]

    # Aggregate voice tracking metrics
    voice_scores = [e.confidence_score for e in exchanges if e.confidence_score is not None]
    speech_rates = [e.speech_rate_wpm for e in exchanges if e.speech_rate_wpm is not None]
    cheat_risks = [e.cheat_risk_score for e in exchanges if e.cheat_risk_score is not None]
    suspicious_questions = [e for e in exchanges if (e.cheat_risk_score or 0) >= 60]

    delayed_start_times = [e.start_delay_seconds for e in exchanges if e.start_delay_seconds is not None]
    delayed_start_count = len([e for e in exchanges if e.start_delay_seconds and e.start_delay_seconds > 3])

    voice_summary = {
        "average_confidence_score": round(sum(voice_scores) / len(voice_scores), 1) if voice_scores else None,
        "average_speech_rate_wpm": round(sum(speech_rates) / len(speech_rates), 1) if speech_rates else None,
        "highest_cheat_risk_score": round(max(cheat_risks), 1) if cheat_risks else None,
        "suspicious_answer_count": len(suspicious_questions),
        "voice_answer_count": len([e for e in exchanges if e.voice_transcript]),
        "average_start_delay_seconds": round(sum(delayed_start_times) / len(delayed_start_times), 1) if delayed_start_times else None,
        "delayed_start_count": delayed_start_count,
    }

    # Score by question type
    type_scores: dict[str, list] = {}
    for e in exchanges:
        if e.answer_score is not None:
            type_scores.setdefault(e.question_type, []).append(e.answer_score)
    type_averages = {t: round(sum(v) / len(v), 1) for t, v in type_scores.items()}

    weak_questions = [e for e in exchanges if e.is_weak_answer]

    return {
        "session_id": session_id,
        "overall_score": session.overall_score,
        "performance_report": session.performance_report,
        "analytics": session.analytics,
        "question_breakdown": question_breakdown,
        "type_averages": type_averages,
        "weak_count": len(weak_questions),
        "total_answered": len(exchanges),
        "avg_response_time": (
            sum(e.response_time_seconds or 0 for e in exchanges) / len(exchanges)
            if exchanges else 0
        ),
        "weak_topics": list({e.topic for e in weak_questions if e.topic}),
        "voice_summary": voice_summary,
    }


@router.get("/faculty/overview")
async def faculty_overview(
    db: AsyncSession = Depends(get_db),
    current_faculty: User = Depends(get_current_faculty),
):
    """Faculty dashboard — overview of all students' performance."""
    # All completed sessions
    result = await db.execute(
        select(VivaSession, User)
        .join(User, VivaSession.student_id == User.id)
        .where(VivaSession.status == SessionStatus.completed)
        .order_by(VivaSession.completed_at.desc())
    )
    rows = result.all()

    students_data: dict[str, dict] = {}
    for session, user in rows:
        uid = str(user.id)
        if uid not in students_data:
            students_data[uid] = {
                "student_id": uid,
                "student_name": user.name,
                "student_email": user.email,
                "sessions": [],
                "avg_score": 0,
            }
        students_data[uid]["sessions"].append({
            "session_id": str(session.id),
            "score": session.overall_score,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        })

    # Compute averages
    for uid, data in students_data.items():
        scores = [s["score"] for s in data["sessions"] if s["score"] is not None]
        data["avg_score"] = round(sum(scores) / len(scores), 1) if scores else 0
        data["total_sessions"] = len(data["sessions"])

    all_scores = [
        s.overall_score for s, _ in rows if s.overall_score is not None
    ]

    return {
        "total_students": len(students_data),
        "total_sessions": len(rows),
        "class_avg_score": round(sum(all_scores) / len(all_scores), 1) if all_scores else 0,
        "students": list(students_data.values()),
    }

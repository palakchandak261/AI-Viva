from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.core.database import get_db
from app.api.deps import get_current_student
from app.models.user import User
from app.models.submission import Submission
from app.models.viva_session import VivaSession, VivaExchange, SessionStatus
from app.services.ai_service import generate_questions
from app.services.viva_engine import viva_engine

router = APIRouter(prefix="/viva", tags=["Viva Sessions"])


class StartSessionRequest(BaseModel):
    submission_id: str
    total_questions: int = 10
    difficulty_level: str = "medium"


class SubmitAnswerRequest(BaseModel):
    session_id: str
    exchange_id: str
    student_answer: str
    response_time_seconds: int = 0


@router.post("/start", status_code=201)
async def start_session(
    payload: StartSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_student),
):
    result = await db.execute(
        select(Submission).where(Submission.id == payload.submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission or str(submission.student_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail="Submission not found.")

    if not submission.extracted_content or not submission.knowledge_map:
        raise HTTPException(status_code=422, detail="Submission has not been processed yet.")

    session = VivaSession(
        student_id=str(current_user.id),
        submission_id=str(submission.id),
        status=SessionStatus.in_progress,
        total_questions=min(max(payload.total_questions, 3), 20),
        difficulty_level=payload.difficulty_level,
        started_at=datetime.now(timezone.utc),
    )
    db.add(session)
    await db.flush()

    questions = await generate_questions(
        project_content=submission.extracted_content.get("summary_text", ""),
        knowledge_map=submission.knowledge_map,
        count=session.total_questions,
        difficulty=payload.difficulty_level,
    )

    for i, q in enumerate(questions, start=1):
        exchange = VivaExchange(
            session_id=str(session.id),
            sequence_number=i,
            question=q["question"],
            question_type=q.get("type", "conceptual"),
            topic=q.get("topic", ""),
            difficulty=q.get("difficulty", "medium"),
        )
        db.add(exchange)
    await db.flush()

    first_result = await db.execute(
        select(VivaExchange)
        .where(VivaExchange.session_id == str(session.id))
        .order_by(VivaExchange.sequence_number)
        .limit(1)
    )
    first_exchange = first_result.scalar_one()

    return {
        "session_id": str(session.id),
        "total_questions": session.total_questions,
        "difficulty_level": session.difficulty_level,
        "project_title": submission.title,
        "first_exchange": {
            "id": str(first_exchange.id),
            "sequence_number": first_exchange.sequence_number,
            "question": first_exchange.question,
            "question_type": first_exchange.question_type,
            "topic": first_exchange.topic,
            "difficulty": first_exchange.difficulty,
        }
    }


@router.post("/answer")
async def submit_answer(
    payload: SubmitAnswerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_student),
):
    result = await db.execute(
        select(VivaSession).where(VivaSession.id == payload.session_id)
    )
    session = result.scalar_one_or_none()
    if not session or str(session.student_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail="Session not found.")

    if session.status != SessionStatus.in_progress:
        raise HTTPException(status_code=400, detail="Session is not active.")

    result = await viva_engine.submit_answer(
        db=db,
        session_id=payload.session_id,
        exchange_id=payload.exchange_id,
        student_answer=payload.student_answer,
        response_time_seconds=payload.response_time_seconds,
    )
    # Include text cheat data in response so frontend can display it
    from app.services.text_cheat_detector import detect_text_cheating
    result["text_cheat"] = detect_text_cheating(
        answer=payload.student_answer,
        question="",
        response_time_seconds=payload.response_time_seconds,
    )
    return result


@router.get("/")
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_student),
):
    result = await db.execute(
        select(VivaSession)
        .where(VivaSession.student_id == str(current_user.id))
        .order_by(VivaSession.created_at.desc())
    )
    sessions = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "submission_id": str(s.submission_id),
            "status": s.status.value,
            "overall_score": s.overall_score,
            "total_questions": s.total_questions,
            "difficulty_level": s.difficulty_level,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
        }
        for s in sessions
    ]


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_student),
):
    result = await db.execute(
        select(VivaSession).where(VivaSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session or str(session.student_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail="Session not found.")

    exchanges_result = await db.execute(
        select(VivaExchange)
        .where(VivaExchange.session_id == session_id)
        .order_by(VivaExchange.sequence_number)
    )
    exchanges = exchanges_result.scalars().all()

    return {
        "session_id": str(session.id),
        "status": session.status.value,
        "total_questions": session.total_questions,
        "difficulty_level": session.difficulty_level,
        "overall_score": session.overall_score,
        "analytics": session.analytics,
        "performance_report": session.performance_report,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "exchanges": [
            {
                "id": str(e.id),
                "sequence_number": e.sequence_number,
                "question": e.question,
                "question_type": e.question_type,
                "topic": e.topic,
                "difficulty": e.difficulty,
                "student_answer": e.student_answer,
                "answer_score": e.answer_score,
                "answer_feedback": e.answer_feedback,
                "is_weak_answer": e.is_weak_answer,
                "response_time_seconds": e.response_time_seconds,
            }
            for e in exchanges
        ]
    }

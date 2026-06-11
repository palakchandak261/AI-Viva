from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.viva_session import VivaSession, VivaExchange, SessionStatus
from app.models.submission import Submission
from app.services.ai_service import (
    evaluate_answer,
    generate_followup_question,
    generate_performance_report,
)
from app.services.text_cheat_detector import detect_text_cheating


class VivaEngine:

    async def submit_answer(
        self,
        db: AsyncSession,
        session_id: str,
        exchange_id: str,
        student_answer: str,
        response_time_seconds: int
    ) -> dict:
        # Fetch exchange
        ex_result = await db.execute(
            select(VivaExchange).where(VivaExchange.id == exchange_id)
        )
        exchange = ex_result.scalar_one_or_none()
        if not exchange or str(exchange.session_id) != str(session_id):
            raise ValueError("Exchange not found or session mismatch.")

        sess_result = await db.execute(
            select(VivaSession).where(VivaSession.id == session_id)
        )
        session = sess_result.scalar_one_or_none()
        if not session or session.status != SessionStatus.in_progress:
            raise ValueError("Session is not active.")

        sub_result = await db.execute(
            select(Submission).where(Submission.id == str(session.submission_id))
        )
        submission = sub_result.scalar_one_or_none()
        project_context = (
            submission.extracted_content.get("summary_text", "")
            if submission and submission.extracted_content else ""
        )

        # Evaluate answer via AI
        evaluation = await evaluate_answer(
            question=exchange.question,
            student_answer=student_answer,
            expected_keywords=[],
            project_context=project_context
        )

        # Persist evaluation + text cheat detection
        text_cheat = detect_text_cheating(
            answer=student_answer,
            question=exchange.question,
            response_time_seconds=response_time_seconds,
        )
        exchange.student_answer = student_answer
        exchange.answer_score = evaluation["score"]
        exchange.answer_feedback = evaluation["feedback"]
        exchange.is_weak_answer = 1 if evaluation["is_weak"] else 0
        # Only overwrite cheat fields if not already set by voice analysis
        if exchange.cheat_risk_score is None:
            exchange.cheat_risk_score = text_cheat["risk_score"]
            exchange.cheat_risk_level = text_cheat["risk_level"]
            exchange.cheat_flags = text_cheat["flags"]
        exchange.response_time_seconds = response_time_seconds
        exchange.answered_at = datetime.now(timezone.utc)
        await db.flush()

        # Count answered
        total_answered = await self._count_answered(db, session_id)

        if total_answered >= session.total_questions:
            return await self._complete_session(db, session, submission)

        # Weak answer → generate follow-up
        if evaluation["is_weak"] and total_answered < session.total_questions:
            # Get the highest existing sequence number to avoid collisions
            from sqlalchemy import func as sqlfunc
            max_seq_result = await db.execute(
                select(sqlfunc.max(VivaExchange.sequence_number))
                .where(VivaExchange.session_id == session_id)
            )
            max_seq = max_seq_result.scalar() or total_answered
            followup_data = await generate_followup_question(
                original_question=exchange.question,
                student_answer=student_answer,
                topic=exchange.topic or "project",
                project_context=project_context
            )
            next_exchange = await self._create_exchange(
                db=db,
                session=session,
                question_data=followup_data,
                sequence_number=max_seq + 1
            )
            return {
                "status": "continue",
                "is_followup": True,
                "evaluation": evaluation,
                "next_exchange": self._exchange_to_dict(next_exchange)
            }

        # Get next pre-generated unanswered question
        next_exchange = await self._get_next_unanswered(db, session_id)
        if next_exchange:
            return {
                "status": "continue",
                "is_followup": False,
                "evaluation": evaluation,
                "next_exchange": self._exchange_to_dict(next_exchange)
            }

        return await self._complete_session(db, session, submission)

    async def _complete_session(self, db, session, submission) -> dict:
        result = await db.execute(
            select(VivaExchange)
            .where(VivaExchange.session_id == str(session.id))
            .where(VivaExchange.student_answer.isnot(None))
            .order_by(VivaExchange.sequence_number)
        )
        exchanges = result.scalars().all()
        exchanges_data = [self._exchange_to_dict(e) for e in exchanges]

        knowledge_map = submission.knowledge_map or {} if submission else {}

        from app.models.user import User
        user_result = await db.execute(
            select(User).where(User.id == str(session.student_id))
        )
        student = user_result.scalar_one_or_none()

        report = await generate_performance_report(
            exchanges=exchanges_data,
            knowledge_map=knowledge_map,
            student_name=student.name if student else "Student"
        )

        session.status = SessionStatus.completed
        session.overall_score = report.get("overall_score", 0)
        session.topic_scores = report.get("topic_scores", {})
        session.performance_report = report.get("detailed_feedback", "")
        session.analytics = {
            "grade": report.get("overall_grade"),
            "strengths": report.get("strengths", []),
            "weaknesses": report.get("weaknesses", []),
            "recommendations": report.get("recommendations", []),
            "topic_scores": report.get("topic_scores", {}),
            "avg_score_per_question": (
                sum(e.get("answer_score") or 0 for e in exchanges_data) / len(exchanges_data)
                if exchanges_data else 0
            )
        }
        session.completed_at = datetime.now(timezone.utc)
        await db.flush()

        return {
            "status": "completed",
            "session_id": str(session.id),
            "report": report,
            "analytics": session.analytics
        }

    async def _count_answered(self, db: AsyncSession, session_id: str) -> int:
        result = await db.execute(
            select(func.count())
            .select_from(VivaExchange)
            .where(VivaExchange.session_id == session_id)
            .where(VivaExchange.student_answer.isnot(None))
        )
        return result.scalar() or 0

    async def _get_next_unanswered(self, db: AsyncSession, session_id: str) -> Optional[VivaExchange]:
        result = await db.execute(
            select(VivaExchange)
            .where(VivaExchange.session_id == session_id)
            .where(VivaExchange.student_answer.is_(None))
            .order_by(VivaExchange.sequence_number)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _create_exchange(self, db, session, question_data, sequence_number) -> VivaExchange:
        exchange = VivaExchange(
            session_id=str(session.id),
            sequence_number=sequence_number,
            question=question_data["question"],
            question_type=question_data.get("type", "probe"),
            topic=question_data.get("topic", ""),
            difficulty=question_data.get("difficulty", "medium"),
        )
        db.add(exchange)
        await db.flush()
        return exchange

    def _exchange_to_dict(self, exchange: VivaExchange) -> dict:
        return {
            "id": str(exchange.id),
            "sequence_number": exchange.sequence_number,
            "question": exchange.question,
            "question_type": exchange.question_type,
            "topic": exchange.topic,
            "difficulty": exchange.difficulty,
            "answer_score": exchange.answer_score,
            "answer_feedback": exchange.answer_feedback,
            "is_weak_answer": exchange.is_weak_answer,
            "student_answer": exchange.student_answer,
            "response_time_seconds": exchange.response_time_seconds,
        }


viva_engine = VivaEngine()

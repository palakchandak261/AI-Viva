from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Float, Integer, Enum as SAEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.core.database import Base


class SessionStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    abandoned = "abandoned"


class VivaSession(Base):
    __tablename__ = "viva_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    submission_id = Column(String(36), ForeignKey("submissions.id"), nullable=False)
    status = Column(SAEnum(SessionStatus), default=SessionStatus.pending, nullable=False)

    total_questions = Column(Integer, default=10)
    difficulty_level = Column(String(20), default="medium")

    overall_score = Column(Float, nullable=True)
    topic_scores = Column(JSON, nullable=True)
    performance_report = Column(Text, nullable=True)
    analytics = Column(JSON, nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    student = relationship("User", back_populates="viva_sessions")
    submission = relationship("Submission", back_populates="viva_sessions")
    exchanges = relationship(
        "VivaExchange", back_populates="session",
        cascade="all, delete-orphan",
        order_by="VivaExchange.sequence_number"
    )


class VivaExchange(Base):
    __tablename__ = "viva_exchanges"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("viva_sessions.id"), nullable=False)
    sequence_number = Column(Integer, nullable=False)

    question = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=False)
    topic = Column(String(100), nullable=True)
    difficulty = Column(String(20), default="medium")

    student_answer = Column(Text, nullable=True)
    answer_score = Column(Float, nullable=True)
    answer_feedback = Column(Text, nullable=True)
    is_weak_answer = Column(Integer, default=0)
    response_time_seconds = Column(Integer, nullable=True)

    # Voice analysis fields
    voice_transcript = Column(Text, nullable=True)       # raw whisper transcript
    confidence_score = Column(Float, nullable=True)      # 0-100
    confidence_label = Column(String(30), nullable=True) # "Confident", "Nervous" etc
    confidence_data = Column(JSON, nullable=True)        # full breakdown
    cheat_risk_score = Column(Float, nullable=True)      # 0-100
    cheat_risk_level = Column(String(20), nullable=True) # "Clean", "Medium Risk" etc
    cheat_flags = Column(JSON, nullable=True)            # list of flag objects
    speech_rate_wpm = Column(Float, nullable=True)
    start_delay_seconds = Column(Integer, nullable=True) # seconds waited after prep before recording

    asked_at = Column(DateTime(timezone=True), server_default=func.now())
    answered_at = Column(DateTime(timezone=True), nullable=True)

    session = relationship("VivaSession", back_populates="exchanges")

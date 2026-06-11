from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Uploaded file paths
    report_path = Column(String(500), nullable=True)
    ppt_path = Column(String(500), nullable=True)
    code_zip_path = Column(String(500), nullable=True)

    # Extracted content (stored as JSON)
    extracted_content = Column(JSON, nullable=True)
    knowledge_map = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    student = relationship("User", back_populates="submissions")
    viva_sessions = relationship("VivaSession", back_populates="submission", cascade="all, delete-orphan")

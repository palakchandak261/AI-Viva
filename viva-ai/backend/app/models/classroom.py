"""
Database models for classroom management system.
Includes Classroom, ClassroomTest, TestResult, and StudentEnrollment models.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import enum
import uuid

Base = declarative_base()


class DifficultyLevel(str, enum.Enum):
    """Difficulty level of the exam."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class TestStatus(str, enum.Enum):
    """Status of the test."""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class StudentEnrollment(Base):
    """Student enrollment in a classroom."""
    __tablename__ = "student_enrollments"

    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    
    classroom_id = Column(Integer, ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    enrolled_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    classroom = relationship("Classroom", back_populates="student_enrollments")
    student = relationship("User", foreign_keys=[student_id], back_populates="classroom_enrollments")
    test_results = relationship("TestResult", back_populates="student_enrollment", cascade="all, delete-orphan")


class Classroom(Base):
    """Classroom model for grouping students and tests."""
    __tablename__ = "classrooms"

    id = Column(Integer, primary_key=True, index=True)
    classroom_code = Column(String, unique=True, index=True, nullable=False)
    
    faculty_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Statistics (cached/denormalized for performance)
    total_students = Column(Integer, default=0)
    total_tests = Column(Integer, default=0)
    
    # Relationships
    faculty = relationship("User", foreign_keys=[faculty_id], back_populates="created_classrooms")
    student_enrollments = relationship("StudentEnrollment", back_populates="classroom", cascade="all, delete-orphan")
    tests = relationship("ClassroomTest", back_populates="classroom", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Classroom {self.classroom_code}: {self.name}>"


class ClassroomTest(Base):
    """Test/Exam model within a classroom."""
    __tablename__ = "classroom_tests"

    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    
    classroom_id = Column(Integer, ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Test details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    difficulty_level = Column(SQLEnum(DifficultyLevel), default=DifficultyLevel.MEDIUM)
    
    # Test configuration
    total_marks = Column(Integer, nullable=False)  # e.g., 100
    pass_marks = Column(Integer, nullable=True)    # e.g., 40 (optional)
    duration_minutes = Column(Integer, nullable=False)  # e.g., 90 minutes
    
    # Timing
    scheduled_date = Column(DateTime, nullable=False)  # When test starts
    scheduled_end_time = Column(DateTime, nullable=False)  # When test ends
    
    # Status
    status = Column(SQLEnum(TestStatus), default=TestStatus.DRAFT)
    is_published = Column(Boolean, default=False)
    allow_late_submission = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Statistics
    total_students_enrolled = Column(Integer, default=0)
    total_students_attempted = Column(Integer, default=0)
    average_score = Column(Float, default=0.0)
    
    # Relationships
    classroom = relationship("Classroom", back_populates="tests")
    created_by_user = relationship("User", foreign_keys=[created_by])
    test_results = relationship("TestResult", back_populates="test", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ClassroomTest {self.test_id}: {self.title}>"


class TestResult(Base):
    """Student's test result/performance record."""
    __tablename__ = "test_results"

    id = Column(Integer, primary_key=True, index=True)
    result_id = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    
    test_id = Column(Integer, ForeignKey("classroom_tests.id", ondelete="CASCADE"), nullable=False)
    student_enrollment_id = Column(Integer, ForeignKey("student_enrollments.id", ondelete="CASCADE"), nullable=False)
    
    # Performance data
    obtained_marks = Column(Float, default=0.0)
    percentage = Column(Float, default=0.0)  # percentage score
    is_passed = Column(Boolean, default=False)
    
    # Timing
    started_at = Column(DateTime, nullable=True)  # When student started
    submitted_at = Column(DateTime, nullable=True)  # When student submitted
    duration_taken = Column(Integer, default=0)  # seconds taken
    
    # Additional data
    attempt_number = Column(Integer, default=1)  # For retakes
    ai_viva_session_id = Column(String, nullable=True)  # Link to viva session
    notes = Column(Text, nullable=True)  # Faculty notes
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    test = relationship("ClassroomTest", back_populates="test_results")
    student_enrollment = relationship("StudentEnrollment", back_populates="test_results")

    def __repr__(self):
        return f"<TestResult {self.result_id}: {self.obtained_marks}/{self.test.total_marks}>"

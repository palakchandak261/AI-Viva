"""
Pydantic schemas for classroom management system.
Used for request validation and response serialization.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class TestStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


# ═══════════════════════════════════════════════════════════════════════════════
# Classroom Schemas
# ═══════════════════════════════════════════════════════════════════════════════

class ClassroomCreateRequest(BaseModel):
    """Request to create a new classroom."""
    name: str = Field(..., min_length=3, max_length=255, description="Classroom name")
    description: Optional[str] = Field(None, max_length=1000, description="Classroom description")

    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Classroom name cannot be empty')
        return v.strip()


class ClassroomUpdateRequest(BaseModel):
    """Request to update an existing classroom."""
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None


class ClassroomResponse(BaseModel):
    """Response schema for a classroom."""
    id: int
    classroom_code: str
    faculty_id: int
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    is_active: bool
    total_students: int
    total_tests: int

    class Config:
        from_attributes = True


class ClassroomDetailResponse(ClassroomResponse):
    """Detailed classroom response with enrollment and test data."""
    student_enrollments: List['StudentEnrollmentResponse'] = []
    tests: List['ClassroomTestResponse'] = []


class ClassroomJoinRequest(BaseModel):
    """Request to join a classroom using code."""
    classroom_code: str = Field(..., min_length=1, description="Classroom code")


# ═══════════════════════════════════════════════════════════════════════════════
# Student Enrollment Schemas
# ═══════════════════════════════════════════════════════════════════════════════

class StudentEnrollmentResponse(BaseModel):
    """Response schema for student enrollment."""
    id: int
    enrollment_id: str
    classroom_id: int
    student_id: int
    enrolled_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class StudentEnrollmentDetailResponse(StudentEnrollmentResponse):
    """Detailed enrollment response with student data."""
    student: Optional[dict] = None  # Will include user info
    test_results: List['TestResultResponse'] = []


# ═══════════════════════════════════════════════════════════════════════════════
# Test Schemas
# ═══════════════════════════════════════════════════════════════════════════════

class ClassroomTestCreateRequest(BaseModel):
    """Request to create a new test."""
    title: str = Field(..., min_length=3, max_length=255, description="Test title")
    description: Optional[str] = Field(None, max_length=2000)
    difficulty_level: DifficultyLevel = Field(DifficultyLevel.MEDIUM)
    total_marks: int = Field(..., gt=0, description="Total marks for the test")
    pass_marks: Optional[int] = Field(None, ge=0, description="Passing marks")
    duration_minutes: int = Field(..., gt=0, description="Test duration in minutes")
    scheduled_date: datetime = Field(..., description="Test start date and time")
    scheduled_end_time: datetime = Field(..., description="Test end date and time")
    allow_late_submission: bool = Field(False, description="Allow submission after deadline")

    @validator('scheduled_end_time')
    def end_time_after_start(cls, v, values):
        if 'scheduled_date' in values and v <= values['scheduled_date']:
            raise ValueError('End time must be after start time')
        return v

    @validator('pass_marks')
    def pass_marks_validation(cls, v, values):
        if v is not None and 'total_marks' in values and v > values['total_marks']:
            raise ValueError('Pass marks cannot exceed total marks')
        return v


class ClassroomTestUpdateRequest(BaseModel):
    """Request to update an existing test."""
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    difficulty_level: Optional[DifficultyLevel] = None
    total_marks: Optional[int] = Field(None, gt=0)
    pass_marks: Optional[int] = Field(None, ge=0)
    duration_minutes: Optional[int] = Field(None, gt=0)
    scheduled_date: Optional[datetime] = None
    scheduled_end_time: Optional[datetime] = None
    allow_late_submission: Optional[bool] = None
    status: Optional[TestStatus] = None


class ClassroomTestResponse(BaseModel):
    """Response schema for a test."""
    id: int
    test_id: str
    classroom_id: int
    title: str
    description: Optional[str]
    difficulty_level: str
    total_marks: int
    pass_marks: Optional[int]
    duration_minutes: int
    scheduled_date: datetime
    scheduled_end_time: datetime
    status: str
    is_published: bool
    allow_late_submission: bool
    created_at: datetime
    updated_at: datetime
    total_students_enrolled: int
    total_students_attempted: int
    average_score: float

    class Config:
        from_attributes = True


class ClassroomTestDetailResponse(ClassroomTestResponse):
    """Detailed test response with results."""
    test_results: List['TestResultResponse'] = []


class ClassroomTestPublishRequest(BaseModel):
    """Request to publish a test."""
    is_published: bool = Field(..., description="Publish or unpublish the test")


# ═══════════════════════════════════════════════════════════════════════════════
# Test Result Schemas
# ═══════════════════════════════════════════════════════════════════════════════

class TestResultCreateRequest(BaseModel):
    """Request to create/submit a test result."""
    test_id: int = Field(..., description="Test ID")
    obtained_marks: float = Field(..., ge=0, description="Marks obtained by student")
    ai_viva_session_id: Optional[str] = Field(None, description="Link to viva session")
    notes: Optional[str] = Field(None, max_length=2000)


class TestResultUpdateRequest(BaseModel):
    """Request to update test result (faculty only)."""
    obtained_marks: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None


class TestResultResponse(BaseModel):
    """Response schema for test result."""
    id: int
    result_id: str
    test_id: int
    student_enrollment_id: int
    obtained_marks: float
    percentage: float
    is_passed: bool
    started_at: Optional[datetime]
    submitted_at: Optional[datetime]
    duration_taken: int
    attempt_number: int
    ai_viva_session_id: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TestResultDetailResponse(TestResultResponse):
    """Detailed test result with student and test info."""
    student_enrollment: Optional[StudentEnrollmentResponse] = None
    test: Optional[ClassroomTestResponse] = None


# ═══════════════════════════════════════════════════════════════════════════════
# Analytics & Statistics Schemas
# ═══════════════════════════════════════════════════════════════════════════════

class ClassroomAnalyticsResponse(BaseModel):
    """Classroom-level analytics."""
    classroom_id: int
    classroom_code: str
    classroom_name: str
    total_students: int
    total_tests: int
    completed_tests: int
    average_class_score: float
    highest_score: float
    lowest_score: float
    pass_rate: float  # percentage of students who passed
    
    class Config:
        from_attributes = True


class TestAnalyticsResponse(BaseModel):
    """Test-level analytics."""
    test_id: str
    test_title: str
    total_students_attempted: int
    total_students_enrolled: int
    average_score: float
    highest_score: float
    lowest_score: float
    median_score: float
    pass_rate: float
    fail_rate: float


class StudentClassroomAnalyticsResponse(BaseModel):
    """Student performance in a classroom."""
    student_id: int
    classroom_id: int
    total_tests_attempted: int
    total_tests_passed: int
    overall_average_score: float
    highest_score: float
    lowest_score: float
    pass_rate: float


# ═══════════════════════════════════════════════════════════════════════════════
# Update model references at the end
# ═══════════════════════════════════════════════════════════════════════════════

ClassroomDetailResponse.model_rebuild()
StudentEnrollmentDetailResponse.model_rebuild()
ClassroomTestDetailResponse.model_rebuild()
TestResultDetailResponse.model_rebuild()

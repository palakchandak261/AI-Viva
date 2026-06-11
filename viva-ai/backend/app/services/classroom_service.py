"""
Classroom management service layer.
Handles business logic for classrooms, tests, enrollments, and results.
"""
import secrets
import string
from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.models.classroom import (
    Classroom, ClassroomTest, StudentEnrollment, TestResult,
    DifficultyLevel, TestStatus
)
from app.models.user import User
from app.schemas.classroom import (
    ClassroomCreateRequest, ClassroomUpdateRequest, ClassroomResponse,
    ClassroomTestCreateRequest, ClassroomTestUpdateRequest,
    TestResultCreateRequest, TestResultUpdateRequest,
    ClassroomAnalyticsResponse, TestAnalyticsResponse,
    StudentClassroomAnalyticsResponse
)


class ClassroomService:
    """Service for classroom operations."""

    @staticmethod
    def generate_classroom_code(length: int = 6) -> str:
        """Generate a unique classroom code."""
        characters = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(characters) for _ in range(length))

    @staticmethod
    async def create_classroom(
        db: AsyncSession,
        faculty_id: int,
        request: ClassroomCreateRequest
    ) -> Classroom:
        """Create a new classroom."""
        # Generate unique code
        while True:
            code = ClassroomService.generate_classroom_code()
            existing = await db.execute(
                select(Classroom).where(Classroom.classroom_code == code)
            )
            if not existing.scalar_one_or_none():
                break

        classroom = Classroom(
            classroom_code=code,
            faculty_id=faculty_id,
            name=request.name,
            description=request.description,
            is_active=True
        )
        db.add(classroom)
        await db.flush()
        await db.commit()
        await db.refresh(classroom)
        return classroom

    @staticmethod
    async def get_classroom_by_id(db: AsyncSession, classroom_id: int) -> Optional[Classroom]:
        """Fetch classroom by ID with relationships."""
        result = await db.execute(
            select(Classroom)
            .where(Classroom.id == classroom_id)
            .options(
                selectinload(Classroom.student_enrollments),
                selectinload(Classroom.tests)
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_classroom_by_code(db: AsyncSession, code: str) -> Optional[Classroom]:
        """Fetch classroom by code."""
        result = await db.execute(
            select(Classroom).where(Classroom.classroom_code == code)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_faculty_classrooms(db: AsyncSession, faculty_id: int) -> List[Classroom]:
        """Get all classrooms created by a faculty."""
        result = await db.execute(
            select(Classroom)
            .where(Classroom.faculty_id == faculty_id)
            .options(
                selectinload(Classroom.student_enrollments),
                selectinload(Classroom.tests)
            )
            .order_by(Classroom.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_student_classrooms(db: AsyncSession, student_id: int) -> List[Classroom]:
        """Get all classrooms a student is enrolled in."""
        result = await db.execute(
            select(Classroom)
            .join(StudentEnrollment)
            .where(
                and_(
                    StudentEnrollment.student_id == student_id,
                    StudentEnrollment.is_active == True
                )
            )
            .options(
                selectinload(Classroom.student_enrollments),
                selectinload(Classroom.tests)
            )
            .order_by(Classroom.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def update_classroom(
        db: AsyncSession,
        classroom_id: int,
        request: ClassroomUpdateRequest
    ) -> Optional[Classroom]:
        """Update classroom details."""
        classroom = await ClassroomService.get_classroom_by_id(db, classroom_id)
        if not classroom:
            return None

        if request.name is not None:
            classroom.name = request.name
        if request.description is not None:
            classroom.description = request.description
        if request.is_active is not None:
            classroom.is_active = request.is_active

        classroom.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(classroom)
        return classroom

    @staticmethod
    async def delete_classroom(db: AsyncSession, classroom_id: int) -> bool:
        """Delete a classroom and all related data."""
        classroom = await ClassroomService.get_classroom_by_id(db, classroom_id)
        if not classroom:
            return False

        await db.delete(classroom)
        await db.commit()
        return True


class EnrollmentService:
    """Service for student enrollment operations."""

    @staticmethod
    async def enroll_student(
        db: AsyncSession,
        classroom_id: int,
        student_id: int
    ) -> Tuple[StudentEnrollment, bool]:
        """
        Enroll a student in a classroom.
        Returns (enrollment, is_new) tuple.
        """
        # Check if already enrolled
        existing = await db.execute(
            select(StudentEnrollment).where(
                and_(
                    StudentEnrollment.classroom_id == classroom_id,
                    StudentEnrollment.student_id == student_id
                )
            )
        )
        enrollment = existing.scalar_one_or_none()

        if enrollment:
            # Reactivate if inactive
            if not enrollment.is_active:
                enrollment.is_active = True
                await db.commit()
                await db.refresh(enrollment)
            return enrollment, False

        # Create new enrollment
        enrollment = StudentEnrollment(
            classroom_id=classroom_id,
            student_id=student_id,
            is_active=True
        )
        db.add(enrollment)

        # Update classroom student count
        classroom = await ClassroomService.get_classroom_by_id(db, classroom_id)
        if classroom:
            classroom.total_students += 1
            classroom.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(enrollment)
        return enrollment, True

    @staticmethod
    async def get_student_enrollment(
        db: AsyncSession,
        classroom_id: int,
        student_id: int
    ) -> Optional[StudentEnrollment]:
        """Get student enrollment in a specific classroom."""
        result = await db.execute(
            select(StudentEnrollment).where(
                and_(
                    StudentEnrollment.classroom_id == classroom_id,
                    StudentEnrollment.student_id == student_id
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_classroom_students(
        db: AsyncSession,
        classroom_id: int,
        active_only: bool = True
    ) -> List[StudentEnrollment]:
        """Get all students in a classroom."""
        query = select(StudentEnrollment).where(
            StudentEnrollment.classroom_id == classroom_id
        )
        if active_only:
            query = query.where(StudentEnrollment.is_active == True)

        result = await db.execute(query.order_by(StudentEnrollment.enrolled_at.desc()))
        return result.scalars().all()

    @staticmethod
    async def remove_student(
        db: AsyncSession,
        classroom_id: int,
        student_id: int
    ) -> bool:
        """Remove student from classroom."""
        enrollment = await EnrollmentService.get_student_enrollment(
            db, classroom_id, student_id
        )
        if not enrollment:
            return False

        enrollment.is_active = False
        await db.commit()

        # Update classroom student count
        classroom = await ClassroomService.get_classroom_by_id(db, classroom_id)
        if classroom:
            classroom.total_students = max(0, classroom.total_students - 1)
            classroom.updated_at = datetime.utcnow()
            await db.commit()

        return True


class TestService:
    """Service for test/exam operations."""

    @staticmethod
    async def create_test(
        db: AsyncSession,
        classroom_id: int,
        faculty_id: int,
        request: ClassroomTestCreateRequest
    ) -> ClassroomTest:
        """Create a new test in a classroom."""
        test = ClassroomTest(
            classroom_id=classroom_id,
            created_by=faculty_id,
            title=request.title,
            description=request.description,
            difficulty_level=request.difficulty_level,
            total_marks=request.total_marks,
            pass_marks=request.pass_marks,
            duration_minutes=request.duration_minutes,
            scheduled_date=request.scheduled_date,
            scheduled_end_time=request.scheduled_end_time,
            allow_late_submission=request.allow_late_submission,
            status=TestStatus.DRAFT
        )
        db.add(test)

        # Update classroom test count
        classroom = await ClassroomService.get_classroom_by_id(db, classroom_id)
        if classroom:
            classroom.total_tests += 1
            classroom.updated_at = datetime.utcnow()

        await db.flush()
        await db.commit()
        await db.refresh(test)
        return test

    @staticmethod
    async def get_test_by_id(db: AsyncSession, test_id: int) -> Optional[ClassroomTest]:
        """Fetch test by ID."""
        result = await db.execute(
            select(ClassroomTest)
            .where(ClassroomTest.id == test_id)
            .options(selectinload(ClassroomTest.test_results))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_classroom_tests(
        db: AsyncSession,
        classroom_id: int,
        status: Optional[TestStatus] = None
    ) -> List[ClassroomTest]:
        """Get all tests in a classroom."""
        query = select(ClassroomTest).where(ClassroomTest.classroom_id == classroom_id)
        if status:
            query = query.where(ClassroomTest.status == status)

        result = await db.execute(
            query.options(selectinload(ClassroomTest.test_results))
            .order_by(ClassroomTest.scheduled_date.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def update_test(
        db: AsyncSession,
        test_id: int,
        request: ClassroomTestUpdateRequest
    ) -> Optional[ClassroomTest]:
        """Update test details."""
        test = await TestService.get_test_by_id(db, test_id)
        if not test:
            return None

        if request.title is not None:
            test.title = request.title
        if request.description is not None:
            test.description = request.description
        if request.difficulty_level is not None:
            test.difficulty_level = request.difficulty_level
        if request.total_marks is not None:
            test.total_marks = request.total_marks
        if request.pass_marks is not None:
            test.pass_marks = request.pass_marks
        if request.duration_minutes is not None:
            test.duration_minutes = request.duration_minutes
        if request.scheduled_date is not None:
            test.scheduled_date = request.scheduled_date
        if request.scheduled_end_time is not None:
            test.scheduled_end_time = request.scheduled_end_time
        if request.allow_late_submission is not None:
            test.allow_late_submission = request.allow_late_submission
        if request.status is not None:
            test.status = request.status

        test.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(test)
        return test

    @staticmethod
    async def publish_test(db: AsyncSession, test_id: int, is_published: bool) -> Optional[ClassroomTest]:
        """Publish/unpublish a test."""
        test = await TestService.get_test_by_id(db, test_id)
        if not test:
            return None

        test.is_published = is_published
        if is_published:
            test.status = TestStatus.ACTIVE
        test.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(test)
        return test

    @staticmethod
    async def delete_test(db: AsyncSession, test_id: int) -> bool:
        """Delete a test."""
        test = await TestService.get_test_by_id(db, test_id)
        if not test:
            return False

        classroom = await ClassroomService.get_classroom_by_id(db, test.classroom_id)
        if classroom:
            classroom.total_tests = max(0, classroom.total_tests - 1)
            classroom.updated_at = datetime.utcnow()

        await db.delete(test)
        await db.commit()
        return True


class ResultService:
    """Service for test result operations."""

    @staticmethod
    async def create_result(
        db: AsyncSession,
        student_enrollment_id: int,
        test_id: int,
        request: TestResultCreateRequest
    ) -> TestResult:
        """Create/submit a test result."""
        test = await TestService.get_test_by_id(db, test_id)
        if not test:
            raise ValueError("Test not found")

        # Calculate percentage and pass status
        percentage = (request.obtained_marks / test.total_marks * 100) if test.total_marks > 0 else 0
        is_passed = (
            test.pass_marks is not None and request.obtained_marks >= test.pass_marks
        ) if test.pass_marks else False

        result = TestResult(
            test_id=test_id,
            student_enrollment_id=student_enrollment_id,
            obtained_marks=request.obtained_marks,
            percentage=percentage,
            is_passed=is_passed,
            started_at=datetime.utcnow(),
            submitted_at=datetime.utcnow(),
            ai_viva_session_id=request.ai_viva_session_id,
            notes=request.notes,
            attempt_number=1
        )
        db.add(result)

        # Update test statistics
        await TestService._update_test_statistics(db, test_id)

        await db.commit()
        await db.refresh(result)
        return result

    @staticmethod
    async def get_result_by_id(db: AsyncSession, result_id: int) -> Optional[TestResult]:
        """Fetch result by ID."""
        result = await db.execute(
            select(TestResult)
            .where(TestResult.id == result_id)
            .options(
                selectinload(TestResult.test),
                selectinload(TestResult.student_enrollment)
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_student_test_result(
        db: AsyncSession,
        student_enrollment_id: int,
        test_id: int
    ) -> Optional[TestResult]:
        """Get a student's result for a specific test."""
        result = await db.execute(
            select(TestResult).where(
                and_(
                    TestResult.student_enrollment_id == student_enrollment_id,
                    TestResult.test_id == test_id
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_test_results(db: AsyncSession, test_id: int) -> List[TestResult]:
        """Get all results for a test."""
        result = await db.execute(
            select(TestResult)
            .where(TestResult.test_id == test_id)
            .options(selectinload(TestResult.student_enrollment))
            .order_by(TestResult.submitted_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_student_results(
        db: AsyncSession,
        student_enrollment_id: int
    ) -> List[TestResult]:
        """Get all results for a student in a classroom."""
        result = await db.execute(
            select(TestResult)
            .where(TestResult.student_enrollment_id == student_enrollment_id)
            .options(selectinload(TestResult.test))
            .order_by(TestResult.submitted_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def update_result(
        db: AsyncSession,
        result_id: int,
        request: TestResultUpdateRequest
    ) -> Optional[TestResult]:
        """Update a test result (faculty only)."""
        result = await ResultService.get_result_by_id(db, result_id)
        if not result:
            return None

        if request.obtained_marks is not None:
            result.obtained_marks = request.obtained_marks
            # Recalculate percentage
            test = result.test
            result.percentage = (request.obtained_marks / test.total_marks * 100) if test.total_marks > 0 else 0
            result.is_passed = (
                test.pass_marks is not None and request.obtained_marks >= test.pass_marks
            ) if test.pass_marks else False

        if request.notes is not None:
            result.notes = request.notes

        result.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(result)

        # Update test statistics
        await TestService._update_test_statistics(db, result.test_id)

        return result

    @staticmethod
    async def _update_test_statistics(db: AsyncSession, test_id: int) -> None:
        """Update test statistics (average, pass rate, etc.)."""
        test = await TestService.get_test_by_id(db, test_id)
        if not test:
            return

        results = await ResultService.get_test_results(db, test_id)

        if results:
            test.total_students_attempted = len(results)
            test.average_score = sum(r.obtained_marks for r in results) / len(results)
        else:
            test.total_students_attempted = 0
            test.average_score = 0.0

        test.updated_at = datetime.utcnow()
        await db.commit()


class AnalyticsService:
    """Service for analytics and reporting."""

    @staticmethod
    async def get_classroom_analytics(
        db: AsyncSession,
        classroom_id: int
    ) -> Optional[dict]:
        """Get comprehensive classroom analytics."""
        classroom = await ClassroomService.get_classroom_by_id(db, classroom_id)
        if not classroom:
            return None

        results = await db.execute(
            select(TestResult)
            .join(StudentEnrollment)
            .where(StudentEnrollment.classroom_id == classroom_id)
        )
        all_results = results.scalars().all()

        if not all_results:
            return {
                "classroom_id": classroom_id,
                "total_students": classroom.total_students,
                "total_tests": classroom.total_tests,
                "average_class_score": 0.0,
                "pass_rate": 0.0,
                "highest_score": 0.0,
                "lowest_score": 0.0
            }

        marks = [r.obtained_marks for r in all_results]
        passed = len([r for r in all_results if r.is_passed])

        return {
            "classroom_id": classroom_id,
            "total_students": classroom.total_students,
            "total_tests": classroom.total_tests,
            "average_class_score": sum(marks) / len(marks) if marks else 0.0,
            "pass_rate": (passed / len(all_results) * 100) if all_results else 0.0,
            "highest_score": max(marks) if marks else 0.0,
            "lowest_score": min(marks) if marks else 0.0
        }

    @staticmethod
    async def get_test_analytics(db: AsyncSession, test_id: int) -> Optional[dict]:
        """Get test-level analytics."""
        test = await TestService.get_test_by_id(db, test_id)
        if not test:
            return None

        results = test.test_results
        if not results:
            return {
                "test_id": test.test_id,
                "total_students_attempted": 0,
                "average_score": 0.0,
                "pass_rate": 0.0
            }

        marks = [r.obtained_marks for r in results]
        passed = len([r for r in results if r.is_passed])

        return {
            "test_id": test.test_id,
            "total_students_attempted": len(results),
            "average_score": sum(marks) / len(marks),
            "highest_score": max(marks),
            "lowest_score": min(marks),
            "pass_rate": (passed / len(results) * 100),
            "fail_rate": ((len(results) - passed) / len(results) * 100)
        }

    @staticmethod
    async def get_student_classroom_analytics(
        db: AsyncSession,
        student_enrollment_id: int
    ) -> Optional[dict]:
        """Get student performance in a classroom."""
        enrollment = await db.execute(
            select(StudentEnrollment).where(
                StudentEnrollment.id == student_enrollment_id
            )
        )
        enrollment_obj = enrollment.scalar_one_or_none()
        if not enrollment_obj:
            return None

        results = await ResultService.get_student_results(db, student_enrollment_id)

        if not results:
            return {
                "student_id": enrollment_obj.student_id,
                "total_tests_attempted": 0,
                "overall_average_score": 0.0,
                "pass_rate": 0.0
            }

        marks = [r.obtained_marks for r in results]
        passed = len([r for r in results if r.is_passed])

        return {
            "student_id": enrollment_obj.student_id,
            "total_tests_attempted": len(results),
            "overall_average_score": sum(marks) / len(marks),
            "highest_score": max(marks),
            "lowest_score": min(marks),
            "pass_rate": (passed / len(results) * 100) if results else 0.0
        }

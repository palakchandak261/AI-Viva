"""
API routes for classroom management.
Endpoints for creating classrooms, managing tests, enrollments, and results.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.classroom_service import (
    ClassroomService, EnrollmentService, TestService, ResultService, AnalyticsService
)
from app.schemas.classroom import (
    ClassroomCreateRequest, ClassroomUpdateRequest, ClassroomResponse, ClassroomDetailResponse,
    ClassroomJoinRequest,
    ClassroomTestCreateRequest, ClassroomTestUpdateRequest, ClassroomTestResponse,
    ClassroomTestPublishRequest,
    TestResultCreateRequest, TestResultUpdateRequest, TestResultResponse,
    ClassroomAnalyticsResponse, TestAnalyticsResponse, StudentClassroomAnalyticsResponse
)

router = APIRouter(prefix="/classrooms", tags=["Classrooms"])


# ═══════════════════════════════════════════════════════════════════════════════
# CLASSROOM ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("", response_model=ClassroomResponse, status_code=status.HTTP_201_CREATED)
async def create_classroom(
    request: ClassroomCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new classroom (faculty only)."""
    if current_user.role != "faculty":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only faculty can create classrooms"
        )

    try:
        classroom = await ClassroomService.create_classroom(db, current_user.id, request)
        return ClassroomResponse.model_validate(classroom)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating classroom: {str(e)}"
        )


@router.get("/{classroom_id}", response_model=ClassroomDetailResponse)
async def get_classroom(
    classroom_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get classroom details with students and tests."""
    classroom = await ClassroomService.get_classroom_by_id(db, classroom_id)

    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found"
        )

    # Check authorization (faculty owner or enrolled student)
    is_owner = classroom.faculty_id == current_user.id
    is_enrolled = any(
        e.student_id == current_user.id and e.is_active
        for e in classroom.student_enrollments
    )

    if not (is_owner or is_enrolled):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this classroom"
        )

    return ClassroomDetailResponse.model_validate(classroom)


@router.get("", response_model=List[ClassroomResponse])
async def list_my_classrooms(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List classrooms based on user role."""
    if current_user.role == "faculty":
        classrooms = await ClassroomService.get_faculty_classrooms(db, current_user.id)
    else:
        classrooms = await ClassroomService.get_student_classrooms(db, current_user.id)

    return [ClassroomResponse.model_validate(c) for c in classrooms]


@router.put("/{classroom_id}", response_model=ClassroomResponse)
async def update_classroom(
    classroom_id: int,
    request: ClassroomUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update classroom details (faculty owner only)."""
    classroom = await ClassroomService.get_classroom_by_id(db, classroom_id)

    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found"
        )

    if classroom.faculty_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only classroom owner can update"
        )

    try:
        updated = await ClassroomService.update_classroom(db, classroom_id, request)
        return ClassroomResponse.model_validate(updated)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating classroom: {str(e)}"
        )


@router.delete("/{classroom_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_classroom(
    classroom_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a classroom (faculty owner only)."""
    classroom = await ClassroomService.get_classroom_by_id(db, classroom_id)

    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found"
        )

    if classroom.faculty_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only classroom owner can delete"
        )

    success = await ClassroomService.delete_classroom(db, classroom_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting classroom"
        )


@router.post("/join", response_model=ClassroomResponse)
async def join_classroom_with_code(
    request: ClassroomJoinRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Join a classroom using classroom code (students only)."""
    if current_user.role == "faculty":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faculty cannot join classrooms as students"
        )

    classroom = await ClassroomService.get_classroom_by_code(db, request.classroom_code)

    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found. Check the code and try again."
        )

    if not classroom.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This classroom is inactive"
        )

    try:
        enrollment, is_new = await EnrollmentService.enroll_student(
            db, classroom.id, current_user.id
        )
        message = "Successfully joined classroom" if is_new else "Already enrolled in this classroom"
        return ClassroomResponse.model_validate(classroom)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error joining classroom: {str(e)}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# STUDENT MANAGEMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/{classroom_id}/students", response_model=List[dict])
async def list_classroom_students(
    classroom_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all students in a classroom (faculty owner only)."""
    classroom = await ClassroomService.get_classroom_by_id(db, classroom_id)

    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found"
        )

    if classroom.faculty_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only classroom owner can view student list"
        )

    students = await EnrollmentService.get_classroom_students(db, classroom_id)
    return [
        {
            "id": s.id,
            "enrollment_id": s.enrollment_id,
            "student_id": s.student_id,
            "enrolled_at": s.enrolled_at,
            "is_active": s.is_active
        }
        for s in students
    ]


@router.delete("/{classroom_id}/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_student_from_classroom(
    classroom_id: int,
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a student from classroom (faculty owner only)."""
    classroom = await ClassroomService.get_classroom_by_id(db, classroom_id)

    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found"
        )

    if classroom.faculty_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only classroom owner can remove students"
        )

    success = await EnrollmentService.remove_student(db, classroom_id, student_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found in this classroom"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST MANAGEMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{classroom_id}/tests", response_model=ClassroomTestResponse, status_code=status.HTTP_201_CREATED)
async def create_test(
    classroom_id: int,
    request: ClassroomTestCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new test in a classroom (faculty owner only)."""
    classroom = await ClassroomService.get_classroom_by_id(db, classroom_id)

    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found"
        )

    if classroom.faculty_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only classroom owner can create tests"
        )

    try:
        test = await TestService.create_test(db, classroom_id, current_user.id, request)
        return ClassroomTestResponse.model_validate(test)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating test: {str(e)}"
        )


@router.get("/{classroom_id}/tests", response_model=List[ClassroomTestResponse])
async def list_classroom_tests(
    classroom_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    status_filter: str = Query(None, description="Filter by status: draft, active, completed, archived")
):
    """List all tests in a classroom."""
    classroom = await ClassroomService.get_classroom_by_id(db, classroom_id)

    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found"
        )

    # Check authorization
    is_owner = classroom.faculty_id == current_user.id
    is_enrolled = any(
        e.student_id == current_user.id and e.is_active
        for e in classroom.student_enrollments
    )

    if not (is_owner or is_enrolled):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view tests"
        )

    tests = await TestService.get_classroom_tests(db, classroom_id)

    # Filter by status if provided
    if status_filter:
        tests = [t for t in tests if t.status.value == status_filter]

    # Hide unpublished tests from students
    if not is_owner:
        tests = [t for t in tests if t.is_published]

    return [ClassroomTestResponse.model_validate(t) for t in tests]


@router.get("/{classroom_id}/tests/{test_id}", response_model=ClassroomTestResponse)
async def get_test(
    classroom_id: int,
    test_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get test details."""
    test = await TestService.get_test_by_id(db, test_id)

    if not test or test.classroom_id != classroom_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )

    # Check authorization
    classroom = await ClassroomService.get_classroom_by_id(db, classroom_id)
    is_owner = classroom.faculty_id == current_user.id
    is_enrolled = any(
        e.student_id == current_user.id and e.is_active
        for e in classroom.student_enrollments
    )

    if not (is_owner or is_enrolled):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )

    if not is_owner and not test.is_published:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not published yet"
        )

    return ClassroomTestResponse.model_validate(test)


@router.put("/{classroom_id}/tests/{test_id}", response_model=ClassroomTestResponse)
async def update_test(
    classroom_id: int,
    test_id: int,
    request: ClassroomTestUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update test details (faculty owner only)."""
    test = await TestService.get_test_by_id(db, test_id)

    if not test or test.classroom_id != classroom_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )

    classroom = await ClassroomService.get_classroom_by_id(db, classroom_id)
    if classroom.faculty_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only test creator can update"
        )

    try:
        updated = await TestService.update_test(db, test_id, request)
        return ClassroomTestResponse.model_validate(updated)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating test: {str(e)}"
        )


@router.post("/{classroom_id}/tests/{test_id}/publish", response_model=ClassroomTestResponse)
async def publish_test(
    classroom_id: int,
    test_id: int,
    request: ClassroomTestPublishRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Publish/unpublish a test (faculty owner only)."""
    test = await TestService.get_test_by_id(db, test_id)

    if not test or test.classroom_id != classroom_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )

    classroom = await ClassroomService.get_classroom_by_id(db, classroom_id)
    if classroom.faculty_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only test creator can publish"
        )

    try:
        updated = await TestService.publish_test(db, test_id, request.is_published)
        return ClassroomTestResponse.model_validate(updated)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error publishing test: {str(e)}"
        )


@router.delete("/{classroom_id}/tests/{test_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test(
    classroom_id: int,
    test_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a test (faculty owner only)."""
    test = await TestService.get_test_by_id(db, test_id)

    if not test or test.classroom_id != classroom_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )

    classroom = await ClassroomService.get_classroom_by_id(db, classroom_id)
    if classroom.faculty_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only test creator can delete"
        )

    success = await TestService.delete_test(db, test_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting test"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST RESULT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{classroom_id}/tests/{test_id}/results", response_model=TestResultResponse, status_code=status.HTTP_201_CREATED)
async def submit_test_result(
    classroom_id: int,
    test_id: int,
    request: TestResultCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit a test result (students only)."""
    if current_user.role == "faculty":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faculty cannot submit test results"
        )

    # Get enrollment
    enrollment = await EnrollmentService.get_student_enrollment(db, classroom_id, current_user.id)
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enrolled in this classroom"
        )

    # Verify test exists and belongs to classroom
    test = await TestService.get_test_by_id(db, test_id)
    if not test or test.classroom_id != classroom_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )

    try:
        result = await ResultService.create_result(
            db, enrollment.id, test_id, request
        )
        return TestResultResponse.model_validate(result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error submitting result: {str(e)}"
        )


@router.get("/{classroom_id}/tests/{test_id}/results", response_model=List[TestResultResponse])
async def list_test_results(
    classroom_id: int,
    test_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all results for a test (faculty owner only)."""
    test = await TestService.get_test_by_id(db, test_id)

    if not test or test.classroom_id != classroom_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )

    classroom = await ClassroomService.get_classroom_by_id(db, classroom_id)
    if classroom.faculty_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only faculty can view test results"
        )

    results = await ResultService.get_test_results(db, test_id)
    return [TestResultResponse.model_validate(r) for r in results]


@router.get("/{classroom_id}/tests/{test_id}/results/{result_id}", response_model=TestResultResponse)
async def get_test_result(
    classroom_id: int,
    test_id: int,
    result_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific test result."""
    result = await ResultService.get_result_by_id(db, result_id)

    if not result or result.test_id != test_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found"
        )

    test = await TestService.get_test_by_id(db, test_id)
    if test.classroom_id != classroom_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found in this classroom"
        )

    # Check authorization
    classroom = await ClassroomService.get_classroom_by_id(db, classroom_id)
    is_owner = classroom.faculty_id == current_user.id
    is_student = result.student_enrollment.student_id == current_user.id

    if not (is_owner or is_student):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )

    return TestResultResponse.model_validate(result)


@router.put("/{classroom_id}/tests/{test_id}/results/{result_id}", response_model=TestResultResponse)
async def update_test_result(
    classroom_id: int,
    test_id: int,
    result_id: int,
    request: TestResultUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update test result (faculty owner only)."""
    result = await ResultService.get_result_by_id(db, result_id)

    if not result or result.test_id != test_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found"
        )

    test = await TestService.get_test_by_id(db, test_id)
    classroom = await ClassroomService.get_classroom_by_id(db, test.classroom_id)

    if classroom.faculty_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only faculty can update results"
        )

    try:
        updated = await ResultService.update_result(db, result_id, request)
        return TestResultResponse.model_validate(updated)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating result: {str(e)}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYTICS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/{classroom_id}/analytics", response_model=dict)
async def get_classroom_analytics(
    classroom_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get classroom-level analytics (faculty owner only)."""
    classroom = await ClassroomService.get_classroom_by_id(db, classroom_id)

    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found"
        )

    if classroom.faculty_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only classroom owner can view analytics"
        )

    analytics = await AnalyticsService.get_classroom_analytics(db, classroom_id)
    return analytics


@router.get("/{classroom_id}/tests/{test_id}/analytics", response_model=dict)
async def get_test_analytics(
    classroom_id: int,
    test_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get test-level analytics (faculty owner only)."""
    test = await TestService.get_test_by_id(db, test_id)

    if not test or test.classroom_id != classroom_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )

    classroom = await ClassroomService.get_classroom_by_id(db, classroom_id)
    if classroom.faculty_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only faculty can view analytics"
        )

    analytics = await AnalyticsService.get_test_analytics(db, test_id)
    return analytics

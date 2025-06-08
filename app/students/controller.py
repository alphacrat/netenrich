from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.database import get_database
from app.schemas.auth import StudentResponse
from app.schemas.issue import IssueResponse
from app.students.service import StudentService
from app.core.deps import get_current_active_user, get_admin_or_librarian

router = APIRouter(prefix="/students", tags=["Students"])


@router.get("/", response_model=dict)
async def search_students(
    department: Optional[str] = Query(None, description="Filter by department"),
    semester: Optional[int] = Query(None, description="Filter by semester"),
    search: Optional[str] = Query(
        None, description="Search by name, roll number, or phone"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_database),
    current_user=Depends(get_admin_or_librarian),
):
    students, total = await StudentService.search_students(
        db, department, semester, search, page, limit
    )

    return {
        "students": students,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit,
    }


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: int,
    db: AsyncSession = Depends(get_database),
    current_user=Depends(get_admin_or_librarian),
):
    student = await StudentService.get_student_by_id(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.get("/{student_identifier}/issues", response_model=List[IssueResponse])
async def get_student_issues(
    student_identifier: str,
    db: AsyncSession = Depends(get_database),
    current_user=Depends(get_current_active_user),
):
    issues = await StudentService.get_student_issues(db, student_identifier)
    return issues

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from app.scheduler.service import SchedulerService
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.database import get_database
from app.schemas.issue import IssueResponse, IssueCreate, IssueWithDetails
from app.issues.service import IssueService
from app.core.deps import get_current_active_user, get_admin_or_librarian

router = APIRouter(prefix="/issues", tags=["Issues"])


@router.post("/", response_model=IssueResponse)
async def issue_book(
    issue_data: IssueCreate,
    db: AsyncSession = Depends(get_database),
    current_user=Depends(get_admin_or_librarian),
):

    try:
        issue = await IssueService.issue_book(db, issue_data)
        return issue
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while issuing the book",
        )


@router.put("/{issue_id}/return", response_model=IssueResponse)
async def return_book(
    issue_id: int,
    db: AsyncSession = Depends(get_database),
    current_user=Depends(get_admin_or_librarian),
):
    try:
        issue = await IssueService.return_book(db, issue_id)
        return issue
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while returning the book",
        )


from fastapi import HTTPException


@router.get("/", response_model=dict)
async def get_all_issues(
    is_returned: Optional[bool] = Query(None, description="Filter by return status"),
    page: int = Query(1, ge=1, description="page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_database),
    current_user=Depends(get_admin_or_librarian),
):
    try:
        issues, total = await IssueService.get_all_issues(db, is_returned, page, limit)

        # transform to include additional details
        issue_with_details = []
        for issue in issues:
            issue_dict = {
                "id": issue.id,
                "book_id": issue.book_id,
                "student_id": issue.student_id,
                "issue_date": issue.issue_date,
                "due_date": issue.due_date,
                "return_date": issue.return_date,
                "is_returned": issue.is_returned,
                "book_title": issue.book.title,
                "book_author": issue.book.author,
                "student_name": issue.student.user.name,
                "student_roll_no": issue.student.roll_no,
            }
            issue_with_details.append(issue_dict)

        return {
            "issues": issue_with_details,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit,
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while fetching issues",
        )


@router.get("/overdue", response_model=List[IssueWithDetails])
async def get_overdue_books(
    db: AsyncSession = Depends(get_database),
    current_user=Depends(get_admin_or_librarian),
):
    try:
        issure = await IssueService.get_overdue_books(db)

        # transform the reposne to incude additonal details
        issue_with_details = []
        for issue in issure:
            issue_dict = {
                "id": issue.id,
                "book_id": issue.book_id,
                "student_id": issue.student_id,
                "issue_date": issue.issue_date,
                "due_date": issue.due_date,
                "return_date": issue.return_date,
                "is_returned": issue.is_returned,
                "book_title": issue.book.title,
                "book_author": issue.book.author,
                "student_name": issue.student.user.name,
                "student_roll_no": issue.student.roll_no,
            }
            issue_with_details.append(issue_dict)

        return issue_with_details
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while fetching overdue books",
        )


@router.post(
    "/trigger-overdue-check",
    summary="Trigger overdue check manually",
    description="Admin/Librarian endpoint to manually trigger overdue book checks",
    dependencies=[Depends(get_admin_or_librarian)],
)
async def trigger_overdue_check(
    background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_database)
):
    """Manually trigger overdue book check"""
    try:
        background_tasks.add_task(SchedulerService.check_overdue_books, db)
        return {"message": "Overdue check triggered successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error triggering overdue check: {str(e)}"
        )

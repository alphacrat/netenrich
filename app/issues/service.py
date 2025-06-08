from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from app.issues.model import Issue
from app.books.model import Book
from app.auth.model import Student
from app.schemas.issue import IssueCreate


class IssueService:

    @staticmethod
    async def issue_book(db: AsyncSession, issue_data: IssueCreate) -> Issue:
        # Check if book exists and has available copies
        book_result = await db.execute(
            select(Book).where(Book.id == issue_data.book_id)
        )
        book = book_result.scalar_one_or_none()

        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        if book.available_copies <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No available copies of this book",
            )

        # Check if student exists
        student_result = await db.execute(
            select(Student).where(Student.user_id == issue_data.student_id)
        )
        student = student_result.scalar_one_or_none()

        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        # Check if student already has this book issued
        existing_issue = await db.execute(
            select(Issue).where(
                and_(
                    Issue.book_id == issue_data.book_id,
                    Issue.student_id == issue_data.student_id,
                    Issue.is_returned == False,
                )
            )
        )

        if existing_issue.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Student already has this book issued",
            )

        # Create issue record
        due_date = datetime.now(timezone.utc) + timedelta(
            days=issue_data.days_to_return
        )

        db_issue = Issue(
            book_id=issue_data.book_id,
            student_id=issue_data.student_id,
            due_date=due_date,
        )

        db.add(db_issue)

        # Update book available copies
        await db.execute(
            update(Book)
            .where(Book.id == issue_data.book_id)
            .values(available_copies=Book.available_copies - 1)
        )

        await db.commit()
        await db.refresh(db_issue)
        return db_issue

    @staticmethod
    async def return_book(db: AsyncSession, issue_id: int) -> Issue:
        # Get the issue record
        result = await db.execute(
            select(Issue).options(selectinload(Issue.book)).where(Issue.id == issue_id)
        )
        issue = result.scalar_one_or_none()

        if not issue:
            raise HTTPException(status_code=404, detail="Issue record not found")

        if issue.is_returned:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Book already returned"
            )

        # Mark as returned
        issue.is_returned = True
        issue.return_date = datetime.utcnow()

        # Update book available copies
        await db.execute(
            update(Book)
            .where(Book.id == issue.book_id)
            .values(available_copies=Book.available_copies + 1)
        )

        await db.commit()
        await db.refresh(issue)
        return issue

    @staticmethod
    async def get_all_issues(
        db: AsyncSession,
        is_returned: Optional[bool] = None,
        page: int = 1,
        limit: int = 10,
    ) -> tuple[List[Issue], int]:
        query = select(Issue).options(
            selectinload(Issue.book),
            selectinload(Issue.student).selectinload(Student.user),
        )

        if is_returned is not None:
            query = query.where(Issue.is_returned == is_returned)

        # Get total count
        from sqlalchemy import func

        count_query = select(func.count(Issue.id))
        if is_returned is not None:
            count_query = count_query.where(Issue.is_returned == is_returned)

        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit).order_by(Issue.issue_date.desc())

        result = await db.execute(query)
        issues = result.scalars().all()

        return list(issues), total

    @staticmethod
    async def get_overdue_books(db: AsyncSession) -> List[Issue]:
        current_time = datetime.utcnow()
        result = await db.execute(
            select(Issue)
            .options(
                selectinload(Issue.book),
                selectinload(Issue.student).selectinload(Student.user),
            )
            .where(and_(Issue.is_returned == False, Issue.due_date < current_time))
            .order_by(Issue.due_date.asc())
        )

        return list(result.scalars().all())

    @staticmethod
    async def get_books_due_soon(db: AsyncSession, days: int = 5) -> List[Issue]:
        """Get books that are due in the next X days"""
        current_time = datetime.utcnow()
        due_date_threshold = current_time + timedelta(days=days)

        result = await db.execute(
            select(Issue)
            .options(
                selectinload(Issue.book),
                selectinload(Issue.student).selectinload(Student.user),
            )
            .where(
                and_(
                    Issue.is_returned == False,
                    Issue.due_date > current_time,
                    Issue.due_date <= due_date_threshold,
                )
            )
            .order_by(Issue.due_date.asc())
        )

        return list(result.scalars().all())

    @staticmethod
    async def update_last_notice_sent(
        db: AsyncSession, issue_id: int, timestamp: datetime
    ) -> None:
        """Update the last notice sent time for an issue"""
        await db.execute(
            update(Issue).where(Issue.id == issue_id).values(last_notice_sent=timestamp)
        )
        await db.commit()

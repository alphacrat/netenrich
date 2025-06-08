from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from typing import Optional, List
from app.auth.model import Student, User
from app.issues.model import Issue
from app.books.model import Book


class StudentService:

    @staticmethod
    async def get_student_by_id(db: AsyncSession, student_id: int) -> Optional[Student]:
        try:
            result = await db.execute(
                select(Student)
                .options(selectinload(Student.user))
                .where(Student.user_id == student_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            print(f"Error in get_student_by_id: {e}")
            raise

    @staticmethod
    async def search_students(
        db: AsyncSession,
        department: Optional[str] = None,
        semester: Optional[int] = None,
        search_term: Optional[str] = None,
        page: int = 1,
        limit: int = 10,
    ) -> tuple[List[Student], int]:
        try:
            query = select(Student).options(selectinload(Student.user))

            conditions = []

            if department:
                conditions.append(Student.department.ilike(f"%{department}%"))

            if semester:
                conditions.append(Student.semester == semester)

            if search_term:
                # Search in name, roll number, or phone
                search_conditions = [
                    User.name.ilike(f"%{search_term}%"),
                    Student.roll_no.ilike(f"%{search_term}%"),
                    User.phone.ilike(f"%{search_term}%"),
                ]
                query = query.join(User)
                conditions.append(or_(*search_conditions))
            else:
                query = query.join(User)

            if conditions:
                query = query.where(and_(*conditions))

            # Get total count
            count_query = select(func.count(Student.user_id)).join(User)
            if conditions:
                count_query = count_query.where(and_(*conditions))

            total_result = await db.execute(count_query)
            total = total_result.scalar()

            # Apply pagination
            offset = (page - 1) * limit
            query = query.offset(offset).limit(limit)

            result = await db.execute(query)
            students = result.scalars().all()

            return list(students), total
        except Exception as e:
            print(f"Error in search_students: {e}")
            raise

    @staticmethod
    async def get_student_issues(
        db: AsyncSession, student_identifier: str
    ) -> List[Issue]:
        try:
            # Try to find student by roll_no, name, or phone
            student_query = (
                select(Student).options(selectinload(Student.user)).join(User)
            )

            conditions = [
                Student.roll_no == student_identifier,
                User.name.ilike(f"%{student_identifier}%"),
                User.phone == student_identifier,
            ]

            student_query = student_query.where(or_(*conditions))
            result = await db.execute(student_query)
            student = result.scalar_one_or_none()

            if not student:
                return []

            # Get active issues for this student
            issues_query = (
                select(Issue)
                .options(selectinload(Issue.book))
                .where(
                    and_(
                        Issue.student_id == student.user_id, Issue.is_returned == False
                    )
                )
            )

            result = await db.execute(issues_query)
            return list(result.scalars().all())
        except Exception as e:
            print(f"Error in get_student_issues: {e}")
            raise

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from datetime import timedelta
from app.auth.model import User, Student, Employee, UserType
from app.schemas.auth import UserCreate, StudentCreate, EmployeeCreate
from app.utils.hashing import hash_password, verify_password
from app.utils.jwt import create_access_token
from app.config import settings


class AuthService:

    @staticmethod
    async def create_user(
        db: AsyncSession, user_data: UserCreate, additional_data=None
    ):
        # Check if email already exists
        result = await db.execute(select(User).where(User.email == user_data.email))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Hash password
        hashed_password = hash_password(user_data.password)

        # Create user
        db_user = User(
            email=user_data.email,
            name=user_data.name,
            phone=user_data.phone,
            password_hash=hashed_password,
            user_type=user_data.user_type,
        )

        db.add(db_user)
        await db.flush()  # Get the user ID

        # Create student profile if needed
        if user_data.user_type == UserType.STUDENT and additional_data:
            if isinstance(additional_data, StudentCreate):
                # Check if roll number already exists
                result = await db.execute(
                    select(Student).where(Student.roll_no == additional_data.roll_no)
                )
                if result.scalar_one_or_none():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Roll number already registered",
                    )

                student = Student(
                    user_id=db_user.id,
                    roll_no=additional_data.roll_no,
                    department=additional_data.department,
                    semester=additional_data.semester,
                )
                db.add(student)

        # Create employee profile if needed
        elif (
            user_data.user_type in [UserType.ADMIN, UserType.LIBRARIAN]
            and additional_data
        ):
            if isinstance(additional_data, EmployeeCreate):
                # Check if employee ID already exists
                result = await db.execute(
                    select(Employee).where(
                        Employee.employee_id == additional_data.employee_id
                    )
                )
                if result.scalar_one_or_none():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Employee ID already registered",
                    )

                employee = Employee(
                    user_id=db_user.id,
                    employee_id=additional_data.employee_id,
                    designation=additional_data.designation,
                    department=additional_data.department,
                    salary=additional_data.salary,
                )
                db.add(employee)

        await db.commit()
        await db.refresh(db_user)
        return db_user

    @staticmethod
    async def authenticate_user(db: AsyncSession, email: str, password: str):
        """Fixed method signature to match router usage"""
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            return None
        return user

    @staticmethod
    async def create_access_token_for_user(user: User):
        """Create access token for a user object"""
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        return access_token

    @staticmethod
    async def create_access_token(user: User):
        """Legacy method - kept for backward compatibility"""
        return await AuthService.create_access_token_for_user(user)

    @staticmethod
    async def get_user_by_email(email: str, db: AsyncSession):
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        return user

    @staticmethod
    async def get_user_with_profile(db: AsyncSession, user_id: int):
        """Eagerly load user with their profile relationships"""
        result = await db.execute(
            select(User)
            .options(selectinload(User.student), selectinload(User.employee))
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

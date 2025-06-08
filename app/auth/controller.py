from fastapi import APIRouter, Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime, timezone

from app.database import get_database
from app.schemas.auth import (
    UserCreate,
    StudentCreate,
    EmployeeCreate,
    UserResponse,
    Token,
    StudentResponse,
    EmployeeResponse,
    StudentResponseSimple,
    EmployeeResponseSimple,
)
from app.auth.service import AuthService
from app.auth.model import UserType
from app.core.deps import get_current_active_user, get_admin

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_active_user_optional(
    token: Optional[str] = Security(oauth2_scheme),
) -> Optional[UserResponse]:
    """
    Get current user but don't raise error if token is missing or invalid.
    Returns None if no valid token is provided.
    """
    if not token:
        return None
    try:
        return await get_current_active_user(token)
    except Exception:
        return None


@router.post(
    "/register/student",
    response_model=StudentResponseSimple,
    status_code=status.HTTP_201_CREATED,
)
async def register_student(
    user_data: UserCreate,
    student_data: StudentCreate,
    db: AsyncSession = Depends(get_database),
):
    """
    Register a new student.
    This endpoint is open to everyone (no authentication required).
    """

    if user_data.user_type != UserType.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User type must be student for this endpoint",
        )

    try:
        # Create user and student profile
        user = await AuthService.create_user(db, user_data, student_data)

        # Get user with eagerly loaded profile data
        user_with_profile = await AuthService.get_user_with_profile(db, user.id)

        if not user_with_profile or not user_with_profile.student:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create student profile",
            )

        # Return the student profile without the user relationship
        return user_with_profile.student

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        print(f"Student registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student registration failed. Email might already exist.",
        )


@router.post(
    "/register/employee",
    response_model=EmployeeResponseSimple,
    status_code=status.HTTP_201_CREATED,
)
async def register_employee(
    user_data: UserCreate,
    employee_data: EmployeeCreate,
    db: AsyncSession = Depends(get_database),
    current_user: UserResponse = Depends(
        get_admin
    ),  # Only admin can create employee account
):
    """
    Register a new employee.
    Only admin users can access this endpoint.
    """

    if user_data.user_type not in [UserType.ADMIN, UserType.LIBRARIAN]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only create admin or librarian accounts from this endpoint",
        )

    try:
        # Create user and employee profile
        user = await AuthService.create_user(db, user_data, employee_data)

        # Get user with eagerly loaded profile data
        user_with_profile = await AuthService.get_user_with_profile(db, user.id)

        if not user_with_profile or not user_with_profile.employee:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create employee profile",
            )

        # Return the employee profile without the user relationship
        return user_with_profile.employee

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        print(f"Employee registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee registration failed. Email might already exist.",
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_database),
):
    """
    Authenticate user and return access token.
    """
    user = await AuthService.authenticate_user(
        db, form_data.username, form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = await AuthService.create_access_token_for_user(user)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: UserResponse = Depends(get_current_active_user)):
    """
    Get current user's profile information.
    """
    return current_user


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    current_user: UserResponse = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    """
    Logout user (token invalidation would be handled client-side in stateless JWT setup).
    """
    try:
        return {
            "message": "Successfully logged out",
            "user_id": current_user.id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        print(f"Logout error: {e}")
        # Even if cleanup fails, we can still return success
        # since the client should remove the token anyway
        return {"message": "Logged out (with cleanup warnings)"}


@router.get("/verify-token")
async def verify_token(current_user: UserResponse = Depends(get_current_active_user)):
    """
    Verify if the current token is valid and return user information.
    """
    return {
        "valid": True,
        "user_type": current_user.user_type,
        "user_id": current_user.id,
        "email": current_user.email,
        "is_active": current_user.is_active,
    }


@router.post("/refresh-token", response_model=Token)
async def refresh_token(
    current_user: UserResponse = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    """
    Refresh the access token for the current user.
    This is useful for extending sessions without requiring re-login.
    """
    try:
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled",
            )

        access_token = await AuthService.create_access_token_for_user(current_user)
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        print(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed",
        )

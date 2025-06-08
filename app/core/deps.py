from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_database
from app.auth.model import User, UserType
from app.utils.jwt import verify_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_database)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    email = verify_token(token)
    if email is None:
        raise credentials_exception

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return current_user


async def get_admin(curent_user: User = Depends(get_current_active_user)):
    if curent_user.user_type != UserType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="user unauthorized -> not an admin",
        )
    return curent_user


async def get_admin_or_librarian(current_user: User = Depends(get_current_active_user)):
    if current_user.user_type not in (UserType.ADMIN, UserType.LIBRARIAN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="user unauthorized -> not an admin or librarian",
        )
    return current_user

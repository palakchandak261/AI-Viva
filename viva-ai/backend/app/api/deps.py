"""FastAPI dependency injection — auth, DB session, current user."""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if not user_id:
        raise credentials_exception

    # Use select instead of db.get() to avoid UUID type issues with SQLite
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise credentials_exception
    return user


async def get_current_student(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in (UserRole.student, UserRole.admin):
        raise HTTPException(status_code=403, detail="Students only.")
    return current_user


async def get_current_faculty(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in (UserRole.faculty, UserRole.admin):
        raise HTTPException(status_code=403, detail="Faculty only.")
    return current_user

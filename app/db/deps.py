# FastAPI dependencies — injected into route functions via Depends().
# Dependencies in FastAPI are like reusable setup/teardown blocks that run before
# each request handler. They handle the database session lifecycle and auth checks.

from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.db.repositories.user_repository import UserRepository
from app.db.models import User
from app.services.rule_engine import RuleEngine
from app.services import auth as auth_service

async def get_db():
    # Opens a DB session for the duration of one request, then closes it.
    # If anything raises inside the route, the session is rolled back.
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


def get_rule_engine(request: Request) -> RuleEngine:
    # Retrieves the RuleEngine that was loaded at startup from app.state.
    # This avoids re-reading the rules JSON on every request.
    return request.app.state.rule_engine


# Tells FastAPI to read the Bearer token from the Authorization header.
# The tokenUrl tells the /docs UI where to send login requests.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db)
) -> User:
    # Decodes the JWT, looks up the user in the DB, and returns them.
    # Any route that Depends() on this will automatically reject unauthenticated requests.
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = auth_service.decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    repo = UserRepository(db)
    user = await repo.get_user_by_id(user_id)
    if not user or not user.is_active:
        raise credentials_exception
    return user

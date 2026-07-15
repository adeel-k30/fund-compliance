# Authentication routes: register a new organisation and log in to get a JWT.
#
# Flow:
#   POST /auth/register  → creates a Client (tenant) + User, returns user details
#   POST /auth/token     → verifies credentials, returns a JWT access token
#
# The JWT is then passed as "Authorization: Bearer <token>" on every protected request.

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.user_repository import UserRepository
from app.schemas.auth import UserRegister, Token, UserSummary
from app.db.deps import get_db
from app.services.auth import  hash_password, create_access_token, verify_password


router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
        user_data: UserRegister,
        db: AsyncSession = Depends(get_db)
) -> UserSummary:
    repo = UserRepository(db)
    existing_user = await repo.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = hash_password(user_data.password)
    user = await repo.create_user(organisation_name=user_data.organisation_name, email=user_data.email, hashed_password=hashed_password)

    return UserSummary.model_validate(user)


@router.post("/token", summary="Login")
async def login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_db)
) -> Token:
    repo = UserRepository(db)
    user = await repo.get_user_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials", headers={"WWW-Authenticate": "Bearer"})
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive")
    # "sub" (subject) is the standard JWT claim for the entity the token represents.
    # We also embed client_id so downstream code can use it without an extra DB lookup.
    access_token = create_access_token(data={"sub": user.id, "client_id": user.client_id})
    return Token(access_token=access_token, token_type="bearer")





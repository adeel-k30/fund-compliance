# Pydantic schemas for the auth endpoints — separate from the ORM models.
# These define what the API accepts as input and returns as output.
# ConfigDict(from_attributes=True) lets Pydantic read values from SQLAlchemy
# model instances directly (without having to convert to a dict first).

from pydantic import BaseModel, ConfigDict, Field, EmailStr
from datetime import datetime

class UserRegister(BaseModel):
    # Input for POST /auth/register
    organisation_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8)

class Token(BaseModel):
    # Response from POST /auth/token — the client stores access_token and sends it
    # in the Authorization header on all subsequent requests
    access_token: str
    token_type: str = "bearer"

class UserSummary(BaseModel):
    # Response from POST /auth/register — confirms what was created
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    client_id: str
    is_active: bool
    created_at: datetime


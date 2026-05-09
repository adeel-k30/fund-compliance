from pydantic import BaseModel, ConfigDict, Field, EmailStr
from datetime import datetime

class UserRegister(BaseModel):
    organisation_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    client_id: str
    is_active: bool
    created_at: datetime


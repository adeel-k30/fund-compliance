from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

class ClientCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class ClientSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    created_at: datetime
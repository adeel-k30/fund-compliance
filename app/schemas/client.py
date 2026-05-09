from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

class ClientSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    created_at: datetime
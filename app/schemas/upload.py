from pydantic import BaseModel, ConfigDict
from datetime import datetime


class UploadSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    template_type: str
    total_rows: int
    rows_with_issues: int
    status: str
    created_at: datetime
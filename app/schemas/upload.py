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


class UploadAccepted(BaseModel):
    upload_id: str
    task_id: str
    message: str = "File uploaded successfully. Validation is running in the background."

STATUS_MESSAGES = {
    "pending": "Your file has been uploaded and is queued for validation.",
    "processing": "Validation is currently running.",
    "complete": "Validation completed successfully.",
    "failed": "Validation failed. Please check your file and try again.",
}

class UploadStatus(BaseModel):
    upload_id: str
    status: str
    task_id: str | None
    total_rows: int | None
    rows_with_issues: int | None
    message: str | None
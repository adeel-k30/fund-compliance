# Pydantic schemas for the validation/upload endpoints.
# These are the API's public contract — what clients see in responses.
# They intentionally expose less than the full ORM model (e.g. s3_key is internal).

from pydantic import BaseModel, ConfigDict
from datetime import datetime


class UploadSummary(BaseModel):
    # Returned by GET /validate/uploads and GET /validate/uploads/{id}
    model_config = ConfigDict(from_attributes=True)  # allows reading from SQLAlchemy objects

    id: str
    filename: str
    template_type: str
    total_rows: int
    rows_with_issues: int
    status: str
    created_at: datetime


class UploadAccepted(BaseModel):
    # Returned immediately (202) after POST /validate/emt.
    # The client uses upload_id to poll for results and task_id to check Celery status.
    upload_id: str
    task_id: str
    message: str = "File uploaded successfully. Validation is running in the background."


# Human-readable status descriptions returned by the /status endpoint
STATUS_MESSAGES = {
    "pending": "Your file has been uploaded and is queued for validation.",
    "processing": "Validation is currently running.",
    "complete": "Validation completed successfully.",
    "failed": "Validation failed. Please check your file and try again.",
}

class UploadStatus(BaseModel):
    # Returned by GET /validate/uploads/{id}/status — a lightweight polling response
    upload_id: str
    status: str
    task_id: str | None
    total_rows: int | None
    rows_with_issues: int | None
    message: str | None
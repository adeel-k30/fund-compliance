# Validation routes — the core workflow of the API:
#   POST /validate/emt               Upload a file → stores in S3, queues Celery job, returns 202
#   GET  /validate/uploads           List all uploads for the current client (paginated)
#   GET  /validate/uploads/{id}      Fetch one upload record
#   GET  /validate/uploads/{id}/status  Poll for processing progress and results
#
# All routes require a valid JWT. The current_user dependency enforces this
# and also scopes every DB query to that user's client_id.

import uuid
import asyncio
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Form, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.s3_service import upload_file_to_s3, delete_file_from_s3
from app.db.deps import get_db, get_current_user
from app.db.models import UploadStatus, User
from app.db.repositories.upload_repository import UploadRepository
from app.schemas.upload import UploadSummary, UploadAccepted, UploadStatus as UploadStatusSchema, STATUS_MESSAGES
from app.worker.tasks import validate_emt_file

router = APIRouter(
    prefix="/validate",
    tags=["validate"])

@router.post("/emt", status_code=status.HTTP_202_ACCEPTED)
async def validate_emt(
        current_user: User = Depends(get_current_user),
        file: UploadFile = File(...),
        delimiter: str = Form(","),
        db: AsyncSession = Depends(get_db)
) -> UploadAccepted:

    extension = file.filename.split('.')[-1].lower()
    if extension not in ['xlsx', 'xls', 'csv']:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only Excel (.xlsx, .xls) and CSV files are supported"
        )


    upload_id = str(uuid.uuid4())
    # Read the files bytes
    contents = await file.read()

    # S3 key structure: uploads/<client_id>/<upload_id>/<filename>
    # Namespacing by client_id ensures files are naturally isolated per tenant.
    s3_key = f"uploads/{current_user.client_id}/{upload_id}/{file.filename}"

    # upload_file_to_s3 is a synchronous (blocking) call. run_in_executor offloads it
    # to a thread pool so the async event loop isn't blocked while the file uploads.
    await asyncio.get_running_loop().run_in_executor(None, upload_file_to_s3, contents, s3_key)

    repo = UploadRepository(db)

    try:
        upload = await repo.create_upload(  # capture the returned Upload object
            upload_id=upload_id,
            client_id=current_user.client_id,
            filename=file.filename,
            template_type="EMT", # This is a placeholder, implement logic to determine the template type based on the file content or name
            template_version="V4.2",
            total_rows=0,
            rows_with_issues=0,
            status=UploadStatus.PENDING,
            s3_key= s3_key
        )
    except Exception as e:
        # clean up — delete orphaned S3 file
        await asyncio.get_running_loop().run_in_executor(None, delete_file_from_s3, s3_key)
        raise HTTPException(status_code=500, detail="Failed to create upload record")

    # Queue task get task_id
    task = validate_emt_file.delay(upload_id, s3_key, file.filename, delimiter)

    # Update the upload record with the Celery task ID
    try:
        await repo.update_upload(upload_id=upload_id, task_id=task.id)
    except Exception as e:
        task.revoke()
        await asyncio.get_event_loop().run_in_executor(None, delete_file_from_s3, s3_key)
        raise HTTPException(status_code=500, detail="Failed to update upload record")

    return  UploadAccepted(
        upload_id=upload.id,
        task_id=task.id,
        message="File uploaded successfully. Validation is running in the background."
    )


@router.get("/uploads")
async def get_uploads(
        current_user: User = Depends(get_current_user),
        skip: int = 0,
        limit: int = 20,
        db: AsyncSession = Depends(get_db)
) -> list[UploadSummary]:

    repo = UploadRepository(db)
    uploads = await repo.list_uploads(client_id=current_user.client_id, skip=skip, limit=limit)
    return [UploadSummary.model_validate(upload) for upload in uploads] # Use model_validate to convert SQLAlchemy models to Pydantic schemas


@router.get("/uploads/{upload_id}")
async def get_upload(
        upload_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
) -> UploadSummary:

    repo = UploadRepository(db)
    upload = await repo.get_upload_by_id(upload_id, client_id=current_user.client_id)
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    return UploadSummary.model_validate(upload)


@router.get("/uploads/{upload_id}/status")
async def get_upload_status(
        upload_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
) -> UploadStatusSchema:

    repo = UploadRepository(db)
    upload = await repo.get_upload_by_id(upload_id, current_user.client_id)

    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    return UploadStatusSchema(
        upload_id=upload.id,
        status=upload.status,
        task_id=upload.task_id,
        total_rows=upload.total_rows,
        rows_with_issues=upload.rows_with_issues,
        message=STATUS_MESSAGES.get(upload.status))

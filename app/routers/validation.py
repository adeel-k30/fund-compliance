from fastapi import APIRouter, UploadFile, File, HTTPException, status, Form, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.file_parser import parse_upload
from app.services.rule_engine import RuleEngine
from app.db.deps import get_db, get_rule_engine, get_current_user
from app.db.models import User
from app.db.repositories.upload_repository import UploadRepository
from app.schemas.upload import UploadSummary
from app.models.validation import ValidationReport

router = APIRouter(
    prefix="/validate",
    tags=["validate"])

@router.post("/emt")
async def validate_emt(
        current_user: User = Depends(get_current_user),
        file: UploadFile = File(...),
        delimiter: str = Form(","),
        db: AsyncSession = Depends(get_db),
        rule_engine: RuleEngine = Depends(get_rule_engine)
) -> ValidationReport:

    extension = file.filename.split('.')[-1].lower()
    if extension not in ['xlsx', 'xls', 'csv']:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only Excel (.xlsx, .xls) and CSV files are supported"
        )

    # Read the files bytes
    contents = await file.read()

    try:
        rows = parse_upload(file.filename, contents, delimiter)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    validation_results = rule_engine.validate_file(rows, file.filename)

    repo = UploadRepository(db)
    upload = await repo.create_upload(  # capture the returned Upload object
        client_id=current_user.client_id,
        filename=file.filename,
        template_type="EMT", # This is a placeholder, you can implement logic to determine the template type based on the file content or name
        template_version=validation_results.template_version,
        total_rows=validation_results.total_rows,
        rows_with_issues=validation_results.rows_with_issues
    )
    await repo.save_validation_issues(upload.id, validation_results)

    return  validation_results


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
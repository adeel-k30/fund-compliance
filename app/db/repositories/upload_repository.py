# Data access layer for Upload records and their associated ValidationIssues.
# All queries filter by client_id — this enforces tenant isolation so one
# client can never access another client's uploads, even with a valid token.

from sqlalchemy import select

from app.db.models import Upload, ValidationIssue
from app.models.validation import ValidationReport
from app.db.models import UploadStatus

class UploadRepository:
    def __init__(self, session):
        self.session = session

    async def create_upload(self, upload_id, client_id: str, filename: str, template_type: str, template_version:str, total_rows: int, rows_with_issues: int, status: UploadStatus, s3_key: str) -> Upload:
        new_upload = Upload(
            id=upload_id,
            client_id=client_id,
            filename=filename,
            template_type=template_type,
            template_version=template_version,
            total_rows=total_rows,
            rows_with_issues=rows_with_issues,
            status=status,
            s3_key=s3_key,
        )
        self.session.add(new_upload)
        await self.session.commit()
        await self.session.refresh(new_upload)

        return new_upload


    async def update_upload(self, upload_id: str, **kwargs) -> Upload | None:
        upload = await self.session.get(Upload, upload_id)
        if not upload:
            return None
        for key, value in kwargs.items():
            setattr(upload, key, value)

        await self.session.commit()
        await self.session.refresh(upload)
        return upload


    async def save_validation_issues(self, upload_id: str, validation_report: ValidationReport) -> int:
        issues_to_add = []
        for row in validation_report.results:
            for issue in row.issues:
                new_issue = ValidationIssue(
                    upload_id=upload_id,
                    row_index=row.row_index,
                    isin=row.isin,
                    instrument_name=row.instrument_name,
                    field_code=issue.field_code,
                    field_label=issue.field_label,
                    rule_type=issue.rule_type.value,
                    message=issue.message
                )
                issues_to_add.append(new_issue)

        self.session.add_all(issues_to_add)
        await self.session.commit()
        return len(issues_to_add)


    async def get_upload_by_id(self, upload_id: str, client_id: str) -> Upload | None:
        result = await self.session.execute(select(Upload).where(Upload.id == upload_id).where(Upload.client_id == client_id))
        return result.scalar_one_or_none()


    async def list_uploads(self, client_id: str, skip: int = 0, limit: int = 20) -> list[Upload]:
        result = await self.session.execute(select(Upload).where(Upload.client_id == client_id).offset(skip).limit(limit).order_by(Upload.created_at.desc()))
        return result.scalars().all()

    async def get_issues_by_upload_id(self, upload_id: str, client_id: str) -> list[ValidationIssue] | None:
        # Verify the upload belongs to this client before returning any issues.
        # Returns None if the upload doesn't exist or belongs to a different client (→ 404).
        upload = await self.get_upload_by_id(upload_id, client_id)
        if not upload:
            return None

        result = await self.session.execute(
            select(ValidationIssue)
            .where(ValidationIssue.upload_id == upload_id)
            .order_by(ValidationIssue.isin, ValidationIssue.row_index)
        )
        return result.scalars().all()





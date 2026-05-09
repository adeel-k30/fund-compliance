from sqlalchemy import select

from app.db.models import Upload, ValidationIssue
from app.models.validation import ValidationReport
from app.core.config import settings

class UploadRepository:
    def __init__(self, session):
        self.session = session

    async def create_upload(self, filename: str, template_type: str, template_version:str, total_rows: int, rows_with_issues: int) -> Upload:
        new_upload = Upload(
            client_id=settings.dev_client_id,  # In a real app, this would come from the authenticated user's client association
            filename=filename,
            template_type=template_type,
            template_version=template_version,
            total_rows=total_rows,
            rows_with_issues=rows_with_issues,
            status="complete"
        )
        self.session.add(new_upload)
        await self.session.commit()
        await self.session.refresh(new_upload)

        return new_upload


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


    async def get_upload_by_id(self, upload_id: str) -> Upload | None:
        result = await self.session.execute(select(Upload).where(Upload.id == upload_id))
        return result.scalar_one_or_none()


    async def list_uploads(self, skip: int = 0, limit: int = 20) -> list[Upload]:
        result = await self.session.execute(select(Upload).offset(skip).limit(limit).order_by(Upload.created_at.desc()))
        return result.scalars().all()





from pathlib import Path
import json

from app.worker.celery_app import celery_app
from app.services.s3_service import download_file_from_s3
from app.services.file_parser import parse_upload
from app.services.rule_engine import RuleEngine
from app.models.rules import FieldRule
from app.db.models import Upload, UploadStatus
from app.db.session import SyncSessionLocal
from app.db.models import ValidationIssue

rules_path = Path("app/data/emt_rules.json")
_rules = [FieldRule.model_validate(r) for r in json.loads(rules_path.read_text())]
_rule_engine = RuleEngine(_rules)

@celery_app.task(bind=True, max_retries=3)
def validate_emt_file(self, upload_id: str, s3_key: str, filename: str, delimiter: str = ","):
    db = SyncSessionLocal()
    try:
        # 1. Update status to processing
        upload = db.get(Upload, upload_id)
        upload.status = UploadStatus.PROCESSING
        db.commit()

        # 2. Download file bytes from s3
        file_bytes = download_file_from_s3(s3_key)

        # 3. Parse the file
        rows = parse_upload(filename, file_bytes, delimiter=delimiter)

        # 4. Run validation
        validation_report = _rule_engine.validate_file(rows, filename)

        # 5. Save validation issues
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

        db.add_all(issues_to_add)
        upload.total_rows = validation_report.total_rows
        upload.rows_with_issues = validation_report.rows_with_issues
        upload.status = UploadStatus.COMPLETE
        db.commit()

    except Exception as e:
        db.rollback()

        try:
            upload = db.get(Upload, upload_id)
            if upload:
                if self.request.retries >= self.max_retries:
                    upload.status = UploadStatus.FAILED
                db.commit()
        except Exception:
            pass # If we fail to update status, there's not much we can do

        raise self.retry(exc=e, countdown=60) # Retry after 1 minute

    finally:
        db.close()

from pydantic import BaseModel, Field

from app.models.rules import RuleType

class ValidationIssue(BaseModel):
    field_code: str = Field(..., max_length=5)
    field_label: str
    allowed_values: list[str] | None = None
    rule_type: RuleType
    message: str
    row_index: int | None = None

class RowValidationResult(BaseModel):
    row_index: int
    isin: str
    instrument_name: str
    issues: list[ValidationIssue]
    is_valid: bool

class ValidationReport(BaseModel):
    filename: str
    template_version: str
    total_rows: int
    rows_with_issues: int
    valid_rows: int
    results: list[RowValidationResult]

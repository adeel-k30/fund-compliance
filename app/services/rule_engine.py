import math

from app.models.rules import FieldRule, Condition, RuleType, ConditionOperator
from app.models.validation import RowValidationResult, ValidationIssue, ValidationReport


class RuleEngine():
    def __init__(self, rules: list[FieldRule]):
        self.rules = rules

    @staticmethod
    def _is_empty(value) -> bool:
        """
        Returns True if a cell value should be considered empty.
        Handles the three cases pandas can return for a missing/empty cell:
          - None       → missing object
          - ""         → empty string
          - float('nan') → pandas NaN for numeric/untyped empty cells
        """
        if value is None:
            return True
        if isinstance(value, float) and math.isnan(value):
            return True
        if isinstance(value, str) and value.strip() == "":
            return True
        return False

    # Checks if a given row of data satisfies the specified condition and should the rule be applied
    def evaluate_condition(self, condition: Condition, row: dict) -> bool:
        field_value = row.get(condition.field_code)

        if condition.operator == ConditionOperator.EQUALS:
            return field_value == condition.value
        elif condition.operator == ConditionOperator.NOT_EQUALS:
            return field_value != condition.value
        elif condition.operator == ConditionOperator.IN_SET:
            return field_value in condition.values
        elif condition.operator == ConditionOperator.NOT_IN_SET:
            return field_value not in condition.values
        elif condition.operator == ConditionOperator.IS_EMPTY:
            return self._is_empty(field_value)
        elif condition.operator == ConditionOperator.IS_NOT_EMPTY:
            return not self._is_empty(field_value)
        elif condition.operator == ConditionOperator.AND:
            return all(self.evaluate_condition(cond, row) for cond in condition.conditions or [])
        elif condition.operator == ConditionOperator.OR:
            return any(self.evaluate_condition(cond, row) for cond in condition.conditions or [])
        else:
            raise ValueError(f"Unsupported operator: {condition.operator}")


    def validate_row(self, row: dict, row_index: int) -> RowValidationResult:
        issues: list[ValidationIssue] = []
        for rule in self.rules:
            if rule.condition is None or self.evaluate_condition(rule.condition, row):
                field_value = row.get(rule.field_code)
                if rule.rule_type == RuleType.EXPECT_VALUE and self._is_empty(field_value):
                    issues.append(ValidationIssue(
                        field_code=rule.field_code,
                        field_label=rule.label,
                        allowed_values=rule.allowed_values,
                        rule_type=rule.rule_type,
                        message=f"Field {rule.label} ({rule.field_code}) is mandatory but has no value.",
                        row_index=row_index
                    ))
                elif rule.rule_type == RuleType.EXPECT_EMPTY and not self._is_empty(field_value):
                    issues.append(ValidationIssue(
                        field_code=rule.field_code,
                        field_label=rule.label,
                        allowed_values=rule.allowed_values,
                        rule_type=rule.rule_type,
                        message=f"Field {rule.label} ({rule.field_code}) should be empty but has a value.",
                        row_index=row_index
                    ))
                elif rule.rule_type == RuleType.CUSTOM:
                    # Placeholder for custom validation logic
                    pass

        return RowValidationResult(
            row_index=row_index,
            isin=row.get('00010', ''),
            instrument_name=row.get('00030', ''),
            issues=issues,
            is_valid=len(issues) == 0
        )


    def validate_file(self, rows: list[dict], filename: str) -> ValidationReport:
        results: list[RowValidationResult] = []

        for index, row in enumerate(rows):
            result = self.validate_row(row, index)
            results.append(result)

        return ValidationReport(
            filename=filename,
            template_version=rows[0].get('00001', 'unknown'),
            total_rows=len(rows),
            rows_with_issues=sum(1 for r in results if not r.is_valid),
            valid_rows=sum(1 for r in results if r.is_valid),
            results=results
        )

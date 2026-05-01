import math
import re
from datetime import datetime

from app.models.rules import FieldRule, FieldType, Condition, RuleType, ConditionOperator
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


    def _validate_field_type(self, value, field_type: FieldType) -> str | None:
        """
        Validates that a value conforms to the expected field type.
        Returns an error message if validation fails, or None if it passes.
        """
        if self._is_empty(value):
            return None  # Empty values are handled by rule types, not field type validation

        if field_type == FieldType.STRING:
            if not isinstance(value, str):
                return f"Expected a text, but got {type(value).__name__}."

        elif field_type == FieldType.INTEGER:
            try:
                int(value)
            except (ValueError, TypeError):
                return f"Expected an integer value, but got '{value}'."

        elif field_type == FieldType.DECIMAL:
            try:
                float(value)
            except (ValueError, TypeError):
                return f"Expected a decimal number, but got '{value}'."

        elif field_type == FieldType.PERCENTAGE:
            try:
                num = float(value)
                if not (0 <= num <= 1):
                    return f"Expected a percentage value between 0 and 1, but got '{value}'."
            except (ValueError, TypeError):
                return f"Expected a percentage value between 0 and 1, but got '{value}'."

        elif field_type == FieldType.DATE:
            try:
                datetime.strptime(str(value), "%Y-%m-%d")
            except ValueError:
                return f"Expected a date in YYYY-MM-DD format, but got '{value}'."

        elif field_type == FieldType.DATETIME:
            try:
                datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return f"Expected a datetime in ISO 8601 format (YYYY-MM-DD HH:MM:SS), but got '{value}'."

        elif field_type == FieldType.BOOLEAN:
            if str(value).upper() not in ['Y', 'N']:
                return f"Expected a boolean value 'Y' or 'N', but got '{value}'."

        elif field_type == FieldType.ISIN:
            if not re.match(r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$', str(value)):
                return f"Expected a valid ISIN code, but got '{value}'."

        elif field_type == FieldType.LEI:
            if not re.match(r'^[A-Z0-9]{20}$', str(value)):
                return f"Expected a valid 20-character LEI, got '{value}'"

        return None  # No error


    def _validate_allowed_values(self, value, allowed_values: list[str]) -> str | None:
        """
        Validates that a value is within the allowed values.
        Returns an error message if validation fails, or None if it passes.
        """
        if self._is_empty(value):
            return None  # Empty values are handled by rule types, not allowed values validation

        if str(value).strip() not in allowed_values:
            return f"Value '{value}' is not in the allowed set: {allowed_values}."

        return None  # No error


    # Checks if a given row of data satisfies the specified condition and should the rule be applied
    def _evaluate_condition(self, condition: Condition, row: dict) -> bool:
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
            return all(self._evaluate_condition(cond, row) for cond in condition.conditions or [])
        elif condition.operator == ConditionOperator.OR:
            return any(self._evaluate_condition(cond, row) for cond in condition.conditions or [])
        else:
            raise ValueError(f"Unsupported operator: {condition.operator}")


    def validate_row(self, row: dict, row_index: int) -> RowValidationResult:
        issues: list[ValidationIssue] = []
        validated_row = dict(row) # start as a copy of the raw row

        # Pass 1 — field format and allowed values
        for rule in self.rules:
            field_value = row.get(rule.field_code)
            if self._is_empty(field_value):
                continue # nothing to format-check on an empty field

            if rule.field_type:
                error = self._validate_field_type(field_value, rule.field_type)
                if error:
                    issues.append(ValidationIssue(
                        field_code=rule.field_code,
                        field_label=rule.label,
                        allowed_values=rule.allowed_values,
                        rule_type=RuleType.FORMAT,
                        message=error,
                        row_index= row_index

                    ))
                    validated_row[rule.field_code] = None # Clear invalid value for pass 2 rules

            if rule.allowed_values:
                error = self._validate_allowed_values(field_value, rule.allowed_values)
                if error:
                    issues.append(ValidationIssue(
                        field_code=rule.field_code,
                        field_label=rule.label,
                        allowed_values=rule.allowed_values,
                        rule_type=RuleType.ALLOWED_VALUES,
                        message=error,
                        row_index=row_index
                    ))
                    validated_row[rule.field_code] = None # Clear invalid value for pass 2 rules


        # Pass 2 — mandatory and conditional rules using validated_row
        for rule in self.rules:
            if rule.condition is None or self._evaluate_condition(rule.condition, row):
                field_value = validated_row.get(rule.field_code)
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

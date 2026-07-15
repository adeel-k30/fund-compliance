# Pydantic models that represent the structure of a rule loaded from emt_rules.json.
# These are NOT database models — they're in-memory data shapes used by the rule engine.
# Each FieldRule maps to one entry in the JSON file and describes how a single EMT
# field should be validated (its type, allowed values, and when it must/must not have a value).

from enum import Enum
from pydantic import BaseModel, Field

class ConditionOperator(str, Enum):
    # Operators used in a rule's condition block to decide whether the rule should fire
    EQUALS = 'eq'
    NOT_EQUALS = 'neq'
    IN_SET = 'in_set'
    NOT_IN_SET = 'not_in_set'
    IS_EMPTY = 'is_empty'
    IS_NOT_EMPTY = 'is_not_empty'
    AND = 'and'
    OR = 'or'

class Condition(BaseModel):
    # A condition decides whether a rule should apply to a given row.
    # For simple operators (eq, neq, in_set, etc.) use field_code + value/values.
    # For compound logic (and/or) use the nested `conditions` list instead.
    field_code: str | None = None
    operator: ConditionOperator
    value: str | None = None
    values: list[str] | None = None
    conditions: list['Condition'] | None = None  # Nested conditions for and/or

# model_rebuild() is required because Condition references itself (recursive type)
Condition.model_rebuild()

class RuleType(str, Enum):
    # Determines what kind of check the rule performs:
    # FORMAT        — is the value the right data type (date, ISIN, decimal, etc.)?
    # ALLOWED_VALUES — is the value in the permitted list?
    # EXPECT_VALUE  — the field must not be empty (mandatory field)
    # EXPECT_EMPTY  — the field must be empty (e.g. mutually exclusive with another field)
    # CUSTOM        — placeholder for one-off logic not covered above
    FORMAT = 'format'
    ALLOWED_VALUES = 'allowed_values'
    EXPECT_VALUE = 'expect_value'
    EXPECT_EMPTY = 'expect_empty'
    CUSTOM = 'custom'

class FieldType(str, Enum):
    STRING = 'string'
    INTEGER = 'integer'
    DECIMAL = 'decimal'
    PERCENTAGE = 'percentage'
    DATE = 'date'
    DATETIME = 'datetime'
    BOOLEAN = 'boolean'
    ISIN = 'isin'
    LEI = 'lei'


class FieldRule(BaseModel):
    field_code: str = Field(..., max_length=5)
    label: str
    field_type: FieldType | None = None
    allowed_values: list[str] | None = None
    rule_type: RuleType
    condition: Condition | None = None
    description: str | None = None

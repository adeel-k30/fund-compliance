from enum import Enum
from pydantic import BaseModel, Field

class ConditionOperator(str, Enum):
    EQUALS = 'eq'
    NOT_EQUALS = 'neq'
    IN_SET = 'in_set'
    NOT_IN_SET = 'not_in_set'
    IS_EMPTY = 'is_empty'
    IS_NOT_EMPTY = 'is_not_empty'
    AND = 'and'
    OR = 'or'

class Condition(BaseModel):
    field_code: str | None = None
    operator: ConditionOperator
    value: str | None = None
    values: list[str] | None = None
    conditions: list['Condition'] | None = None

Condition.model_rebuild()

class RuleType(str, Enum):
    EXPECT_VALUE = 'expect_value'
    EXPECT_EMPTY = 'expect_empty'
    CUSTOM = 'custom'

class FieldRule(BaseModel):
    field_code: str = Field(..., max_length=5)
    label: str
    rule_type: RuleType
    condition: Condition | None = None
    allowed_values: list[str] | None = None
    description: str | None = None

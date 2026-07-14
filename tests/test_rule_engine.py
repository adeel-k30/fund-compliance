from app.models.rules import FieldRule, RuleType
from app.services.rule_engine import RuleEngine

def make_rule(field_code, rule_type="expect_value", field_type=None,
              allowed_values=None, condition=None):
    return FieldRule.model_validate({
        "field_code": field_code,
        "label": "Test_Field",
        "field_type": field_type,
        "allowed_values": allowed_values,
        "rule_type": rule_type,
        "condition": condition,
        "description": "",
    })


# ---------- Mandatory fields ----------
def test_mandatory_field_missing_gives_one_issue():
    rule = make_rule("00050")  # always mandatory
    engine = RuleEngine([rule])

    result = engine.validate_row({}, row_index=0)  # 00050 is missing

    assert len(result.issues) == 1
    assert result.issues[0].rule_type == RuleType.EXPECT_VALUE


def test_mandatory_field_present_gives_no_issue():
    rule = make_rule("00050")
    engine = RuleEngine([rule])

    result = engine.validate_row({"00050": "2026-07-13"}, row_index=0)

    assert result.issues == []


# ---------- Conditional rules ----------
# This rule: 00085 is mandatory ONLY when 00060 is "S".
def conditional_rule():
    return make_rule("00085", condition={
        "operator": "eq",
        "field_code": "00060",
        "value": "S",
    })


def test_condition_not_met_gives_no_issue():
    engine = RuleEngine([conditional_rule()])

    # 00060 is "U", not "S", so the rule doesn't apply.
    result = engine.validate_row({"00060": "U"}, row_index=0)

    assert result.issues == []


def test_condition_met_but_field_missing_gives_issue():
    engine = RuleEngine([conditional_rule()])

    # 00060 is "S", so 00085 is now required, but it's missing.
    result = engine.validate_row({"00060": "S"}, row_index=0)

    assert len(result.issues) == 1


def test_condition_met_and_field_present_gives_no_issue():
    engine = RuleEngine([conditional_rule()])

    result = engine.validate_row({"00060": "S", "00085": "N"}, row_index=0)

    assert result.issues == []


# ---------- AND conditions ----------
# This rule applies only when 00006 is "Y" AND 00060 is "UM".
def and_rule():
    return make_rule("03010", condition={
        "operator": "and",
        "conditions": [
            {"operator": "eq", "field_code": "00006", "value": "Y"},
            {"operator": "eq", "field_code": "00060", "value": "UM"},
        ],
    })


def test_and_both_true_rule_applies():
    engine = RuleEngine([and_rule()])

    # Both parts true, 03010 missing -> issue.
    result = engine.validate_row({"00006": "Y", "00060": "UM"}, row_index=0)

    assert len(result.issues) == 1


def test_and_one_false_rule_does_not_apply():
    engine = RuleEngine([and_rule()])

    # 00006 is "N", so the AND is false -> rule skipped.
    result = engine.validate_row({"00006": "N", "00060": "UM"}, row_index=0)

    assert result.issues == []


# ---------- _is_empty ----------
def test_is_empty_true_for_empty_things():
    assert RuleEngine._is_empty(None) is True
    assert RuleEngine._is_empty("") is True
    assert RuleEngine._is_empty(float("nan")) is True


def test_is_empty_false_for_real_values():
    assert RuleEngine._is_empty("Y") is False
    assert RuleEngine._is_empty("0") is False
    assert RuleEngine._is_empty(0) is False


# ---------- Allowed values and field types ----------
def test_bad_allowed_value_gives_allowed_values_issue():
    rule = make_rule("00060", allowed_values=["S", "SF", "U", "N"])
    engine = RuleEngine([rule])

    result = engine.validate_row({"00060": "XYZ"}, row_index=0)

    issue_types = [i.rule_type for i in result.issues]
    assert RuleType.ALLOWED_VALUES in issue_types


def test_bad_isin_gives_format_issue():
    rule = make_rule("00010", field_type="isin")
    engine = RuleEngine([rule])

    result = engine.validate_row({"00010": "NOT-AN-ISIN"}, row_index=0)

    issue_types = [i.rule_type for i in result.issues]
    assert RuleType.FORMAT in issue_types


# ---------- Pass 1 clears bad values before Pass 2 ----------
def test_invalid_value_is_cleared_so_pass2_sees_it_as_empty():
    # 00060 must be in the allowed list.
    product_rule = make_rule("00060", allowed_values=["S", "SF", "U", "N"])
    # 00085 is mandatory when 00060 is "not empty".
    dependent_rule = make_rule("00085", condition={
        "operator": "is_not_empty",
        "field_code": "00060",
    })
    engine = RuleEngine([product_rule, dependent_rule])

    # 00060 = "XYZ" is invalid. Pass 1 clears it to None.
    # So in Pass 2, 00060 looks empty and the 00085 rule does NOT fire.
    result = engine.validate_row({"00060": "XYZ"}, row_index=0)

    fields_with_issues = [i.field_code for i in result.issues]
    assert "00085" not in fields_with_issues
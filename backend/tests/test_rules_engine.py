import pytest

from app.services.rules_engine import ELIGIBLE, NEEDS_INFO, NOT_ELIGIBLE, evaluate_rules


def make_rule(operator, value):
    return {"field": "value", "operator": operator, "value_json": value, "explanation_en": "test rule"}


@pytest.mark.parametrize(
    ("operator", "expected", "actual", "should_match"),
    [
        ("eq", "Maharashtra", "Maharashtra", True),
        ("eq", "Maharashtra", "Gujarat", False),
        ("neq", "ST", "General", True),
        ("neq", "ST", "ST", False),
        ("lt", 5, 2, True),
        ("lt", 5, 5, False),
        ("lte", 5, 5, True),
        ("lte", 5, 6, False),
        ("gt", 1, 2, True),
        ("gt", 2, 2, False),
        ("gte", 2, 2, True),
        ("gte", 3, 2, False),
        ("in", ["SC", "ST"], "SC", True),
        ("in", ["SC", "ST"], "General", False),
        ("contains", "farmer", "small farmer", True),
        ("contains", "farmer", "teacher", False),
        ("contains", "cotton", ["cotton", "onion"], True),
        ("exists", True, "present", True),
        ("exists", True, None, None),
    ],
)
def test_rule_operators(operator, expected, actual, should_match):
    result = evaluate_rules({"value": actual}, [make_rule(operator, expected)])
    if should_match is None:
        assert result["status"] == NEEDS_INFO
        assert result["reasoning"][0]["result"] == "unknown"
    elif should_match:
        assert result["status"] == ELIGIBLE
        assert result["reasoning"][0]["result"] == "matched"
    else:
        assert result["status"] == NOT_ELIGIBLE
        assert result["reasoning"][0]["result"] == "failed"


def test_missing_profile_value_is_unknown():
    result = evaluate_rules({}, [make_rule("eq", "Maharashtra")])
    assert result["status"] == NEEDS_INFO
    assert result["reasoning"][0]["result"] == "unknown"


def test_failure_takes_precedence_over_unknown():
    result = evaluate_rules(
        {"value": "Gujarat"},
        [make_rule("eq", "Maharashtra"), {"field": "age", "operator": "gte", "value_json": 18}],
    )
    assert result["status"] == NOT_ELIGIBLE


def test_all_rules_must_match_for_likely_eligible():
    result = evaluate_rules(
        {"value": "Maharashtra", "age": 31},
        [make_rule("eq", "Maharashtra"), {"field": "age", "operator": "gte", "value_json": 18}],
    )
    assert result["status"] == ELIGIBLE
    assert len(result["reasoning"]) == 2


def test_no_rules_needs_more_info():
    assert evaluate_rules({}, []) == {"status": NEEDS_INFO, "reasoning": []}


def test_explanation_uses_requested_language():
    rule = {"field": "value", "operator": "eq", "value_json": "yes", "explanation_en": "English", "explanation_mr": "मराठी"}
    result = evaluate_rules({"value": "yes"}, [rule], "mr")
    assert result["status"] == ELIGIBLE
    assert result["reasoning"][0]["explanation"] == "मराठी"


def test_unsupported_operator_is_rejected():
    with pytest.raises(ValueError, match="Unsupported scheme rule"):
        evaluate_rules({"value": 1}, [make_rule("approx", 1)])
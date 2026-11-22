from collections.abc import Iterable, Mapping
from typing import Any


ELIGIBLE = "Likely eligible"
NEEDS_INFO = "Maybe, needs more info"
NOT_ELIGIBLE = "Likely not eligible"

SUPPORTED_OPERATORS = {"eq", "neq", "lt", "lte", "gt", "gte", "in", "contains", "exists"}


def _read(rule: Mapping[str, Any] | object, key: str, default: Any = None) -> Any:
    if isinstance(rule, Mapping):
        return rule.get(key, default)
    return getattr(rule, key, default)


def _matches(actual: Any, operator: str, expected: Any) -> bool:
    if operator == "exists":
        return actual is not None
    if operator == "eq":
        return actual == expected
    if operator == "neq":
        return actual != expected
    if operator == "in":
        return isinstance(expected, (list, tuple, set)) and actual in expected
    if operator == "contains":
        if isinstance(actual, str) and isinstance(expected, str):
            return expected.casefold() in actual.casefold()
        if isinstance(actual, (list, tuple, set)):
            return expected in actual
        return False
    comparisons = {"lt": lambda: actual < expected, "lte": lambda: actual <= expected,
                   "gt": lambda: actual > expected, "gte": lambda: actual >= expected}
    try:
        return comparisons[operator]()
    except TypeError:
        return False


def evaluate_rules(profile: Mapping[str, Any] | object, rules: Iterable[Mapping[str, Any] | object], language: str = "en") -> dict[str, Any]:
    """Evaluate stored scheme rules without using a language model."""
    reasoning = []
    failures = 0
    unknowns = 0

    for rule in rules:
        field = _read(rule, "field")
        operator = _read(rule, "operator")
        if not isinstance(field, str) or operator not in SUPPORTED_OPERATORS:
            raise ValueError(f"Unsupported scheme rule: {field!r} {operator!r}")
        actual = profile.get(field) if isinstance(profile, Mapping) else getattr(profile, field, None)
        expected = _read(rule, "value_json")
        if operator == "exists" and expected is None:
            expected = True

        if actual is None:
            result = "unknown"
            unknowns += 1
        elif _matches(actual, operator, expected):
            result = "matched"
        else:
            result = "failed"
            failures += 1

        reasoning.append({
            "field": field,
            "operator": operator,
            "expected": expected,
            "actual": actual,
            "result": result,
            "explanation": _read(rule, f"explanation_{language}") or _read(rule, "explanation_en", ""),
        })

    if failures:
        status = NOT_ELIGIBLE
    elif unknowns or not reasoning:
        status = NEEDS_INFO
    else:
        status = ELIGIBLE
    return {"status": status, "reasoning": reasoning}
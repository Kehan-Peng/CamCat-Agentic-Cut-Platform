from typing import Any

from pydantic import BaseModel


class ReflectionResult(BaseModel):
    passed: bool
    issues: list[str]


def validate_grounding(final_answer: str | None, results: list[Any]) -> ReflectionResult:
    issues: list[str] = []

    if not final_answer or not final_answer.strip():
        issues.append("missing_final_answer")

    if not results:
        return ReflectionResult(passed=not issues, issues=issues)

    for result in results:
        if _missing_timestamp(result):
            _add_issue(issues, "missing_timestamp")
        if not _get_value(result, "evidence"):
            _add_issue(issues, "missing_evidence")
        if not str(_get_value(result, "reason") or "").strip():
            _add_issue(issues, "missing_reason")
        if final_answer and not _answer_completes_result(final_answer, result):
            _add_issue(issues, "incomplete_answer")

    return ReflectionResult(passed=not issues, issues=issues)


def _missing_timestamp(result: Any) -> bool:
    return _get_value(result, "start_time") is None or _get_value(result, "end_time") is None


def _answer_completes_result(final_answer: str, result: Any) -> bool:
    segment_id = _get_value(result, "segment_id")
    reason = str(_get_value(result, "reason") or "").strip()
    evidence_texts = [
        str(_get_value(evidence, "text") or "").strip()
        for evidence in (_get_value(result, "evidence") or [])
    ]
    return (
        (not segment_id or str(segment_id) in final_answer)
        and _answer_mentions_timestamp(final_answer, result)
        and (
            (reason and reason in final_answer)
            or any(text and text in final_answer for text in evidence_texts)
        )
    )


def _answer_mentions_timestamp(final_answer: str, result: Any) -> bool:
    start_time = _get_value(result, "start_time")
    end_time = _get_value(result, "end_time")
    if start_time is None or end_time is None:
        return False
    return str(start_time) in final_answer and str(end_time) in final_answer


def _add_issue(issues: list[str], issue: str) -> None:
    if issue not in issues:
        issues.append(issue)


def _get_value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)

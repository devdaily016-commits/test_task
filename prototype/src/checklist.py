from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from .schema import FIELD_LABELS, Extraction

ROOT = Path(__file__).resolve().parents[1]
CHECKLIST_PATH = ROOT / "checklists" / "l39240_lumbar_esi.yaml"


@dataclass(frozen=True)
class ItemResult:
    id: str
    label: str
    source: str
    letter: str
    status: str
    detail: str


@lru_cache(maxsize=1)
def load_checklist() -> dict:
    return yaml.safe_load(CHECKLIST_PATH.read_text())


def _value(extraction: Extraction, field: str):
    return getattr(extraction, field)


def _clause_ok(extraction: Extraction, clause: dict) -> bool:
    op = clause["op"]
    if op is True:
        op = "true"
    else:
        op = str(op)
    value = _value(extraction, clause["field"])
    if op == "present":
        return value is not None and str(value).strip() != ""
    if op == "nonempty":
        return isinstance(value, list) and len(value) > 0
    if op == "true":
        return value is True
    if op == "gte":
        if value is None:
            return False
        return float(value) >= float(clause["value"])
    if op == "in":
        if value is None or str(value).strip() == "":
            return False
        allowed = {str(item).lower() for item in clause["value"]}
        return str(value).lower() in allowed
    raise ValueError(f"Unknown rule op: {op}")


def _format_number(value: float) -> str:
    return f"{float(value):g}"


def _clause_detail(extraction: Extraction, clause: dict) -> str:
    label = FIELD_LABELS.get(clause["field"], clause["field"])
    value = _value(extraction, clause["field"])
    op = clause["op"]
    if op == "present":
        if value is None or str(value).strip() == "":
            return f"{label} is missing"
        return f"{label}: {value}"
    if op == "nonempty":
        if not value:
            return f"{label} is missing"
        return f"{label}: {', '.join(value)}"
    if op == "true":
        if value is True:
            return f"{label} is in the packet"
        return f"{label} is not documented"
    if op == "gte":
        need = _format_number(clause["value"])
        if value is None:
            return f"{label} is missing (needs at least {need})"
        got = _format_number(value)
        if _clause_ok(extraction, clause):
            return f"{label}: {got}"
        return f"{label}: {got} (needs at least {need})"
    if op == "in":
        if value is None or str(value).strip() == "":
            return f"{label} is missing"
        allowed = " or ".join(str(item) for item in clause["value"])
        if not _clause_ok(extraction, clause):
            return f"{label}: {value} (needs {allowed})"
        return f"{label}: {value}"
    return label


def _clauses(item: dict) -> list[dict]:
    if "all" in item:
        return item["all"]
    if "any" in item:
        return item["any"]
    raise ValueError(f"Checklist item {item['id']} needs all or any")


def _passed(extraction: Extraction, item: dict) -> tuple[bool, list[str]]:
    clauses = _clauses(item)
    if "all" in item:
        if all(_clause_ok(extraction, clause) for clause in clauses):
            return True, [clause["field"] for clause in clauses]
        return False, []
    driving = [clause["field"] for clause in clauses if _clause_ok(extraction, clause)]
    return bool(driving), driving


def _detail(extraction: Extraction, item: dict, passed: bool) -> str:
    clauses = _clauses(item)
    if "any" in item and not passed:
        primary = _clause_detail(extraction, clauses[0])
        exceptions = [
            FIELD_LABELS.get(clause["field"], clause["field"])
            for clause in clauses[1:]
            if not _clause_ok(extraction, clause)
        ]
        if exceptions:
            return primary + ". Exception not documented: " + ", ".join(exceptions)
        return primary
    if passed:
        chosen = [clause for clause in clauses if _clause_ok(extraction, clause)]
    else:
        chosen = [clause for clause in clauses if not _clause_ok(extraction, clause)]
    return ". ".join(_clause_detail(extraction, clause) for clause in chosen)


def _confidence(extraction: Extraction, field: str) -> float:
    return float(extraction.field_confidence.get(field, 1.0))


def evaluate(extraction: Extraction, checklist: dict | None = None) -> list[ItemResult]:
    checklist = checklist or load_checklist()
    threshold = float(checklist.get("review_confidence_below", 0.7))
    results: list[ItemResult] = []
    for item in checklist["items"]:
        source = item.get("source", checklist["policy_id"])
        when = item.get("when")
        if when is not None and not _clause_ok(extraction, when):
            results.append(
                ItemResult(
                    id=item["id"],
                    label=item["label"],
                    source=source,
                    letter=item["letter"],
                    status="not_applicable",
                    detail=item.get("when_skipped", "Does not apply to this request."),
                )
            )
            continue
        passed, driving = _passed(extraction, item)
        detail = _detail(extraction, item, passed)
        if not passed:
            status = "gap"
        else:
            low = [field for field in driving if _confidence(extraction, field) < threshold]
            if low:
                status = "needs_review"
                names = ", ".join(FIELD_LABELS.get(field, field) for field in low)
                detail = f"{detail}. Low confidence on {names}."
            else:
                status = "met"
        results.append(
            ItemResult(
                id=item["id"],
                label=item["label"],
                source=source,
                letter=item["letter"],
                status=status,
                detail=detail,
            )
        )
    return results


def verdict_of(items: list[ItemResult]) -> str:
    statuses = {item.status for item in items}
    if "gap" in statuses:
        return "incomplete"
    if "needs_review" in statuses:
        return "needs_review"
    return "complete"

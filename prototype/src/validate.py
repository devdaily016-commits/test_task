from __future__ import annotations

import re
from dataclasses import replace

from .checklist import ItemResult
from .npi import npi_is_valid
from .schema import Extraction

ICD10 = re.compile(r"^[A-TV-Z][0-9][0-9AB](?:\.[0-9A-TV-Z]{1,4})?$")
CPT = re.compile(r"^\d{5}$")


def _flag(items: list[ItemResult], item_id: str, sentence: str) -> list[ItemResult]:
    updated: list[ItemResult] = []
    for item in items:
        if item.id == item_id and item.status == "met":
            detail = f"{item.detail} {sentence}".strip()
            updated.append(replace(item, status="needs_review", detail=detail))
        else:
            updated.append(item)
    return updated


def apply_field_checks(
    items: list[ItemResult], extraction: Extraction
) -> tuple[list[ItemResult], list[str]]:
    """Code checks on values the model already extracted. A failure asks a person to look."""
    warnings: list[str] = []
    if extraction.provider_npi and not npi_is_valid(extraction.provider_npi):
        warnings.append(f"NPI {extraction.provider_npi} failed the check digit.")
        items = _flag(items, "requesting_provider", "NPI failed the check digit.")
    bad_codes = [code for code in extraction.icd10 if not ICD10.match(code)]
    if bad_codes:
        warnings.append(f"ICD-10 not in range: {', '.join(bad_codes)}.")
        items = _flag(items, "diagnosis", "An ICD-10 code is not in range.")
    if extraction.cpt and not CPT.match(extraction.cpt):
        warnings.append(f"CPT {extraction.cpt} is not 5 digits.")
        items = _flag(items, "requested_service", "CPT is not 5 digits.")
    return items, warnings

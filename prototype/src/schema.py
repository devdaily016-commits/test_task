from __future__ import annotations

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    page: int
    quote: str


class Extraction(BaseModel):
    member_name: str | None = None
    member_dob: str | None = None
    member_id: str | None = None
    provider_name: str | None = None
    provider_npi: str | None = None
    provider_fax: str | None = None
    cpt: str | None = None
    icd10: list[str] = Field(default_factory=list)
    laterality: str | None = None
    spinal_level: str | None = None
    is_repeat: bool = False
    pain_duration_weeks: float | None = None
    conservative_care_weeks: float | None = None
    conservative_care_description: str | None = None
    unable_to_tolerate_conservative_care: bool = False
    history_and_exam_present: bool = False
    baseline_pain_score: str | None = None
    baseline_function_score: str | None = None
    imaging_report_present: bool = False
    imaging_modality: str | None = None
    imaging_findings: str | None = None
    prior_relief_percent: float | None = None
    prior_relief_months: float | None = None
    herpes_zoster: bool = False
    field_confidence: dict[str, float] = Field(default_factory=dict)
    evidence: dict[str, list[Evidence]] = Field(default_factory=dict)


FIELD_LABELS: dict[str, str] = {
    "member_name": "Member name",
    "member_dob": "Date of birth",
    "member_id": "Member ID",
    "provider_name": "Provider",
    "provider_npi": "NPI",
    "provider_fax": "Fax",
    "cpt": "CPT",
    "icd10": "ICD-10",
    "laterality": "Laterality",
    "spinal_level": "Spinal level",
    "is_repeat": "Repeat injection",
    "pain_duration_weeks": "Pain duration (weeks)",
    "conservative_care_weeks": "Conservative care (weeks)",
    "conservative_care_description": "Conservative care",
    "unable_to_tolerate_conservative_care": "Unable to tolerate conservative care",
    "history_and_exam_present": "History and exam",
    "baseline_pain_score": "Pain score",
    "baseline_function_score": "Function score",
    "imaging_report_present": "Imaging report",
    "imaging_modality": "Modality",
    "imaging_findings": "Imaging findings",
    "prior_relief_percent": "Prior relief (%)",
    "prior_relief_months": "Prior relief (months)",
    "herpes_zoster": "Herpes zoster",
}

CONFIDENCE_FIELDS = [
    "member_name",
    "member_dob",
    "member_id",
    "provider_name",
    "provider_npi",
    "provider_fax",
    "cpt",
    "laterality",
    "spinal_level",
    "is_repeat",
    "pain_duration_weeks",
    "conservative_care_weeks",
    "history_and_exam_present",
    "baseline_pain_score",
    "baseline_function_score",
    "imaging_report_present",
    "imaging_modality",
    "prior_relief_percent",
    "prior_relief_months",
]


def high_confidence(overrides: dict[str, float] | None = None) -> dict[str, float]:
    scores = {name: 0.96 for name in CONFIDENCE_FIELDS}
    if overrides:
        scores.update(overrides)
    return scores

from __future__ import annotations

from dataclasses import dataclass, field

from .npi import make_npi
from .schema import Evidence, Extraction, high_confidence

CHEN_NPI = make_npi("124530001")
PATEL_NPI = make_npi("134567890")
BROOKS_NPI = make_npi("109876543")


@dataclass
class PacketSpec:
    stem: str
    title: str
    who: str
    blurb: str
    reference: str
    extraction: Extraction
    pages: list[list[str]]
    degrade: bool = False
    obscure_lines: dict[int, list[int]] = field(default_factory=dict)
    light_lines: dict[int, list[int]] = field(default_factory=dict)


def all_packets() -> list[PacketSpec]:
    return [incomplete_packet(), complete_packet(), degraded_packet()]


def packet_by_stem(stem: str) -> PacketSpec | None:
    for spec in all_packets():
        if spec.stem == stem:
            return spec
    return None


def _evidence(pages: list[list[str]], fields: dict[str, str]) -> dict[str, list[Evidence]]:
    found: dict[str, list[Evidence]] = {}
    for field_name, quote in fields.items():
        for number, lines in enumerate(pages, start=1):
            if quote in lines:
                found[field_name] = [Evidence(page=number, quote=quote)]
                break
        else:
            raise KeyError(f"{field_name} quote is not on a page: {quote}")
    return found


def incomplete_packet() -> PacketSpec:
    page1 = [
        "PRIOR AUTHORIZATION REQUEST",
        "Fax intake, lumbar epidural steroid injection",
        "",
        "Requesting provider: Avery Chen, MD",
        f"NPI: {CHEN_NPI}",
        "Fax: 555-010-0142",
        "Specialty: Pain medicine",
        "",
        "Member name: Jordan Hale",
        "Date of birth: 1978-04-12",
        "Member ID: SYN-100284",
        "",
        "Service: lumbar interlaminar epidural injection",
        "CPT: 62323",
        "Spinal level: L4-L5",
        "Laterality: Left",
        "Repeat injection: No",
        "Diagnosis: M54.16 Lumbar radiculopathy",
        "",
        "Attached: office note dated 2026-10-20.",
        "Imaging report: not included. MRI ordered.",
    ]
    page2 = [
        "OFFICE NOTE",
        "Date of visit: 2026-10-20",
        "Patient: Jordan Hale",
        "",
        "History: left leg pain began 2 weeks ago after lifting.",
        "No physical therapy has been started.",
        "No prescription anti-inflammatory is documented.",
        "Inability to tolerate conservative care: not described.",
        "",
        "Exam: positive straight-leg raise on the left, 40 degrees.",
        "Strength is 5/5. Sensation is intact.",
        "History, physical, and neurological exam are in this note.",
        "",
        "Assessment: left lumbar radiculopathy, M54.16.",
        "Plan: CPT 62323, left L4-L5 interlaminar injection.",
        "MRI was ordered. The report is not in this packet.",
        "No numeric pain score is recorded.",
        "No function score is recorded.",
    ]
    pages = [page1, page2]
    extraction = Extraction(
        member_name="Jordan Hale",
        member_dob="1978-04-12",
        member_id="SYN-100284",
        provider_name="Avery Chen, MD",
        provider_npi=CHEN_NPI,
        provider_fax="555-010-0142",
        cpt="62323",
        icd10=["M54.16"],
        laterality="Left",
        spinal_level="L4-L5",
        is_repeat=False,
        pain_duration_weeks=2,
        conservative_care_weeks=None,
        conservative_care_description=None,
        unable_to_tolerate_conservative_care=False,
        history_and_exam_present=True,
        baseline_pain_score=None,
        baseline_function_score=None,
        imaging_report_present=False,
        imaging_modality=None,
        imaging_findings=None,
        herpes_zoster=False,
        field_confidence=high_confidence(),
        evidence=_evidence(
            pages,
            {
                "member_name": "Member name: Jordan Hale",
                "member_dob": "Date of birth: 1978-04-12",
                "member_id": "Member ID: SYN-100284",
                "provider_name": "Requesting provider: Avery Chen, MD",
                "provider_npi": f"NPI: {CHEN_NPI}",
                "provider_fax": "Fax: 555-010-0142",
                "cpt": "CPT: 62323",
                "laterality": "Laterality: Left",
                "spinal_level": "Spinal level: L4-L5",
                "pain_duration_weeks": "History: left leg pain began 2 weeks ago after lifting.",
                "history_and_exam_present": "History, physical, and neurological exam are in this note.",
                "imaging_report_present": "MRI was ordered. The report is not in this packet.",
            },
        ),
    )
    return PacketSpec(
        stem="incomplete",
        title="Incomplete fax",
        who="Jordan Hale",
        blurb="Text is clean. Pain is 2 weeks, conservative care is absent, and the MRI report was never attached.",
        reference="PA-SYN-1842",
        extraction=extraction,
        pages=pages,
    )


def complete_packet() -> PacketSpec:
    page1 = [
        "PRIOR AUTHORIZATION REQUEST",
        "Portal upload, lumbar epidural steroid injection",
        "",
        "Requesting provider: Samir Patel, MD",
        f"NPI: {PATEL_NPI}",
        "Fax: 555-014-2208",
        "Specialty: Pain medicine",
        "",
        "Member name: Riley Okonkwo",
        "Date of birth: 1969-11-03",
        "Member ID: SYN-100291",
        "",
        "Service: lumbar transforaminal epidural injection",
        "CPT: 64483",
        "Spinal level: L5",
        "Laterality: Left",
        "Repeat injection: No",
        "Diagnosis: M51.16 Disc herniation with radiculopathy",
        "",
        "Attached: office note and MRI report.",
    ]
    page2 = [
        "OFFICE NOTE",
        "Date of visit: 2026-10-18",
        "Patient: Riley Okonkwo",
        "",
        "History: left leg pain for 8 weeks, into the foot.",
        "Care: naproxen plus physical therapy for 6 weeks.",
        "Those 6 weeks did not produce meaningful relief.",
        "Baseline pain score: NRS 8/10.",
        "Baseline function score: ODI 46.",
        "",
        "Exam: positive left straight-leg raise.",
        "Decreased sensation on the dorsum of the left foot.",
        "History, physical, and neurological exam are in this note.",
        "",
        "Assessment: left L5 radiculopathy, M51.16.",
        "Plan: initial CPT 64483, left L5 transforaminal injection.",
        "This is not a repeat injection.",
    ]
    page3 = [
        "IMAGING REPORT",
        "Modality: MRI lumbar spine without contrast",
        "Date: 2026-09-02",
        "Patient: Riley Okonkwo",
        "",
        "Findings: left paracentral L4-L5 herniation.",
        "The herniation contacts the traversing L5 nerve root.",
        "Moderate left foraminal stenosis at L4-L5.",
        "Concordant with the left L5 radicular exam.",
    ]
    pages = [page1, page2, page3]
    extraction = Extraction(
        member_name="Riley Okonkwo",
        member_dob="1969-11-03",
        member_id="SYN-100291",
        provider_name="Samir Patel, MD",
        provider_npi=PATEL_NPI,
        provider_fax="555-014-2208",
        cpt="64483",
        icd10=["M51.16"],
        laterality="Left",
        spinal_level="L5",
        is_repeat=False,
        pain_duration_weeks=8,
        conservative_care_weeks=6,
        conservative_care_description="Naproxen plus physical therapy for 6 weeks, without meaningful relief.",
        unable_to_tolerate_conservative_care=False,
        history_and_exam_present=True,
        baseline_pain_score="NRS 8/10",
        baseline_function_score="ODI 46",
        imaging_report_present=True,
        imaging_modality="MRI",
        imaging_findings="Left paracentral L4-L5 herniation contacting the traversing L5 nerve root.",
        herpes_zoster=False,
        field_confidence=high_confidence(),
        evidence=_evidence(
            pages,
            {
                "member_name": "Member name: Riley Okonkwo",
                "member_id": "Member ID: SYN-100291",
                "provider_name": "Requesting provider: Samir Patel, MD",
                "cpt": "CPT: 64483",
                "pain_duration_weeks": "History: left leg pain for 8 weeks, into the foot.",
                "conservative_care_weeks": "Care: naproxen plus physical therapy for 6 weeks.",
                "baseline_pain_score": "Baseline pain score: NRS 8/10.",
                "baseline_function_score": "Baseline function score: ODI 46.",
                "history_and_exam_present": "History, physical, and neurological exam are in this note.",
                "imaging_modality": "Modality: MRI lumbar spine without contrast",
                "imaging_findings": "Findings: left paracentral L4-L5 herniation.",
            },
        ),
    )
    return PacketSpec(
        stem="complete",
        title="Complete packet",
        who="Riley Okonkwo",
        blurb="Initial left L5 injection. Eight weeks of pain, six weeks of care, and the MRI report is in the packet.",
        reference="PA-SYN-1904",
        extraction=extraction,
        pages=pages,
    )


def degraded_packet() -> PacketSpec:
    page1 = [
        "PRIOR AUTHORIZATION REQUEST",
        "Fax intake, lumbar epidural steroid injection",
        "",
        "Requesting provider: Lena Brooks, MD",
        f"NPI: {BROOKS_NPI}",
        "Fax: 555-016-4410",
        "Specialty: Pain medicine",
        "",
        "Member name: Morgan Ellis",
        "Date of birth: 1958-06-21",
        "Member ID: SYN-100307",
        "",
        "Service: lumbar interlaminar epidural injection",
        "CPT: 62323",
        "Spinal level: L4-L5",
        "Laterality: Left",
        "Repeat injection: No",
        "Diagnosis: M51.16 Disc herniation with radiculopathy",
    ]
    page2 = [
        "OFFICE NOTE",
        "Date of visit: 2026-10-22",
        "Patient: Morgan Ellis",
        "",
        "History: left leg pain for 8 weeks, into the foot.",
        "Care: naproxen plus physical therapy for 6 weeks.",
        "Those 6 weeks did not produce meaningful relief.",
        "Baseline pain score: NRS 7/10.",
        "Baseline function score: ODI 38.",
        "",
        "Exam: positive left straight-leg raise.",
        "Decreased sensation on the dorsum of the left foot.",
        "History, physical, and neurological exam are in this note.",
        "",
        "Assessment: left L5 radiculopathy, M51.16.",
        "Plan: initial CPT 62323, left L4-L5 interlaminar injection.",
    ]
    page3 = [
        "IMAGING REPORT",
        "Modality: MRI lumbar spine without contrast",
        "Date: 2026-09-12",
        "Patient: Morgan Ellis",
        "Findings: left paracentral L4-L5 herniation.",
        "The herniation contacts the traversing L5 nerve root.",
        "This page is the imaging report.",
    ]
    pages = [page1, page2, page3]
    extraction = Extraction(
        member_name="Morgan Ellis",
        member_dob="1958-06-21",
        member_id=None,
        provider_name="Lena Brooks, MD",
        provider_npi=BROOKS_NPI,
        provider_fax="555-016-4410",
        cpt="62323",
        icd10=["M51.16"],
        laterality="Left",
        spinal_level="L4-L5",
        is_repeat=False,
        pain_duration_weeks=8,
        conservative_care_weeks=6,
        conservative_care_description="Naproxen plus physical therapy for 6 weeks, without meaningful relief.",
        unable_to_tolerate_conservative_care=False,
        history_and_exam_present=True,
        baseline_pain_score="NRS 7/10",
        baseline_function_score="ODI 38",
        imaging_report_present=False,
        imaging_modality=None,
        imaging_findings=None,
        herpes_zoster=False,
        field_confidence=high_confidence(
            {
                "member_id": 0.33,
                "provider_fax": 0.58,
                "imaging_report_present": 0.40,
            }
        ),
        evidence=_evidence(
            pages,
            {
                "member_name": "Member name: Morgan Ellis",
                "member_dob": "Date of birth: 1958-06-21",
                "provider_name": "Requesting provider: Lena Brooks, MD",
                "provider_fax": "Fax: 555-016-4410",
                "cpt": "CPT: 62323",
                "pain_duration_weeks": "History: left leg pain for 8 weeks, into the foot.",
                "conservative_care_weeks": "Care: naproxen plus physical therapy for 6 weeks.",
                "baseline_pain_score": "Baseline pain score: NRS 7/10.",
                "history_and_exam_present": "History, physical, and neurological exam are in this note.",
            },
        ),
    )
    member_line = page1.index("Member ID: SYN-100307")
    fax_line = page1.index("Fax: 555-016-4410")
    return PacketSpec(
        stem="degraded",
        title="Degraded fax",
        who="Morgan Ellis",
        blurb="No text layer. The member ID is covered, the imaging page cannot be read, and the fax number is faint.",
        reference="PA-SYN-2031",
        extraction=extraction,
        pages=pages,
        degrade=True,
        obscure_lines={0: [member_line], 2: list(range(1, len(page3)))},
        light_lines={0: [fax_line]},
    )

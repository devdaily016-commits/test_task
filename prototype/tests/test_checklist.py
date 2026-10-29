from datetime import date

from src.checklist import evaluate, verdict_of
from src.letter import render_letter
from src.npi import make_npi, npi_is_valid
from src.packets import all_packets, complete_packet, degraded_packet, incomplete_packet
from src.schema import Extraction
from src.validate import apply_field_checks


def _statuses(extraction: Extraction) -> dict[str, str]:
    return {item.id: item.status for item in evaluate(extraction)}


def test_published_npi_example():
    assert npi_is_valid("1234567893")


def test_generated_npis_pass_check_digit():
    for base in ("124530001", "134567890", "109876543"):
        npi = make_npi(base)
        assert npi_is_valid(npi)
        assert not npi_is_valid(npi[:-1] + ("0" if npi[-1] != "0" else "1"))


def test_incomplete_packet_gaps():
    items = evaluate(incomplete_packet().extraction)
    status = {item.id: item.status for item in items}
    assert status["pain_duration"] == "gap"
    assert status["conservative_care"] == "gap"
    assert status["imaging"] == "gap"
    assert status["baseline_score"] == "gap"
    assert status["member_identity"] == "met"
    assert status["history_exam"] == "met"
    assert status["repeat_relief"] == "not_applicable"
    assert verdict_of(items) == "incomplete"
    pain = next(item for item in items if item.id == "pain_duration")
    assert "2" in pain.detail
    assert "4" in pain.detail


def test_complete_packet_is_clear():
    spec = complete_packet()
    items = evaluate(spec.extraction)
    assert verdict_of(items) == "complete"
    assert all(item.status in {"met", "not_applicable"} for item in items)
    assert render_letter(spec.extraction, items, spec.reference, date(2026, 10, 28)) is None


def test_degraded_packet_asks_for_id_and_imaging():
    spec = degraded_packet()
    items = evaluate(spec.extraction)
    status = {item.id: item.status for item in items}
    assert status["member_identity"] == "gap"
    assert status["imaging"] == "gap"
    assert status["requesting_provider"] == "needs_review"
    assert status["pain_duration"] == "met"
    assert verdict_of(items) == "incomplete"
    letter = render_letter(spec.extraction, items, spec.reference, date(2026, 10, 28))
    assert letter is not None
    assert "member ID" in letter
    assert "MRI or CT" in letter
    assert "fax number" in letter.lower() or "Fax" in letter
    assert "Coverage has not been decided" in letter
    assert "October 28, 2026" in letter


def test_repeat_rule_applies_only_when_flagged():
    extraction = complete_packet().extraction.model_copy(update={"is_repeat": True})
    status = _statuses(extraction)
    assert status["repeat_relief"] == "gap"
    healed = extraction.model_copy(
        update={"prior_relief_percent": 50, "prior_relief_months": 3}
    )
    assert _statuses(healed)["repeat_relief"] == "met"


def test_low_confidence_asks_for_confirmation_without_a_letter():
    extraction = complete_packet().extraction.model_copy(deep=True)
    extraction.field_confidence["member_name"] = 0.42
    items = evaluate(extraction)
    status = {item.id: item.status for item in items}
    assert status["member_identity"] == "needs_review"
    assert verdict_of(items) == "needs_review"
    assert render_letter(extraction, items, "PA-SYN-1904") is None


def test_bad_npi_is_a_review_flag_not_a_new_policy():
    extraction = complete_packet().extraction.model_copy(update={"provider_npi": "1245300010"})
    items, warnings = apply_field_checks(evaluate(extraction), extraction)
    assert warnings
    assert next(item for item in items if item.id == "requesting_provider").status == "needs_review"


def test_every_quote_is_on_the_named_page():
    for spec in all_packets():
        for evidences in spec.extraction.evidence.values():
            for evidence in evidences:
                assert evidence.quote in spec.pages[evidence.page - 1]


def test_lines_fit_the_fax_page():
    for spec in all_packets():
        for lines in spec.pages:
            for line in lines:
                assert len(line) <= 78

from pathlib import Path

from src.cost import money
from src.packets import all_packets
from src.pipeline import review_packet

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {"incomplete": "incomplete", "complete": "complete", "degraded": "incomplete"}


def test_sample_pdfs_route_and_verdict():
    costs = {}
    for spec in all_packets():
        path = ROOT / "samples" / f"{spec.stem}.pdf"
        assert path.exists(), "Run python generate_packets.py"
        review = review_packet(path, mode="fixture")
        assert review.verdict == EXPECTED[spec.stem]
        assert review.reference == spec.reference
        if spec.degrade:
            assert review.route == "sonnet_vision"
            assert all(page.quality == "poor" for page in review.pages)
        else:
            assert review.route == "haiku_text"
            assert all(page.quality == "good" for page in review.pages)
        costs[spec.stem] = review.cost.usd
        assert review.cost.kind == "estimated"
        assert review.cost.usd > 0
    assert costs["degraded"] > costs["complete"]
    assert costs["degraded"] > costs["incomplete"]


def test_incomplete_letter_names_the_gaps():
    review = review_packet(ROOT / "samples" / "incomplete.pdf")
    assert review.letter is not None
    assert "at least 4 weeks" in review.letter
    assert "noninvasive care" in review.letter
    assert "baseline pain or function score" in review.letter
    assert "Jordan Hale" in review.letter
    assert "PA-SYN-1842" in review.letter


def test_money_format_keeps_small_estimates_visible():
    assert money(0.0006) == "$0.0006"
    assert money(0.017) == "$0.017"
    assert money(300) == "$300"

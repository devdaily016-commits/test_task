from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from .checklist import ItemResult, evaluate, load_checklist, verdict_of
from .cost import Cost, estimate_cost
from .extract import live_extract, load_fixture
from .letter import render_letter
from .packets import packet_by_stem
from .parse import Page, parse_pdf, route_for
from .schema import Extraction
from .validate import apply_field_checks

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Review:
    source_name: str
    mode: str
    route: str
    pages: list[Page]
    extraction: Extraction
    items: list[ItemResult]
    verdict: str
    letter: str | None
    warnings: list[str]
    cost: Cost
    reference: str
    blurb: str
    checklist_note: str


def review_packet(path: Path, mode: str = "fixture") -> Review:
    path = Path(path)
    pages = parse_pdf(path)
    route = route_for(pages)
    spec = packet_by_stem(path.stem)
    reference = spec.reference if spec else "PA-SYN-UPLOAD"
    blurb = spec.blurb if spec else "Uploaded PDF."
    if mode == "fixture":
        extraction = load_fixture(path.stem)
        cost = estimate_cost(pages, route)
    elif mode == "live":
        extraction, cost = live_extract(pages, route)
    else:
        raise ValueError(f"Unknown mode: {mode}")
    items = evaluate(extraction)
    items, warnings = apply_field_checks(items, extraction)
    verdict = verdict_of(items)
    letter = render_letter(extraction, items, reference)
    note = str(load_checklist().get("note", "")).strip()
    return Review(
        source_name=path.name,
        mode=mode,
        route=route,
        pages=pages,
        extraction=extraction,
        items=items,
        verdict=verdict,
        letter=letter,
        warnings=warnings,
        cost=cost,
        reference=reference,
        blurb=blurb,
        checklist_note=note,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Review one synthetic prior-auth PDF.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    review = review_packet(args.pdf, mode="live" if args.live else "fixture")
    print(f"{review.source_name}  {review.verdict}  route={review.route}  {review.cost.detail}")
    for item in review.items:
        print(f"  {item.status:16} {item.label}")
        print(f"    {item.detail}")
    if review.letter:
        print()
        print(review.letter)


if __name__ == "__main__":
    main()

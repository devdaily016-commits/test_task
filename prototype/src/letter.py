from __future__ import annotations

from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .checklist import ItemResult
from .schema import Extraction

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"


def render_letter(
    extraction: Extraction,
    items: list[ItemResult],
    reference: str,
    today: date | None = None,
) -> str | None:
    gaps = [item for item in items if item.status == "gap"]
    if not gaps:
        return None
    reviews = [item for item in items if item.status == "needs_review"]
    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=select_autoescape(disabled_extensions=("j2",), default=False),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("missing_info.txt.j2")
    written = today or date.today()
    return template.render(
        today=f"{written.strftime('%B')} {written.day}, {written.year}",
        provider_name=extraction.provider_name,
        provider_fax=extraction.provider_fax,
        member_name=extraction.member_name,
        member_id=extraction.member_id,
        cpt=extraction.cpt,
        reference=reference,
        gaps=gaps,
        reviews=reviews,
    ).strip() + "\n"

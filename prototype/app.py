"""Fax check. The answer is at the top. The packet, the fields, and the cost are further down."""

from __future__ import annotations

import html
import tempfile
from pathlib import Path

import streamlit as st

from src.checklist import load_checklist
from src.cost import MONTHLY_HIGH_USD, MONTHLY_LOW_USD, PLANNING_BLEND_USD, money
from src.extract import load_api_key
from src.packets import all_packets
from src.pipeline import Review, review_packet
from src.schema import FIELD_LABELS, Extraction

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT / "samples"

GROUPS = [
    ("Member", ["member_name", "member_dob", "member_id"]),
    ("Provider", ["provider_name", "provider_npi", "provider_fax"]),
    ("Service", ["cpt", "icd10", "spinal_level", "laterality", "is_repeat"]),
    (
        "Clinical",
        [
            "pain_duration_weeks",
            "conservative_care_weeks",
            "conservative_care_description",
            "baseline_pain_score",
            "baseline_function_score",
            "history_and_exam_present",
            "imaging_report_present",
            "imaging_modality",
            "imaging_findings",
        ],
    ),
]
WIDE = {"conservative_care_description", "imaging_findings"}
STATUS_LABEL = {
    "met": "In the packet",
    "gap": "Missing",
    "needs_review": "Confirm",
    "not_applicable": "Does not apply",
}
PLAIN_LABEL = {
    "laterality": "Side",
    "imaging_modality": "Imaging type",
}
PACKET_HINT = {
    "incomplete": "missing items",
    "complete": "ready",
    "degraded": "hard to read",
}

STYLES = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Schibsted+Grotesk:wght@500;700&family=Source+Serif+4:opsz,wght@8..60,480;8..60,600&display=swap');
html, body, [class*="css"] {
  font-family: "Schibsted Grotesk", "Avenir Next", "Segoe UI", sans-serif;
}
div[data-testid="stDecoration"], div[data-testid="stToolbar"] { display: none; }
section[data-testid="stSidebar"] { border-right: 1px solid #D5DEE3; }
.block-container { padding-top: 1.5rem; padding-bottom: 4rem; max-width: 46rem; }
section[data-testid="stSidebar"] .block-container { max-width: none; padding-top: 1.4rem; }
.side-kicker {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: #1A2830;
}
.side-note { margin: 0.2rem 0 0.7rem; color: #5C6E78; font-size: 0.84rem; line-height: 1.4; }
.hero { padding-bottom: 1.6rem; }
.kicker {
  margin: 0;
  color: #1E4D6B;
  font-size: 0.92rem;
}
.hero-row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
  margin-top: 0.35rem;
}
h1.name {
  margin: 0;
  font-weight: 700;
  font-size: 2.7rem;
  letter-spacing: -0.035em;
  line-height: 1.02;
  color: #1A2830;
}
.status {
  margin: 0 0 0.35rem;
  padding-left: 0.7rem;
  border-left: 4px solid currentColor;
  font-weight: 700;
  font-size: 1rem;
  line-height: 1.2;
}
.status.incomplete { color: #9E2B22; }
.status.complete { color: #1B5C3E; }
.status.needs_review { color: #8A5A0E; }
.lead {
  margin: 1.15rem 0 0;
  max-width: 34rem;
  color: #1A2830;
  font-size: 1.28rem;
  font-weight: 500;
  line-height: 1.35;
}
.next { margin: 0.45rem 0 0; max-width: 34rem; color: #3C4E58; font-size: 1.02rem; line-height: 1.45; }
.tier { margin-top: 0.4rem; padding-top: 1.5rem; border-top: 1px solid #D5DEE3; }
.tier h2 {
  margin: 0;
  color: #1A2830;
  font-size: 1.2rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}
.help { margin: 0.3rem 0 0; max-width: 34rem; color: #5C6E78; font-size: 0.95rem; line-height: 1.45; }
.rows { margin-top: 0.85rem; }
.row {
  display: grid;
  grid-template-columns: 6.4rem 1fr;
  gap: 0.2rem 0.85rem;
  padding: 0.7rem 0;
  border-top: 1px solid #E1E8EC;
}
.tag { font-size: 0.84rem; font-weight: 700; }
.row.gap .tag { color: #9E2B22; }
.row.needs_review .tag { color: #8A5A0E; }
.row.met .tag { color: #1B5C3E; }
.row.not_applicable .tag { color: #8A9AA3; }
.row strong { color: #1A2830; font-weight: 700; }
.detail { margin: 0.15rem 0 0; color: #3C4E58; font-size: 0.92rem; line-height: 1.4; }
.src { margin: 0.2rem 0 0; color: #8A9AA3; font-size: 0.78rem; }
.note {
  margin: 0.85rem 0 0;
  color: #8A5A0E;
  font-size: 0.95rem;
}
.letter-label { margin: 1.15rem 0 0.4rem; color: #1E4D6B; font-size: 0.92rem; font-weight: 700; }
.letter {
  margin: 0;
  padding: 1.15rem 1.3rem 1.25rem;
  border: 1px solid #D5DEE3;
  background: #F7FBFC;
  color: #1A2830;
  font-family: "Source Serif 4", Georgia, serif !important;
  font-size: 1.02rem;
  line-height: 1.5;
  white-space: pre-wrap;
}
[data-testid="stFileUploader"] small,
[data-testid="stFileUploaderDropzoneInstructions"] div:last-child {
  display: none;
}
.fieldgrid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.85rem 1.4rem; margin-top: 0.9rem; }
.group-label {
  grid-column: 1 / -1;
  margin: 0.7rem 0 0;
  color: #1E4D6B;
  font-size: 0.92rem;
  font-weight: 700;
}
.group-label:first-child { margin-top: 0; }
.field .k { color: #5C6E78; font-size: 0.8rem; }
.field .v {
  color: #1A2830;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 0.95rem;
}
.field .v.missing { color: #8A9AA3; }
.field .q { color: #8A9AA3; font-size: 0.78rem; line-height: 1.35; }
.field .q.low { color: #8A5A0E; font-weight: 700; }
.field.wide { grid-column: 1 / -1; }
.cost { display: flex; flex-wrap: wrap; gap: 1.4rem 2rem; margin-top: 0.9rem; }
.cost b {
  display: block;
  color: #1A2830;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 1rem;
  font-weight: 500;
}
.cost span { color: #5C6E78; font-size: 0.8rem; }
.fine { margin: 0.7rem 0 0; max-width: 38rem; color: #5C6E78; font-size: 0.84rem; line-height: 1.45; }
div[data-testid="stImage"] img { border: 1px solid #D5DEE3; }
@media (max-width: 800px) {
  h1.name { font-size: 2.15rem; }
  .fieldgrid, .row { grid-template-columns: 1fr; }
}
</style>
"""


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _display(field: str, extraction: Extraction) -> str | None:
    value = getattr(extraction, field)
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, list):
        return ", ".join(value) if value else None
    if isinstance(value, float):
        return f"{value:g}"
    if value is None or str(value).strip() == "":
        return None
    return str(value)


def _skip_field(field: str, extraction: Extraction) -> bool:
    if field == "conservative_care_description" and not extraction.conservative_care_description:
        return True
    if field == "imaging_findings" and not extraction.imaging_findings:
        return True
    return False


def _fields_html(extraction: Extraction) -> str:
    blocks = ['<div class="fieldgrid">']
    for group, fields in GROUPS:
        blocks.append(f'<div class="group-label">{_esc(group)}</div>')
        for field in fields:
            if _skip_field(field, extraction):
                continue
            shown = _display(field, extraction)
            missing = shown is None
            value_html = "—" if missing else _esc(shown)
            value_class = "v missing" if missing else "v"
            confidence = extraction.field_confidence.get(field)
            quote = ""
            evidence = extraction.evidence.get(field) or []
            if evidence:
                text = evidence[0].quote
                if len(text) > 96:
                    text = text[:93] + "…"
                quote = f"Page {evidence[0].page}: “{text}”"
            low = confidence is not None and confidence < 0.7
            bits = []
            if low:
                bits.append('<span class="q low">Confirm</span>')
            if quote:
                bits.append(f'<span class="q">{_esc(quote)}</span>')
            meta = " · ".join(bits)
            wide = " wide" if field in WIDE else ""
            label = PLAIN_LABEL.get(field, FIELD_LABELS[field])
            blocks.append(
                f'<div class="field{wide}"><div class="k">{_esc(label)}</div>'
                f'<div class="{value_class}">{value_html}</div>'
                f'<div class="q">{meta}</div></div>'
            )
    blocks.append("</div>")
    return "".join(blocks)


def _rows_html(items: list, with_source: bool, with_detail: bool) -> str:
    rows = []
    for item in items:
        detail = f'<p class="detail">{_esc(item.detail)}</p>' if with_detail else ""
        source = f'<p class="src">{_esc(item.source)}</p>' if with_source else ""
        rows.append(
            f'<div class="row {item.status}">'
            f'<div class="tag">{_esc(STATUS_LABEL[item.status])}</div>'
            f"<div><strong>{_esc(item.label)}</strong>{detail}{source}</div></div>"
        )
    return "".join(rows)


def _hero_copy(review: Review) -> tuple[str, str, str, str]:
    gaps = [item for item in review.items if item.status == "gap"]
    reviews = [item for item in review.items if item.status == "needs_review"]
    name = review.extraction.member_name or "This fax"
    if review.verdict == "complete":
        return (
            name,
            "Ready for a nurse",
            "Everything this checklist asks for is in the packet.",
            "Nothing goes back to the provider. A nurse still decides whether the injection is medically necessary.",
        )
    if gaps and reviews:
        return (
            name,
            "Ask the provider",
            f"{_count(len(gaps))} missing, and {_count(len(reviews))} to confirm.",
            "Send the letter below, and confirm the marked fields. Coverage is not decided on this screen.",
        )
    if gaps:
        return (
            name,
            "Ask the provider",
            f"{_count(len(gaps))} missing from this fax.",
            "Send the letter below. A nurse does not see this packet until those items come back.",
        )
    return (
        name,
        "Confirm first",
        f"{_count(len(reviews))} to confirm before this moves on.",
        "Check the marked fields, then the packet can move on. Coverage is not decided here.",
    )


def _count(n: int) -> str:
    word = "thing" if n == 1 else "things"
    return f"{n} {word}"


def _how_read(review: Review) -> str:
    poor = [str(page.number) for page in review.pages if page.quality == "poor"]
    if review.mode == "live":
        if poor:
            return f"Claude read pages {', '.join(poor)} as images, because those pages have no text."
        return "Claude read the text already in the PDF."
    if poor:
        return (
            f"Saved reading. In production, pages {', '.join(poor)} would be read as images "
            "because they have no text."
        )
    return "Saved reading. The text is already in the PDF, so no page image is needed."


def _show(fragment: str) -> None:
    st.markdown(fragment, unsafe_allow_html=True)


def _render(review: Review) -> None:
    name, status, lead, nxt = _hero_copy(review)
    _show(
        '<header class="hero">'
        f'<p class="kicker">Lumbar injection · {_esc(review.reference)}</p>'
        '<div class="hero-row">'
        f'<h1 class="name">{_esc(name)}</h1>'
        f'<p class="status {review.verdict}">{_esc(status)}</p>'
        "</div>"
        f'<p class="lead">{_esc(lead)}</p>'
        f'<p class="next">{_esc(nxt)}</p>'
        "</header>"
    )

    attention = [item for item in review.items if item.status in {"gap", "needs_review"}]
    action = ['<section class="tier"><h2>What to do</h2>']
    if attention:
        action.append(f'<div class="rows">{_rows_html(attention, with_source=False, with_detail=False)}</div>')
    else:
        action.append(
            '<p class="help">No letter. The packet has what this checklist asks for.</p>'
        )
    for warning in review.warnings:
        action.append(f'<p class="note">Look at this: {_esc(warning)}</p>')
    if review.letter:
        action.append(
            '<p class="letter-label">Letter to the provider</p>'
            f'<div class="letter">{_esc(review.letter)}</div>'
        )
    action.append("</section>")
    _show("".join(action))

    _show(
        '<section class="tier"><h2>The fax</h2>'
        '<p class="help">Use the page to check a field against what was sent.</p></section>'
    )
    labels = [f"Page {page.number}" for page in review.pages]
    selected = st.radio("Page", labels, horizontal=True, label_visibility="collapsed")
    page = review.pages[labels.index(selected)]
    st.image(page.png, width="stretch")
    if page.quality == "good":
        st.caption(f"Page {page.number} of {len(review.pages)}. The text on this page can be read.")
    else:
        st.caption(
            f"Page {page.number} of {len(review.pages)}. This page is an image only, so compare it by eye."
        )

    _show(
        '<section class="tier"><h2>What we read</h2>'
        '<p class="help">Every field taken from the fax. Confirm means a person should check it.</p>'
        f"{_fields_html(review.extraction)}</section>"
    )
    note = str(load_checklist().get("note", "")).strip()
    _show(
        '<section class="tier"><h2>The full checklist</h2>'
        '<p class="help">Includes items already in the packet. This checks completeness, not coverage.</p>'
        f'<div class="rows">{_rows_html(review.items, with_source=True, with_detail=True)}</div>'
        f'<p class="fine">{_esc(note)}</p></section>'
    )

    kind = "measured" if review.cost.kind == "measured" else "estimated"
    _show(
        '<section class="tier"><h2>What this cost</h2>'
        '<p class="help">This sample is short. The monthly range is a planning estimate for a 15-page fax.</p>'
        '<div class="cost">'
        f"<div><b>{_esc(money(review.cost.usd))}</b><span>This fax, {kind}</span></div>"
        f"<div><b>{_esc(money(PLANNING_BLEND_USD))}</b><span>Typical request</span></div>"
        f"<div><b>${MONTHLY_LOW_USD:,}–${MONTHLY_HIGH_USD:,}</b><span>15,000 requests a month</span></div>"
        "</div>"
        f'<p class="fine">{_esc(_how_read(review))} {_esc(review.cost.detail)}.</p>'
        '<p class="fine">Amazon Bedrock list prices, October 2026. Clean pages use a smaller model '
        "($0.11 / $0.55 per million tokens). Pages with no text use a vision model ($2.20 / $11). "
        "About one in five production faxes needs the vision model.</p></section>"
    )


def _selected_pdf() -> tuple[Path, str]:
    packets = all_packets()
    labels = {
        f"{spec.who} · {PACKET_HINT.get(spec.stem, spec.title)}": spec for spec in packets
    }
    with st.sidebar:
        st.markdown('<p class="side-kicker">Which fax</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="side-note">Three samples. Not real patients.</p>',
            unsafe_allow_html=True,
        )
        picked = st.radio("Which fax", list(labels), label_visibility="collapsed")
        st.markdown('<p class="side-kicker">How to read it</p>', unsafe_allow_html=True)
        mode_label = st.radio("How to read it", ["Saved reading", "Ask Claude"], label_visibility="collapsed")
        st.markdown('<p class="side-note">Saved reading is instant. Ask Claude sends this sample and costs a few cents.</p>', unsafe_allow_html=True)
        st.markdown('<p class="side-kicker">Your own file</p>', unsafe_allow_html=True)
        upload = st.file_uploader("PDF", type=["pdf"], label_visibility="collapsed")
        st.markdown(
            '<p class="side-note">Synthetic files only.</p>',
            unsafe_allow_html=True,
        )
    if upload is not None:
        destination = Path(tempfile.gettempdir()) / "synthetic-upload.pdf"
        destination.write_bytes(upload.getvalue())
        return destination, "live"
    spec = labels[picked]
    return SAMPLES / f"{spec.stem}.pdf", "live" if mode_label == "Ask Claude" else "fixture"


def _live_prompt() -> bool:
    _show(
        '<header class="hero">'
        '<p class="kicker">Lumbar injection</p>'
        '<h1 class="name">Read this fax</h1>'
        '<p class="lead">This sends the sample to Claude.</p>'
        '<p class="next">It costs a few cents. Do not use a real patient file.</p>'
        "</header>"
    )
    return st.button("Read this fax", type="primary")


def main() -> None:
    st.set_page_config(page_title="Fax check", layout="centered")
    st.markdown(STYLES, unsafe_allow_html=True)
    path, mode = _selected_pdf()
    if not path.exists():
        st.error("Sample files are missing. From the prototype folder, run python generate_packets.py.")
        return
    if mode == "live" and not load_api_key():
        st.warning("No API key is set. Choose Saved reading, or add ANTHROPIC_API_KEY to prototype/.env.")
        if path.name == "synthetic-upload.pdf":
            return
        mode = "fixture"
    if mode == "live" and not _live_prompt():
        return
    try:
        review = review_packet(path, mode=mode)
    except Exception as exc:
        st.error(str(exc))
        return
    _render(review)


main()

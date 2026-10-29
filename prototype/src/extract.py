from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv

from .cost import Cost, estimate_cost, measured_cost
from .packets import packet_by_stem
from .parse import Page
from .schema import Extraction

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"

HAIKU_MODEL = "anthropic/claude-haiku-5-5"
SONNET_MODEL = "anthropic/claude-sonnet-5-5"

PROMPT = """Extract a prior authorization packet for a lumbar epidural steroid injection.
Return one JSON object and nothing else.

Rules:
- Copy facts that are written on the pages. Use null when a fact is absent.
- "MRI ordered" is not an imaging report. imaging_report_present is true only when findings are in the packet.
- pain_duration_weeks and conservative_care_weeks are numbers of weeks, or null.
- is_repeat is true only when the note says this injection is a repeat.
- herpes_zoster is true only when herpes zoster or shingles is documented.
- imaging_modality is "MRI" or "CT" when a report is present, otherwise null.
- field_confidence maps each field name to a number from 0 to 1.
- evidence maps field names to a list of {"page": 1-based page, "quote": "short exact quote"}.
- Do not decide coverage. Do not say the packet is complete or incomplete.

Fields:
member_name, member_dob, member_id, provider_name, provider_npi, provider_fax,
cpt, icd10 (array of strings), laterality, spinal_level, is_repeat,
pain_duration_weeks, conservative_care_weeks, conservative_care_description,
unable_to_tolerate_conservative_care, history_and_exam_present,
baseline_pain_score, baseline_function_score, imaging_report_present,
imaging_modality, imaging_findings, prior_relief_percent, prior_relief_months,
herpes_zoster, field_confidence, evidence.
"""


def load_api_key() -> str | None:
    load_dotenv(ROOT / ".env")
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    return key or None


def load_fixture(stem: str) -> Extraction:
    path = FIXTURES / f"{stem}.json"
    if path.exists():
        return Extraction.model_validate(json.loads(path.read_text()))
    spec = packet_by_stem(stem)
    if spec is not None:
        return spec.extraction
    raise FileNotFoundError(f"No fixture for {stem}")


def _parse_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("The model did not return a JSON object.")
    return json.loads(cleaned[start : end + 1])


def _message_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(block.get("text") or "")
            else:
                parts.append(getattr(block, "text", "") or "")
        return "".join(parts)
    return str(content)


def live_extract(pages: list[Page], route: str) -> tuple[Extraction, Cost]:
    import litellm

    key = load_api_key()
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set. Use fixture extraction, or add the key to prototype/.env.")
    os.environ["ANTHROPIC_API_KEY"] = key

    model = SONNET_MODEL if route == "sonnet_vision" else HAIKU_MODEL
    content: list[dict] = [{"type": "text", "text": PROMPT}]
    for page in pages:
        if page.quality == "good" and page.text.strip():
            content.append({"type": "text", "text": f"\n--- page {page.number} text ---\n{page.text}"})
        elif page.quality == "poor":
            encoded = base64.standard_b64encode(page.png).decode("ascii")
            content.append({"type": "text", "text": f"\n--- page {page.number} image (no text layer) ---"})
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{encoded}"},
                }
            )
    messages = [
        {"role": "system", "content": "You extract fax fields into JSON. You do not decide coverage."},
        {"role": "user", "content": content},
    ]
    try:
        response = litellm.completion(
            model=model,
            messages=messages,
            max_tokens=2500,
            response_format={"type": "json_object"},
        )
    except Exception as exc:
        if "response_format" not in str(exc).lower() and "json" not in str(exc).lower():
            raise
        response = litellm.completion(model=model, messages=messages, max_tokens=2500)

    payload = _parse_json(_message_text(response.choices[0].message.content))
    extraction = Extraction.model_validate(payload)
    usage = getattr(response, "usage", None)
    if usage is None:
        return extraction, estimate_cost(pages, route)
    prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    return extraction, measured_cost(model, prompt_tokens, completion_tokens)

from __future__ import annotations

from dataclasses import dataclass


HAIKU_IN = 0.11
HAIKU_OUT = 0.55
SONNET_IN = 2.20
SONNET_OUT = 11.0

# Planning figures for a 15-page production packet, not for these short samples.
PLANNING_BLEND_USD = 0.02
MONTHLY_LOW_USD = 300
MONTHLY_HIGH_USD = 800
PROMPT_OVERHEAD_TOKENS = 700
OUTPUT_TOKENS = 800


@dataclass(frozen=True)
class Cost:
    kind: str
    usd: float
    input_tokens: int
    output_tokens: int
    detail: str


def money(usd: float) -> str:
    if usd < 0.01:
        return f"${usd:.4f}"
    if usd < 1:
        return f"${usd:.3f}"
    if usd < 100:
        return f"${usd:.2f}"
    return f"${usd:,.0f}"


def _image_tokens(width: int, height: int) -> int:
    return max(int(width * height / 750), 1)


def estimate_cost(pages: list, route: str) -> Cost:
    good_text = "\n".join(page.text for page in pages if page.quality == "good")
    text_tokens = len(good_text) // 4
    if route == "haiku_text":
        incoming = text_tokens + PROMPT_OVERHEAD_TOKENS
        usd = incoming * HAIKU_IN / 1_000_000 + OUTPUT_TOKENS * HAIKU_OUT / 1_000_000
        detail = f"Haiku 5.5 text · {incoming:,} in / {OUTPUT_TOKENS} out"
        return Cost("estimated", usd, incoming, OUTPUT_TOKENS, detail)
    image_tokens = sum(
        _image_tokens(page.width, page.height) for page in pages if page.quality == "poor"
    )
    incoming = image_tokens + text_tokens + PROMPT_OVERHEAD_TOKENS
    usd = incoming * SONNET_IN / 1_000_000 + OUTPUT_TOKENS * SONNET_OUT / 1_000_000
    poor = sum(1 for page in pages if page.quality == "poor")
    detail = f"Sonnet 5.5 vision · {poor} page image{'s' if poor != 1 else ''} · {incoming:,} in / {OUTPUT_TOKENS} out"
    return Cost("estimated", usd, incoming, OUTPUT_TOKENS, detail)


def measured_cost(model: str, input_tokens: int, output_tokens: int) -> Cost:
    if "sonnet" in model:
        usd = input_tokens * SONNET_IN / 1_000_000 + output_tokens * SONNET_OUT / 1_000_000
        label = "Sonnet 5.5"
    else:
        usd = input_tokens * HAIKU_IN / 1_000_000 + output_tokens * HAIKU_OUT / 1_000_000
        label = "Haiku 5.5"
    detail = f"{label} measured · {input_tokens:,} in / {output_tokens:,} out"
    return Cost("measured", usd, input_tokens, output_tokens, detail)

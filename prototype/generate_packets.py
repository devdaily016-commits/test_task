"""Write the three synthetic PDFs and their fixture extractions.

Every page is watermarked in spirit as synthetic. Clean packets keep a text
layer. The degraded packet is image-only, with the member ID covered and the
imaging page blacked out.
"""

from __future__ import annotations

import io
import random
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageEnhance, ImageFont
from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from src.packets import all_packets
from src.parse import TEXT_QUALITY_FLOOR

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT / "samples"
FIXTURES = ROOT / "fixtures"
FONT_PATH = Path("/System/Library/Fonts/Supplemental/Courier New.ttf")
MAX_LINE = 78


def _banner(pdf: canvas.Canvas, width: float, height: float) -> None:
    pdf.setFillColor(HexColor("#1E4D6B"))
    pdf.rect(0, height - 26, width, 26, fill=1, stroke=0)
    pdf.setFillColor(white)
    pdf.setFont("Courier", 8)
    pdf.drawString(36, height - 16, "SYNTHETIC   NOT A REAL PATIENT   NOT FOR TREATMENT OR BILLING")


def _watermark(pdf: canvas.Canvas, width: float, height: float) -> None:
    pdf.saveState()
    pdf.setFillColor(Color(0.76, 0.18, 0.14, alpha=0.10))
    pdf.translate(width / 2, height / 2)
    pdf.rotate(30)
    pdf.setFont("Courier-Bold", 58)
    pdf.drawCentredString(0, 0, "SYNTHETIC")
    pdf.restoreState()


def _footer(pdf: canvas.Canvas, width: float, number: int, total: int) -> None:
    pdf.setFillColor(HexColor("#1A2830"))
    pdf.setFont("Courier", 8)
    pdf.drawString(36, 28, "SYNTHETIC DEMONSTRATION")
    pdf.drawRightString(width - 36, 28, f"Page {number} of {total}")


def write_clean(path: Path, pages: list[list[str]]) -> None:
    pdf = canvas.Canvas(str(path), pagesize=letter)
    pdf.setTitle("SYNTHETIC prior authorization packet")
    pdf.setAuthor("Synthetic intake demo")
    width, height = letter
    total = len(pages)
    for number, lines in enumerate(pages, start=1):
        _banner(pdf, width, height)
        _watermark(pdf, width, height)
        pdf.setFillColor(HexColor("#1A2830"))
        pdf.setFont("Courier", 10)
        y = height - 48
        for line in lines:
            if y < 46:
                raise RuntimeError(f"{path.name} page {number} overflow: {line}")
            pdf.drawString(40, y, line)
            y -= 14
        _footer(pdf, width, number, total)
        pdf.showPage()
    pdf.save()


def _speckle(image: Image.Image, amount: float) -> Image.Image:
    noise = Image.effect_noise(image.size, 36).convert("L")
    gray = Image.merge("RGB", (noise, noise, noise))
    return Image.blend(image, gray, amount)


def render_fax_page(
    lines: list[str],
    obscure: list[int],
    light: list[int],
    heavy: bool,
    seed: int,
) -> Image.Image:
    random.seed(seed)
    width, height = 1275, 1650
    image = Image.new("RGB", (width, height), (236, 232, 214))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(FONT_PATH), 22)
    draw.rectangle((0, 0, width, 58), fill=(28, 32, 36))
    draw.text(
        (28, 16),
        "FAX  555-010-0198    10/27/2026  02:14    SYNTHETIC",
        fill=(230, 226, 210),
        font=font,
    )
    y = 88
    for index, line in enumerate(lines):
        if index in obscure:
            draw.rectangle((36, y - 6, width - 36, y + 28), fill=(32, 30, 28))
        else:
            fill = (206, 202, 194) if index in light else (28, 26, 24)
            draw.text((40, y), line, fill=fill, font=font)
        y += 40
    draw.text((40, height - 52), "SYNTHETIC  NOT A REAL PATIENT", fill=(140, 42, 36), font=font)
    if heavy:
        image = _speckle(image, 0.34)
        image = ImageEnhance.Contrast(image).enhance(0.72)
    else:
        image = _speckle(image, 0.10)
    angle = random.uniform(-1.0, 1.0)
    return image.rotate(angle, resample=Image.Resampling.BICUBIC, expand=False, fillcolor=(214, 210, 196))


def write_degraded(path: Path, pages: list[list[str]], obscure: dict, light: dict) -> None:
    pdf = canvas.Canvas(str(path), pagesize=letter)
    pdf.setTitle("SYNTHETIC degraded fax")
    pdf.setAuthor("Synthetic intake demo")
    width, height = letter
    last = len(pages) - 1
    for index, lines in enumerate(pages):
        image = render_fax_page(
            lines,
            obscure=obscure.get(index, []),
            light=light.get(index, []),
            heavy=index == last,
            seed=39240 + index,
        )
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=40)
        buffer.seek(0)
        pdf.drawImage(ImageReader(buffer), 0, 0, width=width, height=height, preserveAspectRatio=True, anchor="c")
        pdf.showPage()
    pdf.save()


def _assert_text_layer(path: Path, expect_text: bool) -> None:
    document = pymupdf.open(path)
    try:
        for page in document:
            alnum = sum(character.isalnum() for character in (page.get_text("text") or ""))
            readable = alnum >= TEXT_QUALITY_FLOOR
            if readable != expect_text:
                raise RuntimeError(f"{path.name} text-layer check failed (alnum={alnum})")
    finally:
        document.close()


def main() -> None:
    if not FONT_PATH.exists():
        raise SystemExit(f"Missing font for the degraded fax: {FONT_PATH}")
    SAMPLES.mkdir(exist_ok=True)
    FIXTURES.mkdir(exist_ok=True)
    for spec in all_packets():
        for lines in spec.pages:
            for line in lines:
                if len(line) > MAX_LINE:
                    raise SystemExit(f"{spec.stem} line is {len(line)} chars: {line}")
        pdf_path = SAMPLES / f"{spec.stem}.pdf"
        if spec.degrade:
            write_degraded(pdf_path, spec.pages, spec.obscure_lines, spec.light_lines)
        else:
            write_clean(pdf_path, spec.pages)
        _assert_text_layer(pdf_path, expect_text=not spec.degrade)
        fixture = FIXTURES / f"{spec.stem}.json"
        fixture.write_text(spec.extraction.model_dump_json(indent=2) + "\n")
        print(f"wrote {pdf_path.name} and {fixture.name}")


if __name__ == "__main__":
    main()

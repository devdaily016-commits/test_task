from __future__ import annotations

from dataclasses import dataclass

import pymupdf


TEXT_QUALITY_FLOOR = 80


@dataclass
class Page:
    number: int
    text: str
    png: bytes
    width: int
    height: int
    quality: str
    alnum: int


def parse_pdf(path) -> list[Page]:
    document = pymupdf.open(path)
    pages: list[Page] = []
    try:
        for index, page in enumerate(document):
            text = page.get_text("text") or ""
            alnum = sum(character.isalnum() for character in text)
            quality = "good" if alnum >= TEXT_QUALITY_FLOOR else "poor"
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(1.6, 1.6), alpha=False)
            pages.append(
                Page(
                    number=index + 1,
                    text=text,
                    png=pixmap.tobytes("png"),
                    width=pixmap.width,
                    height=pixmap.height,
                    quality=quality,
                    alnum=alnum,
                )
            )
    finally:
        document.close()
    if not pages:
        raise ValueError(f"No pages in {path}")
    return pages


def route_for(pages: list[Page]) -> str:
    if any(page.quality == "poor" for page in pages):
        return "sonnet_vision"
    return "haiku_text"

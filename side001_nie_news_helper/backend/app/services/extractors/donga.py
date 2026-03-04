# backend/app/services/extractors/donga.py
from __future__ import annotations

from typing import List, Optional

from .base import BaseExtractor, ExtractionError


class DongaExtractor(BaseExtractor):
    extractor_name: str = "donga"

    def supports(self, url: Optional[str] = None, html: Optional[str] = None) -> bool:
        if url and "donga.com" in url:
            return True
        if html and "news_view" in html:
            return True
        return False

    def _extract_text_blocks(self, html: str, url: Optional[str]) -> List[str]:
        soup = self._try_get_soup(html)

        section = soup.select_one("section.news_view")
        if section is None:
            raise ExtractionError("동아일보 본문 영역(section.news_view)을 찾지 못했습니다.")

        # Remove obvious non-content
        for tag in section.select("script, style, nav, header, footer, aside, form"):
            tag.decompose()

        # Prefer known text containers if present
        container = (
            section.select_one(".article_txt")
            or section.select_one(".article_txt .txt")
            or section.select_one(".article_txts")
            or section.select_one(".article")
            or section
        )

        # If the container has <p>, use them
        p_tags = container.find_all("p")
        if p_tags:
            blocks: List[str] = []
            for p in p_tags:
                txt = p.get_text(" ", strip=True)
                if txt:
                    blocks.append(txt)
            if self._total_len(blocks) >= 120:
                return blocks

        # Fallback: split by newlines (handles <br>)
        text = container.get_text("\n", strip=True)
        blocks = self._split_lines_to_blocks(text)

        return blocks

    def _is_boilerplate(self, line: str) -> bool:
        if super()._is_boilerplate(line):
            return True

        # Donga-specific footer patterns (keep conservative)
        bad = [
            "동아일보 db",
            "동아일보db",
            "ⓒ",
            "구독",
            "공유",
            "댓글",
            "좋아요",
        ]
        if any(b in line for b in bad):
            return True

        return False

    @staticmethod
    def _total_len(blocks: List[str]) -> int:
        return sum(len(b) for b in blocks)
    
def extract_news_view_text(html: str, url: str | None = None) -> str:
    """
    동아일보 section.news_view에서 본문 텍스트만 추출해 하나의 문자열로 반환.
    (문단 구분은 \\n\\n)
    """
    ex = DongaExtractor()
    blocks = ex._extract_text_blocks(html=html, url=url)
    blocks = ex._postprocess_blocks(blocks)
    return "\n\n".join(blocks).strip()
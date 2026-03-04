# backend/app/services/extractors/generic.py
from __future__ import annotations

from typing import Iterable, List, Optional, Tuple

from .base import BaseExtractor


class GenericExtractor(BaseExtractor):
    extractor_name: str = "generic"

    def supports(self, url: Optional[str] = None, html: Optional[str] = None) -> bool:
        return True

    def _extract_text_blocks(self, html: str, url: Optional[str]) -> List[str]:
        soup = self._try_get_soup(html)

        for tag in soup.select("script, style, nav, header, footer, aside, form, noscript"):
            tag.decompose()

        candidate = self._pick_best_container(soup)
        text = candidate.get_text("\n", strip=True)
        blocks = self._split_lines_to_blocks(text)

        # If we accidentally grabbed too much chrome, keep only the densest run.
        blocks = self._trim_low_signal(blocks)

        return blocks

    def _pick_best_container(self, soup):
        candidates = []

        selectors = [
            "article",
            "main",
            "[role='main']",
            "#content",
            "#article",
            ".article",
            ".article-body",
            ".articleBody",
            ".content",
            ".post-content",
            ".entry-content",
            ".news_view",
        ]

        for sel in selectors:
            for el in soup.select(sel):
                candidates.append(el)

        if not candidates:
            body = soup.body or soup
            return body

        scored: List[Tuple[int, object]] = []
        for el in candidates:
            txt = el.get_text(" ", strip=True)
            score = len(txt)
            scored.append((score, el))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    def _trim_low_signal(self, blocks: Iterable[str]) -> List[str]:
        lst = [b for b in blocks if b]
        if not lst:
            return []

        # Keep blocks that look like prose; drop very short UI crumbs.
        prose = [b for b in lst if len(b) >= 10]
        if len(prose) >= 3:
            return prose

        return lst
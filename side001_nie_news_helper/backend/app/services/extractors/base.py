# backend/app/services/extractors/base.py
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable, List, Optional


class ExtractionError(RuntimeError):
    pass


_RE_WS = re.compile(r"[ \t\r\f\v]+")
_RE_MULTI_NL = re.compile(r"\n{2,}")


@dataclass(frozen=True)
class Paragraph:
    id: str
    text: str

    def to_dict(self) -> dict:
        return {"id": self.id, "text": self.text}


class BaseExtractor(ABC):
    extractor_name: str = "base"

    def supports(self, url: Optional[str] = None, html: Optional[str] = None) -> bool:
        return False

    def extract(self, html: str, url: Optional[str] = None) -> List[dict]:
        blocks = self._extract_text_blocks(html=html, url=url)
        blocks = self._postprocess_blocks(blocks)
        paragraphs = [
            Paragraph(id=f"p{i+1}", text=txt).to_dict() for i, txt in enumerate(blocks)
        ]
        return paragraphs

    @abstractmethod
    def _extract_text_blocks(self, html: str, url: Optional[str]) -> List[str]:
        raise NotImplementedError

    def _postprocess_blocks(self, blocks: Iterable[str]) -> List[str]:
        cleaned: List[str] = []
        prev: Optional[str] = None

        for raw in blocks:
            s = self._normalize_text(raw)
            if not s:
                continue
            if self._is_boilerplate(s):
                continue
            if prev is not None and s == prev:
                continue
            cleaned.append(s)
            prev = s

        return cleaned

    def _normalize_text(self, text: str) -> str:
        s = text.replace("\u00a0", " ")
        s = _RE_WS.sub(" ", s)
        s = s.strip()
        return s

    def _split_lines_to_blocks(self, text: str) -> List[str]:
        t = text.replace("\u00a0", " ")
        t = t.replace("\r\n", "\n").replace("\r", "\n")
        t = _RE_MULTI_NL.sub("\n\n", t).strip()
        parts = [p.strip() for p in t.split("\n") if p.strip()]
        return parts

    def _is_boilerplate(self, line: str) -> bool:
        # Keep this conservative for v1.
        lower = line.lower()

        bad_substrings = [
            "무단 전재",
            "재배포 금지",
            "copyright",
            "all rights reserved",
            "동아일보",
            "donga",
            "기사입력",
            "입력 ",
            "수정 ",
            "기자",
            "기자 ",
            "기자=",
            "이메일",
            "email",
            "관련기사",
            "추천기사",
        ]
        if any(bs in line for bs in bad_substrings):
            return True
        if any(bs in lower for bs in ["copyright", "all rights reserved"]):
            return True

        # Very short UI crumbs (but allow short meaningful sentences).
        if len(line) <= 2:
            return True

        return False

    def _try_get_soup(self, html: str):
        try:
            from bs4 import BeautifulSoup  # type: ignore
        except Exception as e:
            raise ExtractionError(
                "BeautifulSoup(bs4)가 필요합니다. 의존성에 bs4를 추가하세요."
            ) from e

        return BeautifulSoup(html, "html.parser")
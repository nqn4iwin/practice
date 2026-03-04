# backend/app/services/cleaner.py
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional


_RE_WS = re.compile(r"[ \t\r\f\v]+")
_RE_MULTI_NL = re.compile(r"\n{3,}")


class CleanError(RuntimeError):
    pass


@dataclass(frozen=True)
class CleanedArticle:
    title: str
    url: str
    paragraphs: List[Dict[str, str]]  # [{"id": "...", "text": "..."}]

    def to_dict(self) -> Dict[str, object]:
        return {"title": self.title, "url": self.url, "paragraphs": self.paragraphs}


class ArticleCleaner:
    """
    v1: extractor 결과(paragraphs)를 프론트 렌더링용으로 최소 정제.
    - 공백/개행 정리
    - 너무 짧은 문단 제거(보수적으로)
    - id 재부여(p1..)
    """

    def __init__(self, min_len: int = 5):
        self.min_len = min_len

    def clean(self, *, title: str, url: str, paragraphs: List[Dict[str, str]]) -> CleanedArticle:
        if not isinstance(paragraphs, list):
            raise CleanError("paragraphs는 리스트여야 합니다.")

        cleaned_texts: List[str] = []
        for p in paragraphs:
            txt = (p or {}).get("text", "")
            t = self._normalize(txt)
            if not t:
                continue
            if len(t) < self.min_len:
                continue
            cleaned_texts.append(t)

        re_paragraphs = [{"id": f"p{i+1}", "text": t} for i, t in enumerate(cleaned_texts)]
        return CleanedArticle(title=self._normalize_title(title), url=url, paragraphs=re_paragraphs)

    def _normalize(self, text: str) -> str:
        s = (text or "").replace("\u00a0", " ")
        s = s.replace("\r\n", "\n").replace("\r", "\n")
        s = _RE_WS.sub(" ", s)
        s = _RE_MULTI_NL.sub("\n\n", s)
        s = s.strip()
        return s

    def _normalize_title(self, title: str) -> str:
        t = self._normalize(title)
        return t or "제목 없음"
    
def to_paragraph_texts(x, min_len: int = 5) -> list[str]:
    """
    API가 기대하는 함수형 인터페이스.
    - 입력: str(전체 텍스트) 또는 list[str] 또는 list[{"text": ...}]
    - 출력: 문단 텍스트 리스트
    """
    cleaner = ArticleCleaner(min_len=min_len)

    # list[dict] or list[str]
    if isinstance(x, list):
        texts = []
        for item in x:
            if isinstance(item, dict):
                texts.append(str(item.get("text", "")))
            else:
                texts.append(str(item))
        out = []
        for t in texts:
            t2 = cleaner._normalize(t)
            if t2 and len(t2) >= min_len:
                out.append(t2)
        return out

    # str
    s = cleaner._normalize(str(x))
    if not s:
        return []

    # 빈 줄 기준 우선, 없으면 줄 기준
    if "\n\n" in s:
        parts = [p.strip() for p in s.split("\n\n")]
    else:
        parts = [p.strip() for p in s.split("\n")]

    out = []
    for p in parts:
        p2 = cleaner._normalize(p)
        if p2 and len(p2) >= min_len:
            out.append(p2)
    return out
# backend/app/schemas/llm.py

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class ParagraphIn(BaseModel):
    id: str
    text: str


class ExplainRequest(BaseModel):
    selection_text: str = Field(..., description="사용자가 선택한 문장/구간")
    context_paragraphs: List[ParagraphIn] = Field(
        default_factory=list, description="선택 구간 주변 문단(컨텍스트)"
    )


class ExplainResponse(BaseModel):
    explanation: str


class QuestionsRequest(BaseModel):
    paragraphs: List[ParagraphIn] = Field(..., description="기사 문단 전체")
    n: int = Field(5, ge=1, le=12, description="질문 개수")


class QuestionsResponse(BaseModel):
    questions: List[str]


class VocabLookupRequest(BaseModel):
    word: str = Field(..., min_length=1, description="조회할 단어/표현")
    context_text: Optional[str] = Field(None, description="컨텍스트(선택)")


class VocabLookupResponse(BaseModel):
    word: str
    meaning: str
    examples: List[str] = Field(default_factory=list)
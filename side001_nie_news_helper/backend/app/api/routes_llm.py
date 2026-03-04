# backend/app/api/routes_llm.py

from __future__ import annotations

from typing import List, Optional, Union

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter(prefix="/api/llm", tags=["llm"])


class ParagraphIn(BaseModel):
    id: str
    text: str


class ExplainRequest(BaseModel):
    selection_text: str = Field(..., description="사용자가 드래그로 선택한 문장/구간")
    context_paragraphs: List[ParagraphIn] = Field(
        default_factory=list, description="선택 구간 주변 문단(컨텍스트)"
    )


class ExplainResponse(BaseModel):
    explanation: str


class QuestionsRequest(BaseModel):
    paragraphs: List[ParagraphIn] = Field(..., description="기사 문단 전체")
    n: int = Field(5, ge=1, le=12, description="질문 개수(기본 5, v1 한정)")


class QuestionsResponse(BaseModel):
    questions: List[str]


class VocabLookupRequest(BaseModel):
    word: str = Field(..., min_length=1, description="조회할 단어/표현")
    context_text: Optional[str] = Field(None, description="선택 구간/문장 등 컨텍스트(선택)")


class VocabLookupResponse(BaseModel):
    word: str
    meaning: str
    examples: List[str] = Field(default_factory=list)


def _join_paragraphs(paragraphs: List[ParagraphIn]) -> str:
    return "\n\n".join([p.text.strip() for p in paragraphs if p.text and p.text.strip()])


@router.post("/explain", response_model=ExplainResponse)
def explain(payload: ExplainRequest) -> ExplainResponse:
    try:
        from app.services.llm_client import explain_selection  # type: ignore
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Service import failed: {e}") from e

    selection = (payload.selection_text or "").strip()
    if not selection:
        raise HTTPException(status_code=422, detail="selection_text is empty.")

    context = _join_paragraphs(payload.context_paragraphs)

    try:
        explanation = explain_selection(selection_text=selection, context_text=context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM explain failed: {e}") from e

    return ExplainResponse(explanation=str(explanation).strip())


@router.post("/questions", response_model=QuestionsResponse)
def questions(payload: QuestionsRequest) -> QuestionsResponse:
    try:
        from app.services.llm_client import generate_critical_questions  # type: ignore
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Service import failed: {e}") from e

    article_text = _join_paragraphs(payload.paragraphs)
    if not article_text:
        raise HTTPException(status_code=422, detail="paragraphs are empty.")

    try:
        qs = generate_critical_questions(article_text=article_text, n=payload.n)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM questions failed: {e}") from e

    questions_list: List[str] = [str(q).strip() for q in (qs or []) if str(q).strip()]
    return QuestionsResponse(questions=questions_list)


@router.post("/vocab-lookup", response_model=VocabLookupResponse)
def vocab_lookup(payload: VocabLookupRequest) -> VocabLookupResponse:
    try:
        from app.services.llm_client import vocab_lookup as llm_vocab_lookup  # type: ignore
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Service import failed: {e}") from e

    word = (payload.word or "").strip()
    if not word:
        raise HTTPException(status_code=422, detail="word is empty.")

    try:
        result = llm_vocab_lookup(word=word, context_text=(payload.context_text or "").strip() or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM vocab lookup failed: {e}") from e

    if isinstance(result, dict):
        meaning = str(result.get("meaning", "")).strip()
        examples = result.get("examples", []) or []
    else:
        meaning = str(result).strip()
        examples = []

    if not meaning:
        raise HTTPException(status_code=502, detail="Vocab lookup returned empty meaning.")

    examples_list = [str(x).strip() for x in examples if str(x).strip()]
    return VocabLookupResponse(word=word, meaning=meaning, examples=examples_list)
# backend/app/api/routes_article.py

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import AnyHttpUrl, BaseModel, Field


router = APIRouter(prefix="/api/article", tags=["article"])


class ArticleParseRequest(BaseModel):
    url: AnyHttpUrl = Field(..., description="DongA일보 기사 URL (v1)")


class Paragraph(BaseModel):
    id: str
    text: str


class ArticleParseResponse(BaseModel):
    url: str
    paragraphs: List[Paragraph]


@router.post("/parse", response_model=ArticleParseResponse)
def parse_article(payload: ArticleParseRequest) -> ArticleParseResponse:
    """
    v1: 동아일보 페이지에서 section.news_view 본문을 추출하고 paragraphs[{id,text}]로 반환.
    """
    url = str(payload.url)

    try:
        # 서비스 인터페이스는 이미 존재한다고 가정
        from app.services.fetcher import fetch_html  # type: ignore
        from app.services.extractors.donga import extract_news_view_text  # type: ignore
        from app.services.cleaner import to_paragraph_texts  # type: ignore
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Service import failed: {e}") from e

    try:
        html = fetch_html(url)
        raw_text = extract_news_view_text(html)
        paragraph_texts = to_paragraph_texts(raw_text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse article: {e}") from e

    paragraphs = [
        Paragraph(id=f"p{i+1}", text=t) for i, t in enumerate(paragraph_texts) if t and t.strip()
    ]
    if not paragraphs:
        raise HTTPException(status_code=422, detail="No paragraphs extracted.")

    return ArticleParseResponse(url=url, paragraphs=paragraphs)
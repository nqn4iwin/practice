# backend/app/schemas/article.py

from __future__ import annotations

from typing import List
from pydantic import AnyHttpUrl, BaseModel, Field


class ArticleParseRequest(BaseModel):
    url: AnyHttpUrl = Field(..., description="DongA일보 기사 URL (v1)")


class Paragraph(BaseModel):
    id: str
    text: str


class ArticleParseResponse(BaseModel):
    url: str
    paragraphs: List[Paragraph]
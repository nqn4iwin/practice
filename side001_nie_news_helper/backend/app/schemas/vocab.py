# backend/app/schemas/vocab.py

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class VocabAddRequest(BaseModel):
    word: str = Field(..., min_length=1)
    meaning: str = Field(..., min_length=1)
    example: Optional[str] = None
    source_url: Optional[str] = None


class VocabEntry(BaseModel):
    id: int
    word: str
    meaning: str
    example: Optional[str] = None
    source_url: Optional[str] = None
    created_at: Optional[str] = None


class VocabAddResponse(BaseModel):
    entry: VocabEntry


class VocabListResponse(BaseModel):
    items: List[VocabEntry]


class VocabDeleteRequest(BaseModel):
    id: int = Field(..., ge=1)


class VocabDeleteResponse(BaseModel):
    ok: bool
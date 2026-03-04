# backend/app/api/routes_vocab.py

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter(prefix="/api/vocab", tags=["vocab"])


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


@router.post("/add", response_model=VocabAddResponse)
def add_vocab(payload: VocabAddRequest) -> VocabAddResponse:
    try:
        from app.services.db_crud import vocab as vocab_crud  # type: ignore
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Service import failed: {e}") from e

    word = payload.word.strip()
    meaning = payload.meaning.strip()

    try:
        created = vocab_crud.add(
            word=word,
            meaning=meaning,
            example=(payload.example.strip() if payload.example else None),
            source_url=(payload.source_url.strip() if payload.source_url else None),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB add failed: {e}") from e

    if not isinstance(created, dict) or "id" not in created:
        raise HTTPException(status_code=502, detail="DB add returned invalid payload.")

    return VocabAddResponse(entry=VocabEntry(**created))


@router.get("/list", response_model=VocabListResponse)
def list_vocab(limit: int = 200, offset: int = 0) -> VocabListResponse:
    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=422, detail="limit must be 1..1000")
    if offset < 0:
        raise HTTPException(status_code=422, detail="offset must be >= 0")

    try:
        from app.services.db_crud import vocab as vocab_crud  # type: ignore
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Service import failed: {e}") from e

    try:
        rows = vocab_crud.list(limit=limit, offset=offset)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB list failed: {e}") from e

    items = [VocabEntry(**r) for r in (rows or []) if isinstance(r, dict)]
    return VocabListResponse(items=items)


@router.post("/delete", response_model=VocabDeleteResponse)
def delete_vocab(payload: VocabDeleteRequest) -> VocabDeleteResponse:
    try:
        from app.services.db_crud import vocab as vocab_crud  # type: ignore
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Service import failed: {e}") from e

    try:
        ok = bool(vocab_crud.delete(entry_id=payload.id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB delete failed: {e}") from e

    return VocabDeleteResponse(ok=ok)
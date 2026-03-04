# backend/app/db/crud.py

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import Vocab


def add_vocab(
    db: Session,
    word: str,
    meaning: str,
    example: Optional[str] = None,
    source_url: Optional[str] = None,
) -> Dict[str, Any]:
    word = (word or "").strip()
    meaning = (meaning or "").strip()
    if not word:
        raise ValueError("word is empty")
    if not meaning:
        raise ValueError("meaning is empty")

    row = Vocab(
        word=word,
        meaning=meaning,
        example=(example.strip() if example else None),
        source_url=(source_url.strip() if source_url else None),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def list_vocab(db: Session, limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
    stmt = (
        select(Vocab)
        .order_by(Vocab.id.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = db.execute(stmt).scalars().all()
    return [_to_dict(r) for r in rows]


def delete_vocab(db: Session, entry_id: int) -> bool:
    stmt = delete(Vocab).where(Vocab.id == entry_id)
    res = db.execute(stmt)
    db.commit()
    return (res.rowcount or 0) > 0


def _to_dict(row: Vocab) -> Dict[str, Any]:
    return {
        "id": row.id,
        "word": row.word,
        "meaning": row.meaning,
        "example": row.example,
        "source_url": row.source_url,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
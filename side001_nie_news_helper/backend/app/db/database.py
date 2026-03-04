# backend/app/db/database.py

from __future__ import annotations

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# 기본: 프로젝트 루트에서 실행 시 ./nie.db 생성
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./nie.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    # models import가 먼저 되어야 테이블이 등록됨
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
# backend/app/main.py
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .services.cleaner import CleanError
from .services.fetcher import FetchError
from .services.extractors.base import ExtractionError
from .services.llm.client import LLMClientError, LLMResponseParseError


def create_app() -> FastAPI:
    app = FastAPI(title="NIE News Helper API", version="0.1.0")

    origins_raw = os.getenv("CORS_ALLOW_ORIGINS", "*").strip()
    allow_origins = ["*"] if origins_raw == "*" else [o.strip() for o in origins_raw.split(",") if o.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health():
        return {"ok": True}

    @app.exception_handler(FetchError)
    async def fetch_error_handler(_req, exc: FetchError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(ExtractionError)
    async def extraction_error_handler(_req, exc: ExtractionError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(CleanError)
    async def clean_error_handler(_req, exc: CleanError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(LLMResponseParseError)
    async def llm_parse_error_handler(_req, exc: LLMResponseParseError):
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.exception_handler(LLMClientError)
    async def llm_client_error_handler(_req, exc: LLMClientError):
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    # Routers (각 router는 "/article/...", "/llm/...", "/vocab/..." 형태로 정의한다고 가정)
    from .api.routes_article import router as article_router
    from .api.routes_llm import router as llm_router
    from .api.routes_vocab import router as vocab_router

    app.include_router(article_router)
    app.include_router(llm_router)
    app.include_router(vocab_router)

    return app


app = create_app()
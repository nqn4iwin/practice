# backend/app/services/fetcher.py
from __future__ import annotations

import certifi
import logging
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class FetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class FetchResult:
    url: str
    status_code: int
    html: str
    final_url: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "url": self.url,
            "status_code": self.status_code,
            "final_url": self.final_url,
            "html": self.html,
        }


class Fetcher:
    """
    v1: URL에서 HTML을 가져오는 최소 구현.
    - httpx 사용
    - UA 설정
    - 리다이렉트 허용
    - 인코딩 자동 처리
    """

    def __init__(self, timeout_s: float = 20.0, user_agent: Optional[str] = None):
        self.timeout_s = timeout_s
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0 Safari/537.36"
        )

    def fetch(self, url: str) -> FetchResult:
        self._validate_url(url)

        try:
            import httpx  # type: ignore
        except Exception as e:
            raise FetchError("httpx가 필요합니다. 의존성에 httpx를 추가하세요.") from e

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko,en;q=0.8",
            "Connection": "keep-alive",
        }

        try:
            with httpx.Client(timeout=self.timeout_s, follow_redirects=True, headers=headers, verify=certifi.where(),) as client:
                resp = client.get(url)
        except Exception as e:
            raise FetchError(f"요청 실패: {e}") from e

        status = int(resp.status_code)
        if status >= 400:
            raise FetchError(f"HTTP 오류(status={status})")

        # httpx는 encoding을 추정해 text를 제공. 실패 대비로 fallback.
        try:
            html = resp.text
        except Exception:
            html = resp.content.decode("utf-8", errors="replace")

        final_url = str(resp.url)
        return FetchResult(url=url, status_code=status, html=html, final_url=final_url)

    @staticmethod
    def _validate_url(url: str) -> None:
        try:
            parsed = urlparse(url)
        except Exception as e:
            raise FetchError("URL 파싱 실패") from e

        if parsed.scheme not in {"http", "https"}:
            raise FetchError("http/https URL만 지원합니다.")
        if not parsed.netloc:
            raise FetchError("유효하지 않은 URL입니다.")
        
def fetch_html(url: str, timeout_s: float = 20.0, user_agent: str | None = None) -> str:
    return Fetcher(timeout_s=timeout_s, user_agent=user_agent).fetch(url).html
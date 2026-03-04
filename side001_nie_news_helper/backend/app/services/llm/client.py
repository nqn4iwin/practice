# backend/app/services/llm/client.py
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_RE_CODE_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


class LLMClientError(RuntimeError):
    pass


class LLMResponseParseError(LLMClientError):
    pass


@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    model: str
    base_url: str = "https://api.openai.com"
    timeout_s: float = 30.0
    temperature: float = 0.2
    max_tokens: int = 900
    json_mode: bool = True

    @staticmethod
    def from_env() -> "LLMConfig":
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY") or ""
        if not api_key:
            raise LLMClientError("OPENAI_API_KEY(또는 LLM_API_KEY)가 필요합니다.")

        model = os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL") or ""
        if not model:
            raise LLMClientError("LLM_MODEL(또는 OPENAI_MODEL)이 필요합니다.")

        base_url = (os.getenv("LLM_BASE_URL") or "https://api.openai.com").rstrip("/")
        timeout_s = float(os.getenv("LLM_TIMEOUT_S") or "30")
        temperature = float(os.getenv("LLM_TEMPERATURE") or "0.2")
        max_tokens = int(os.getenv("LLM_MAX_TOKENS") or "900")
        json_mode = (os.getenv("LLM_JSON_MODE") or "1").strip() not in {"0", "false", "False"}

        return LLMConfig(
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout_s=timeout_s,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
        )


class LLMClient:
    """
    OpenAI 호환 Chat Completions API 클라이언트.
    - 기본 엔드포인트: {base_url}/v1/chat/completions
    - 프롬프트 템플릿: backend/app/services/llm/prompt/*.txt
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig.from_env()
        self._prompt_dir = Path(__file__).resolve().parent / "prompt"

    def explain(self, *, title: str, url: str, context_paragraphs: Any, selected_text: str) -> Dict[str, Any]:
        prompt = self._render_prompt(
            "explain.txt",
            title=title,
            url=url,
            context_paragraphs=self._ensure_json_str(context_paragraphs),
            selected_text=selected_text,
        )
        return self._chat_json(prompt)

    def questions(self, *, title: str, url: str, paragraphs: Any) -> Dict[str, Any]:
        prompt = self._render_prompt(
            "questions.txt",
            title=title,
            url=url,
            paragraphs=self._ensure_json_str(paragraphs),
        )
        return self._chat_json(prompt)

    def vocab_lookup(self, *, title: str, url: str, context_paragraphs: Any, term: str) -> Dict[str, Any]:
        prompt = self._render_prompt(
            "vocab.txt",
            title=title,
            url=url,
            context_paragraphs=self._ensure_json_str(context_paragraphs),
            term=term,
        )
        return self._chat_json(prompt)

    def _render_prompt(self, filename: str, **kwargs: Any) -> str:
        path = self._prompt_dir / filename
        if not path.exists():
            raise LLMClientError(f"프롬프트 파일을 찾지 못했습니다: {path}")

        template = path.read_text(encoding="utf-8")

        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise LLMClientError(f"프롬프트 변수 누락: {e}") from e

    def _chat_json(self, user_prompt: str) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": user_prompt}],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        if self.config.json_mode:
            payload["response_format"] = {"type": "json_object"}

        data = self._post_chat_completions(payload)
        content = self._extract_content(data)
        return self._parse_json(content)

    def _post_chat_completions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.config.base_url}/v1/chat/completions"

        try:
            import httpx  # type: ignore
        except Exception as e:
            raise LLMClientError("httpx가 필요합니다. 의존성에 httpx를 추가하세요.") from e

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=self.config.timeout_s) as client:
                resp = client.post(url, headers=headers, json=payload)
        except Exception as e:
            raise LLMClientError(f"LLM 호출 실패: {e}") from e

        if resp.status_code >= 400:
            msg = resp.text
            raise LLMClientError(f"LLM 응답 오류(status={resp.status_code}): {msg}")

        try:
            return resp.json()
        except Exception as e:
            raise LLMClientError("LLM 응답이 JSON이 아닙니다.") from e

    @staticmethod
    def _extract_content(data: Dict[str, Any]) -> str:
        try:
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            raise LLMClientError("LLM 응답 형식이 예상과 다릅니다.") from e

    @staticmethod
    def _parse_json(text: str) -> Dict[str, Any]:
        s = text.strip()
        s = _RE_CODE_FENCE.sub("", s).strip()

        try:
            obj = json.loads(s)
        except Exception as e:
            raise LLMResponseParseError(f"LLM JSON 파싱 실패: {e}\n원문:\n{s}") from e

        if not isinstance(obj, dict):
            raise LLMResponseParseError("LLM 응답 JSON 최상위는 객체(dict)여야 합니다.")

        return obj

    @staticmethod
    def _ensure_json_str(x: Any) -> str:
        if isinstance(x, str):
            return x
        try:
            return json.dumps(x, ensure_ascii=False)
        except Exception:
            return str(x)
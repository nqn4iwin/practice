# src/text/tokenize_ko.py

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_WORD_RE = re.compile(r"[가-힣]{2,}|[A-Za-z]{2,}|\d+")


@dataclass
class KoreanTokenizer:
    min_token_len: int
    max_tokens_per_doc: int | None
    _kiwi: Optional[object] = None
    _hf: Optional[object] = None  # transformers tokenizer

    @classmethod
    def build(cls, cfg) -> "KoreanTokenizer":
        tok = cls(min_token_len=cfg.min_token_len, max_tokens_per_doc=cfg.max_tokens_per_doc)

        # Kiwi: force local model_path (root/models/kiwi)
        try:
            from kiwipiepy import Kiwi  # type: ignore

            root = Path(__file__).resolve().parents[2]  # root/src/text -> root
            model_dir = root / "models" / "kiwi"
            tok._kiwi = Kiwi(model_path=str(model_dir))
        except Exception:
            tok._kiwi = None

        # HF tokenizer (KLUE-RoBERTa)
        try:
            from transformers import AutoTokenizer  # type: ignore

            tok._hf = AutoTokenizer.from_pretrained(cfg.hf_tokenizer_name, use_fast=True)
        except Exception:
            tok._hf = None

        return tok

    def word_tokens(self, text: str) -> list[str]:
        text = (text or "").strip()
        if not text:
            return []

        toks: list[str] = []
        allowed_pos = {"NNG", "NNP"}

        if self._kiwi is not None:
            
            # 기존: analyzed = self._kiwi.analyze(text); tokens = analyzed[0][0]
            tokens = self._kiwi.tokenize(text)

            for t in tokens:
                if t.tag not in {"NNG", "NNP"}:
                    continue
                w = t.form.strip()
                if len(w) < self.min_token_len:
                    continue
                toks.append(w)
            
        else:
            for w in _WORD_RE.findall(text):
                w = w.strip()
                if len(w) < self.min_token_len:
                    continue
                toks.append(w)

        if self.max_tokens_per_doc is not None and len(toks) > self.max_tokens_per_doc:
            toks = toks[: self.max_tokens_per_doc]
        return toks

    def subword_tokens(self, text: str) -> list[str]:
        text = (text or "").strip()
        if not text:
            return []

        if self._hf is None:
            return self.word_tokens(text)

        tokens = self._hf.tokenize(text)
        if self.max_tokens_per_doc is not None and len(tokens) > self.max_tokens_per_doc:
            tokens = tokens[: self.max_tokens_per_doc]
        return tokens
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


_WS_RE = re.compile(r"\s+")
_QUOTE_RE = re.compile(r"[\"“”‘’]")
_CTRL_RE = re.compile(r"[\u0000-\u001f]")


@dataclass(frozen=True)
class Example:
    label: str
    text: str


def normalize_text(s: str) -> str:
    s = s.strip()
    s = _QUOTE_RE.sub("", s)
    s = _CTRL_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s)
    return s


def load_json_list(path: Path) -> list[Example]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    out: list[Example] = []
    for i, row in enumerate(data):
        if not isinstance(row, dict):
            continue
        label = str(row.get("label", "")).strip()
        text = str(row.get("text", "")).strip()
        if not label or not text:
            continue
        out.append(Example(label=label, text=normalize_text(text)))
    return out


def load_stopwords(path: Path) -> set[str]:
    if not path.exists():
        return set()
    sw: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        t = line.strip()
        if not t or t.startswith("#"):
            continue
        sw.add(t)
    return sw
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from html import unescape
from typing import Any, Dict, List, Optional, Tuple

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

try:
    from bs4 import BeautifulSoup  # pip install beautifulsoup4
except Exception:
    BeautifulSoup = None

app = Flask(__name__)
CORS(app)

UPSTAGE_API_KEY = os.environ.get("UPSTAGE_API_KEY", "").strip()
UPSTAGE_MODEL = os.environ.get("UPSTAGE_MODEL", "solar-pro2").strip()
UPSTAGE_CHAT_URL = "https://api.upstage.ai/v1/chat/completions"

DB_PATH = os.environ.get("VOCAB_DB_PATH", "vocab.db").strip()


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vocab (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              article_id TEXT,
              term TEXT NOT NULL,
              definition TEXT,
              pos TEXT,
              examples TEXT,
              synonyms TEXT,
              source_sentence TEXT,
              created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def is_http_url(url: str) -> bool:
    return url.startswith("http://") or url.startswith("https://")


def sha1_text(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def fetch_html(url: str) -> str:
    r = requests.get(
        url,
        timeout=15,
        headers={
            "User-Agent": "Mozilla/5.0 (NIE Helper MVP)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    r.raise_for_status()
    r.encoding = r.apparent_encoding or r.encoding
    return r.text


def clean_lines(text: str) -> List[str]:
    text = unescape(text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [ln.strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if ln]
    # 광고/잡음 라인 최소 제거
    bad = {"AD", "광고", "기사입력", "기사수정"}
    out = []
    for ln in lines:
        if ln in bad:
            continue
        out.append(ln)
    return out


def extract_donga(html: str) -> Tuple[str, List[str]]:
    """
    동아일보: section.news_view 내 텍스트를 최대한 본문만 남김.
    return: (title, paragraphs)
    """
    if BeautifulSoup is None:
        # fallback: regex로 section.news_view 대충 잡기
        m = re.search(r'<section[^>]*class="news_view"[^>]*>(.*?)</section>', html, re.S | re.I)
        body = m.group(1) if m else html
        body = re.sub(r"<script.*?>.*?</script>", " ", body, flags=re.S | re.I)
        body = re.sub(r"<style.*?>.*?</style>", " ", body, flags=re.S | re.I)
        body = re.sub(r"<iframe.*?>.*?</iframe>", " ", body, flags=re.S | re.I)
        body = re.sub(r"<[^>]+>", "\n", body)
        lines = clean_lines(body)
        return ("", lines)

    soup = BeautifulSoup(html, "html.parser")

    title = ""
    og = soup.select_one('meta[property="og:title"]')
    if og and og.get("content"):
        title = og.get("content", "").strip()
    elif soup.title and soup.title.string:
        title = soup.title.string.strip()

    section = soup.select_one("section.news_view")
    if not section:
        # fallback
        section = soup.select_one(".news_view") or soup.body

    # 제거 대상
    for tag in section.select("script, style, iframe, noscript"):
        tag.decompose()

    # 광고 컨테이너 패턴(너가 준 케이스 위주)
    for tag in section.select(".view_adK, .view_m_adK, ._adscopeBnFrm, ._adscopeOpt_wide"):
        tag.decompose()

    # 문단 우선 추출
    ps = [p.get_text(" ", strip=True) for p in section.find_all("p")]
    ps = [p.strip() for p in ps if p and p.strip()]

    if ps:
        paragraphs = ps
    else:
        raw = section.get_text("\n", strip=True)
        lines = clean_lines(raw)
        # 줄 단위가 너무 잘게 쪼개지면 문단으로 합치기(2줄씩)
        paragraphs = []
        buf: List[str] = []
        for ln in lines:
            buf.append(ln)
            if len(buf) >= 2:
                paragraphs.append(" ".join(buf))
                buf = []
        if buf:
            paragraphs.append(" ".join(buf))

    return (title, paragraphs)


def parse_article(url: str) -> Dict[str, Any]:
    html = fetch_html(url)

    source = "generic"
    title = ""
    paragraphs: List[str] = []

    if "donga.com" in url:
        source = "donga"
        title, paragraphs = extract_donga(html)
    else:
        # 최소 fallback: 전체 텍스트에서 줄 정리
        if BeautifulSoup:
            soup = BeautifulSoup(html, "html.parser")
            title = (soup.title.string.strip() if soup.title and soup.title.string else "")
            text = soup.get_text("\n", strip=True)
        else:
            text = re.sub(r"<[^>]+>", "\n", html)
        paragraphs = clean_lines(text)[:80]  # MVP용 안전컷

    paragraphs = [p for p in paragraphs if p.strip()]
    article_id = sha1_text(url)

    return {
        "article_id": article_id,
        "title": title,
        "source": source,
        "paragraphs": [{"id": f"p{i+1}", "text": p} for i, p in enumerate(paragraphs)],
    }


def upstage_headers():
    return {
        "Authorization": f"Bearer {UPSTAGE_API_KEY}",
        "Content-Type": "application/json",
    }


def extract_output_text(resp_json: Dict[str, Any]) -> str:
    # Responses API 예시 기준: output[].content[].type == "output_text"
    outs = resp_json.get("output") or []
    chunks: List[str] = []
    for item in outs:
        if item.get("type") != "message":
            continue
        content = item.get("content") or []
        for c in content:
            if c.get("type") == "output_text" and isinstance(c.get("text"), str):
                chunks.append(c["text"])
    return "\n".join(chunks).strip()


UPSTAGE_API_KEY = os.environ.get("UPSTAGE_API_KEY", "").strip()
UPSTAGE_MODEL = os.environ.get("UPSTAGE_MODEL", "solar-pro2").strip()
UPSTAGE_CHAT_URL = "https://api.upstage.ai/v1/chat/completions"

def upstage_headers():
    return {
        "Authorization": f"Bearer {UPSTAGE_API_KEY}",
        "Content-Type": "application/json",
    }

def call_solar_text(system_prompt: str, user_input: str) -> str:
    if not UPSTAGE_API_KEY:
        raise RuntimeError("UPSTAGE_API_KEY가 설정되지 않았습니다")

    payload = {
        "model": UPSTAGE_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
        "temperature": 0,
    }

    r = requests.post(UPSTAGE_CHAT_URL, headers=upstage_headers(), json=payload, timeout=30)
    if not r.ok:
        raise RuntimeError(f"Upstage API 오류: {r.status_code} {r.text}")

    data = r.json()
    return (data["choices"][0]["message"]["content"] or "").strip()

def call_solar_json(system_prompt: str, user_input: str, schema_name: str, schema: dict) -> dict:
    if not UPSTAGE_API_KEY:
        raise RuntimeError("UPSTAGE_API_KEY가 설정되지 않았습니다")

    payload = {
        "model": UPSTAGE_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
        "temperature": 0,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "schema": schema,
                "strict": True,
            },
        },
    }

    r = requests.post(UPSTAGE_CHAT_URL, headers=upstage_headers(), json=payload, timeout=30)
    if not r.ok:
        raise RuntimeError(f"Upstage API 오류: {r.status_code} {r.text}")

    data = r.json()
    txt = (data["choices"][0]["message"]["content"] or "").strip()
    if not txt:
        raise RuntimeError("빈 JSON 응답")

    return json.loads(txt)


@app.route("/api/article/parse", methods=["POST"])
def api_article_parse():
    body = request.get_json(silent=True) or {}
    url = str(body.get("url", "")).strip()

    if not url or not is_http_url(url):
        return jsonify({"error": "invalid url"}), 400

    try:
        data = parse_article(url)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/llm/explain", methods=["POST"])
def api_llm_explain():
    body = request.get_json(silent=True) or {}
    selection = str(body.get("selection", "")).strip()
    context_paragraphs = body.get("context_paragraphs") or []

    if not selection:
        return jsonify({"error": "no selection"}), 400

    context_text = ""
    if isinstance(context_paragraphs, list):
        ctx = [str(x).strip() for x in context_paragraphs if str(x).strip()]
        if ctx:
            context_text = "\n\n[주변 문맥]\n" + "\n".join(f"- {x}" for x in ctx)

    schema = {
        "type": "object",
        "properties": {
            "explanation": {"type": "string", "minLength": 1},
            "key_points": {"type": "array", "items": {"type": "string"}, "minItems": 0},
            "related_terms": {"type": "array", "items": {"type": "string"}, "minItems": 0},
        },
        "required": ["explanation", "key_points", "related_terms"],
        "additionalProperties": False,
    }

    instructions = (
        "너는 NIE(신문활용교육) 보조교사다. 사용자가 고른 뉴스 문장을 중학생도 이해할 수 있게 풀어서 설명하라. "
        "정치적 편향 없이 사실과 해석을 구분하고, 어려운 용어는 쉬운 말로 바꿔라. "
        "출력은 반드시 JSON 스키마를 따른다."
    )

    user_input = f"[선택 문장]\n{selection}{context_text}"

    try:
        out = call_solar_json(instructions, user_input, "nie_explain", schema)
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/llm/questions", methods=["POST"])
def api_llm_questions():
    body = request.get_json(silent=True) or {}
    focus_paragraphs = body.get("focus_paragraphs") or []

    if not isinstance(focus_paragraphs, list) or not focus_paragraphs:
        return jsonify({"error": "no focus_paragraphs"}), 400

    focus = [str(x).strip() for x in focus_paragraphs if str(x).strip()]
    if not focus:
        return jsonify({"error": "empty focus_paragraphs"}), 400

    schema = {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "minLength": 1},
                        "q": {"type": "string", "minLength": 1},
                    },
                    "required": ["type", "q"],
                    "additionalProperties": False,
                },
                "minItems": 3,
                "maxItems": 10,
            }
        },
        "required": ["questions"],
        "additionalProperties": False,
    }

    instructions = (
        "너는 NIE(신문활용교육) 보조교사다. 기사 일부를 보고 비판적 사고를 돕는 질문을 만들어라. "
        "질문 유형(type)은 claim-evidence, missing-info, alternative-view, data-check, impact 중에서 고르고, "
        "각 질문(q)은 학생이 답을 찾아보게 유도하는 형태로 짧고 구체적으로 써라. "
        "출력은 반드시 JSON 스키마를 따른다."
    )

    user_input = "[기사 발췌]\n" + "\n".join(f"- {p}" for p in focus)

    try:
        out = call_solar_json(instructions, user_input, "nie_questions", schema)
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/llm/vocab-lookup", methods=["POST"])
def api_llm_vocab_lookup():
    body = request.get_json(silent=True) or {}
    term = str(body.get("term", "")).strip()
    sentence = str(body.get("sentence", "")).strip()

    if not term:
        return jsonify({"error": "no term"}), 400

    schema = {
        "type": "object",
        "properties": {
            "definition": {"type": "string", "minLength": 1},
            "pos": {"type": "string"},
            "examples": {"type": "array", "items": {"type": "string"}, "minItems": 0, "maxItems": 3},
            "synonyms": {"type": "array", "items": {"type": "string"}, "minItems": 0, "maxItems": 5},
        },
        "required": ["definition", "pos", "examples", "synonyms"],
        "additionalProperties": False,
    }

    instructions = (
        "너는 NIE 단어장 도우미다. 용어를 중학생 수준으로 정의하고, 품사(pos)를 적고, "
        "해당 기사 문맥에 맞는 예문을 최대 3개 제공하라. 가능하면 쉬운 유사어도 제시하라. "
        "출력은 반드시 JSON 스키마를 따른다."
    )

    user_input = f"[단어]\n{term}\n\n[문맥 문장]\n{sentence}" if sentence else f"[단어]\n{term}"

    try:
        out = call_solar_json(instructions, user_input, "nie_vocab", schema)
        # 프론트에서 term을 따로 붙이지만, 있으면 같이 내려줌
        out_with_term = {"term": term, **out}
        return jsonify(out_with_term)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/vocab/add", methods=["POST"])
def api_vocab_add():
    ensure_db()
    body = request.get_json(silent=True) or {}

    term = str(body.get("term", "")).strip()
    if not term:
        return jsonify({"error": "no term"}), 400

    article_id = str(body.get("article_id", "")).strip() or None
    definition = str(body.get("definition", "")).strip() or None
    pos = str(body.get("pos", "")).strip() or None
    source_sentence = str(body.get("source_sentence", "")).strip() or None

    examples = body.get("examples")
    synonyms = body.get("synonyms")
    examples_json = json.dumps(examples if isinstance(examples, list) else [], ensure_ascii=False)
    synonyms_json = json.dumps(synonyms if isinstance(synonyms, list) else [], ensure_ascii=False)

    created_at = now_iso()

    with db_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO vocab (article_id, term, definition, pos, examples, synonyms, source_sentence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (article_id, term, definition, pos, examples_json, synonyms_json, source_sentence, created_at),
        )
        conn.commit()
        new_id = cur.lastrowid

    return jsonify({"ok": True, "id": new_id})


@app.route("/api/vocab/list", methods=["GET"])
def api_vocab_list():
    ensure_db()
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT id, article_id, term, definition, pos, examples, synonyms, source_sentence, created_at "
            "FROM vocab ORDER BY id DESC LIMIT 200"
        ).fetchall()

    items = []
    for r in rows:
        items.append(
            {
                "id": r["id"],
                "article_id": r["article_id"],
                "term": r["term"],
                "definition": r["definition"],
                "pos": r["pos"],
                "examples": json.loads(r["examples"] or "[]"),
                "synonyms": json.loads(r["synonyms"] or "[]"),
                "source_sentence": r["source_sentence"],
                "created_at": r["created_at"],
            }
        )

    return jsonify({"items": items})


@app.route("/api/vocab/<int:item_id>", methods=["DELETE"])
def api_vocab_delete(item_id: int):
    ensure_db()
    with db_conn() as conn:
        cur = conn.execute("DELETE FROM vocab WHERE id = ?", (item_id,))
        conn.commit()
        deleted = cur.rowcount

    return jsonify({"ok": True, "deleted": deleted})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True})


if __name__ == "__main__":
    ensure_db()
    app.run(port=8000, debug=True)
const API_BASE = "http://localhost:8000";

const urlInput = document.getElementById("urlInput");
const btnLoad = document.getElementById("btnLoad");

const articleEl = document.getElementById("article");
const articleMetaEl = document.getElementById("articleMeta");

const inputText = document.getElementById("inputText");
const btnExplain = document.getElementById("btnExplain");
const btnQuestions = document.getElementById("btnQuestions");
const btnVocabLookup = document.getElementById("btnVocabLookup");
const btnVocabSave = document.getElementById("btnVocabSave");

const statusEl = document.getElementById("status");

const modalBackdrop = document.getElementById("modalBackdrop");
const outputBox = document.getElementById("outputBox");
const btnClose = document.getElementById("btnClose");
const btnCopy = document.getElementById("btnCopy");

let 현재기사ID = "";
let 현재문단목록 = []; // [{id, text}]
let 마지막선택문단인덱스 = -1;
let 마지막단어조회결과 = null; // vocab-lookup 응답 저장 (save 버튼에서 사용)

function setStatus(text) {
  statusEl.textContent = text || "";
}

function openModal(text) {
  outputBox.textContent = text || "";
  modalBackdrop.style.display = "flex";
}
function closeModal() {
  modalBackdrop.style.display = "none";
}

btnClose.addEventListener("click", closeModal);
modalBackdrop.addEventListener("click", (e) => {
  if (e.target === modalBackdrop) closeModal();
});
btnCopy.addEventListener("click", async () => {
  await navigator.clipboard.writeText(outputBox.textContent || "");
  setStatus("복사 완료");
  setTimeout(() => setStatus(현재기사ID ? "기사 로드됨" : "대기"), 900);
});

function s(x) {
  return x === null || x === undefined ? "" : String(x);
}

function hasArticle() {
  return Boolean(현재기사ID) && Array.isArray(현재문단목록) && 현재문단목록.length > 0;
}

function 버튼상태업데이트() {
  const selection = inputText.value.trim();
  btnExplain.disabled = !hasArticle() || selection.length === 0;
  btnQuestions.disabled = !hasArticle();
  btnVocabLookup.disabled = !hasArticle();

  // save는 vocab lookup 결과가 있을 때만 활성화
  btnVocabSave.disabled = !hasArticle() || !마지막단어조회결과;
}

function 렌더기사() {
  articleEl.innerHTML = "";

  if (!현재기사ID) {
    articleMetaEl.textContent = "기사 URL을 입력하고 불러오세요.";
    버튼상태업데이트();
    return;
  }

  if (!현재문단목록.length) {
    articleMetaEl.textContent = "본문이 비어 있습니다.";
    버튼상태업데이트();
    return;
  }

  for (let i = 0; i < 현재문단목록.length; i++) {
    const p = 현재문단목록[i];
    const el = document.createElement("p");
    el.dataset.idx = String(i);
    el.dataset.pid = s(p?.id);
    el.textContent = s(p?.text);
    articleEl.appendChild(el);
  }

  버튼상태업데이트();
}

function 가장가까운문단엘리먼트(node) {
  if (!node) return null;
  let cur = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
  while (cur && cur !== articleEl) {
    if (cur.tagName === "P" && cur.dataset && cur.dataset.idx !== undefined) return cur;
    cur = cur.parentElement;
  }
  return null;
}

function 선택영역가져오기() {
  const sel = window.getSelection();
  if (!sel || sel.rangeCount === 0) return { text: "", idx: -1 };

  const range = sel.getRangeAt(0);
  if (!articleEl.contains(range.commonAncestorContainer)) return { text: "", idx: -1 };

  const text = sel.toString().trim();
  if (!text) return { text: "", idx: -1 };

  const pEl = 가장가까운문단엘리먼트(sel.anchorNode);
  const idx = pEl ? Number(pEl.dataset.idx) : -1;

  return { text, idx: Number.isFinite(idx) ? idx : -1 };
}

function 컨텍스트문단뽑기(centerIdx, windowSize = 1) {
  if (!Array.isArray(현재문단목록) || 현재문단목록.length === 0) return [];
  if (!Number.isInteger(centerIdx) || centerIdx < 0) return [];

  const start = Math.max(0, centerIdx - windowSize);
  const end = Math.min(현재문단목록.length - 1, centerIdx + windowSize);

  const out = [];
  for (let i = start; i <= end; i++) {
    const t = s(현재문단목록[i]?.text).trim();
    if (t) out.push(t);
  }
  return out;
}

async function postJson(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const msg = await res.text().catch(() => "");
    throw new Error(msg || `요청 실패: ${path}`);
  }
  return await res.json();
}

async function getJson(path) {
  const res = await fetch(`${API_BASE}${path}`, { method: "GET" });
  if (!res.ok) {
    const msg = await res.text().catch(() => "");
    throw new Error(msg || `요청 실패: ${path}`);
  }
  return await res.json();
}

function 설명응답포맷(data) {
  const explanation = s(data?.explanation).trim();
  const keyPoints = Array.isArray(data?.key_points) ? data.key_points : [];
  const related = Array.isArray(data?.related_terms) ? data.related_terms : [];

  let out = explanation || "(빈 응답)";
  if (keyPoints.length) {
    out += "\n\n[핵심 포인트]\n" + keyPoints.map((x) => "- " + s(x)).join("\n");
  }
  if (related.length) {
    out += "\n\n[관련 용어]\n" + related.map((x) => "- " + s(x)).join("\n");
  }
  return out;
}

function 질문응답포맷(data) {
  const qs = Array.isArray(data?.questions) ? data.questions : [];
  if (!qs.length) return "(질문이 없습니다)";

  // q: {type, q}
  return qs
    .map((x, i) => {
      const t = s(x?.type).trim();
      const q = s(x?.q).trim();
      const head = t ? `[${t}]` : `[Q${i + 1}]`;
      return `${head} ${q || "(빈 질문)"}`;
    })
    .join("\n\n");
}

function 단어응답포맷(data) {
  const term = s(data?.term).trim();
  const pos = s(data?.pos).trim();
  const definition = s(data?.definition).trim();
  const examples = Array.isArray(data?.examples) ? data.examples : [];
  const synonyms = Array.isArray(data?.synonyms) ? data.synonyms : [];

  let out = (term ? term : "(term 없음)") + (pos ? ` (${pos})` : "");
  out += "\n\n" + (definition || "(정의 없음)");

  if (examples.length) {
    out += "\n\n[예문]\n" + examples.map((x) => "- " + s(x)).join("\n");
  }
  if (synonyms.length) {
    out += "\n\n[유사어]\n" + synonyms.map((x) => "- " + s(x)).join("\n");
  }
  return out;
}

function 단어후보선정() {
  const selection = inputText.value.trim();
  // 선택 텍스트가 단어 하나처럼 보이면 그대로 사용
  if (selection && !/\s/.test(selection) && selection.length <= 40) return selection;

  const term = window.prompt("단어를 입력하세요");
  return term ? term.trim() : "";
}

btnLoad.addEventListener("click", async () => {
  const url = urlInput.value.trim();
  if (!url) return openModal("URL을 입력하세요.");

  btnLoad.disabled = true;
  setStatus("기사 불러오는 중");
  마지막단어조회결과 = null;

  try {
    const data = await postJson("/api/article/parse", { url });

    현재기사ID = s(data?.article_id);
    const title = s(data?.title);
    const source = s(data?.source);

    현재문단목록 = Array.isArray(data?.paragraphs) ? data.paragraphs : [];
    마지막선택문단인덱스 = -1;

    articleMetaEl.textContent = (title ? title : "제목 없음") + (source ? ` | ${source}` : "");
    렌더기사();
    setStatus("기사 로드됨");
  } catch (err) {
    현재기사ID = "";
    현재문단목록 = [];
    마지막선택문단인덱스 = -1;
    렌더기사();
    openModal("오류: " + (err?.message || String(err)));
    setStatus("실패");
  } finally {
    btnLoad.disabled = false;
    버튼상태업데이트();
  }
});

document.addEventListener("selectionchange", () => {
  const { text, idx } = 선택영역가져오기();
  if (text) {
    inputText.value = text;
    마지막선택문단인덱스 = idx;
  }
  버튼상태업데이트();
});

inputText.addEventListener("input", 버튼상태업데이트);

btnExplain.addEventListener("click", async () => {
  const selection = inputText.value.trim();
  if (!selection) return;

  btnExplain.disabled = true;
  setStatus("설명 생성 중");

  try {
    const context = 컨텍스트문단뽑기(마지막선택문단인덱스, 1);
    const data = await postJson("/api/llm/explain", {
      article_id: 현재기사ID,
      selection,
      context_paragraphs: context,
    });

    openModal(설명응답포맷(data));
    setStatus("완료");
  } catch (err) {
    openModal("오류: " + (err?.message || String(err)));
    setStatus("실패");
  } finally {
    setTimeout(() => setStatus(현재기사ID ? "기사 로드됨" : "대기"), 900);
    버튼상태업데이트();
  }
});

btnQuestions.addEventListener("click", async () => {
  if (!hasArticle()) return;

  btnQuestions.disabled = true;
  setStatus("질문 생성 중");

  try {
    // 선택 문단 중심으로 질문 생성, 선택이 없으면 전체 기사 기반
    let focus = 컨텍스트문단뽑기(마지막선택문단인덱스, 2);
    if (!focus.length) {
      focus = 현재문단목록.map((p) => s(p?.text)).filter((x) => x.trim().length > 0);
    }

    const data = await postJson("/api/llm/questions", {
      article_id: 현재기사ID,
      focus_paragraphs: focus,
    });

    openModal(질문응답포맷(data));
    setStatus("완료");
  } catch (err) {
    openModal("오류: " + (err?.message || String(err)));
    setStatus("실패");
  } finally {
    setTimeout(() => setStatus(현재기사ID ? "기사 로드됨" : "대기"), 900);
    버튼상태업데이트();
  }
});

btnVocabLookup.addEventListener("click", async () => {
  if (!hasArticle()) return;

  const term = 단어후보선정();
  if (!term) return;

  btnVocabLookup.disabled = true;
  setStatus("단어 조회 중");
  마지막단어조회결과 = null;

  try {
    const sentence = s(현재문단목록[마지막선택문단인덱스]?.text).trim();

    const data = await postJson("/api/llm/vocab-lookup", {
      article_id: 현재기사ID,
      term,
      sentence: sentence || inputText.value.trim(),
    });

    // save 버튼용으로 보관
    마지막단어조회결과 = { ...data, term };

    openModal(단어응답포맷(마지막단어조회결과));
    setStatus("완료");
  } catch (err) {
    openModal("오류: " + (err?.message || String(err)));
    setStatus("실패");
  } finally {
    setTimeout(() => setStatus(현재기사ID ? "기사 로드됨" : "대기"), 900);
    버튼상태업데이트();
  }
});

btnVocabSave.addEventListener("click", async () => {
  if (!hasArticle() || !마지막단어조회결과) return;

  btnVocabSave.disabled = true;
  setStatus("단어 저장 중");

  try {
    // 최소 저장 payload. db 세션에서 맞춰서 스키마 조정하면 됨.
    const payload = {
      article_id: 현재기사ID,
      term: s(마지막단어조회결과?.term).trim(),
      definition: s(마지막단어조회결과?.definition).trim(),
      pos: s(마지막단어조회결과?.pos).trim(),
      examples: Array.isArray(마지막단어조회결과?.examples) ? 마지막단어조회결과.examples : [],
      synonyms: Array.isArray(마지막단어조회결과?.synonyms) ? 마지막단어조회결과.synonyms : [],
      source_sentence: s(현재문단목록[마지막선택문단인덱스]?.text).trim(),
    };

    await postJson("/api/vocab/add", payload);

    // 저장 성공하면 목록을 한번 보여줌 (MVP 디버그용)
    let listText = "저장 완료";
    try {
      const list = await getJson("/api/vocab/list");
      const items = Array.isArray(list?.items) ? list.items : [];
      if (items.length) {
        listText += "\n\n[단어장]\n" + items.map((x) => `- ${s(x?.term)}: ${s(x?.definition)}`).join("\n");
      }
    } catch (_) {
      // list가 아직 없으면 무시
    }

    openModal(listText);
    setStatus("완료");
  } catch (err) {
    openModal("오류: " + (err?.message || String(err)));
    setStatus("실패");
  } finally {
    setTimeout(() => setStatus(현재기사ID ? "기사 로드됨" : "대기"), 900);
    버튼상태업데이트();
  }
});

// 초기 상태
setStatus("대기");
버튼상태업데이트();
렌더기사();
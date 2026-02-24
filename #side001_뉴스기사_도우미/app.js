const fileInput = document.getElementById("fileInput");
const articleEl = document.getElementById("article");
const articleMetaEl = document.getElementById("articleMeta");
const inputText = document.getElementById("inputText");
const btnParaphrase = document.getElementById("btnParaphrase");
const statusEl = document.getElementById("status");
const btnPrev = document.getElementById("btnPrev");
const btnNext = document.getElementById("btnNext");
const topicBar = document.getElementById("topicBar");

const modalBackdrop = document.getElementById("modalBackdrop");
const outputBox = document.getElementById("outputBox");
const btnClose = document.getElementById("btnClose");
const btnCopy = document.getElementById("btnCopy");

const TOPICS = ["사회", "경제", "생활", "정치", "IT/과학", "미용/건강", "스포츠", "문화", "연예"];

let 선택토픽 = "";
let 전체문서목록 = [];
let 기사목록 = [];
let 현재인덱스 = 0;

function setStatus(text) {
  statusEl.textContent = text;
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
  setTimeout(() => setStatus(선택토픽 ? `토픽: ${선택토픽}` : "토픽 선택"), 900);
});

function 안전한문자열(x) {
  return x === null || x === undefined ? "" : String(x);
}

function form만추출해서기사텍스트(doc) {
  const paragraphs = Array.isArray(doc?.paragraph) ? doc.paragraph : [];
  const forms = paragraphs
    .map((p) => 안전한문자열(p?.form).trim())
    .filter(Boolean);
  return forms.join("\n\n");
}

function 렌더기사() {
  // 토픽 선택 전
  if (!선택토픽) {
    articleMetaEl.textContent = "토픽을 먼저 선택하세요.";
    articleEl.textContent = "";
    btnPrev.disabled = true;
    btnNext.disabled = true;
    fileInput.disabled = true;
    btnParaphrase.disabled = inputText.value.trim().length === 0;
    return;
  }

  // 토픽은 선택됐지만 기사 없음
  if (!기사목록.length) {
    articleMetaEl.textContent = `${선택토픽} 토픽 기사가 없습니다.`;
    articleEl.textContent = "";
    btnPrev.disabled = true;
    btnNext.disabled = true;
    btnParaphrase.disabled = inputText.value.trim().length === 0;
    return;
  }

  // 정상 렌더
  const doc = 기사목록[현재인덱스];

  const title = 안전한문자열(doc?.metadata?.title);
  const author = 안전한문자열(doc?.metadata?.author);
  const publisher = 안전한문자열(doc?.metadata?.publisher);
  const date = 안전한문자열(doc?.metadata?.date);
  const idxInfo = `${현재인덱스 + 1}/${기사목록.length}`;

  articleMetaEl.textContent =
    `[${idxInfo}] ${title}` +
    (publisher ? " | " + publisher : "") +
    (author ? " | " + author : "") +
    (date ? " | " + date : "");

  articleEl.textContent = form만추출해서기사텍스트(doc);

  btnPrev.disabled = 현재인덱스 === 0;
  btnNext.disabled = 현재인덱스 === 기사목록.length - 1;

  btnParaphrase.disabled = inputText.value.trim().length === 0;
}

function applyFilterAndRender() {
  if (!선택토픽) {
    기사목록 = [];
    현재인덱스 = 0;
    렌더기사();
    return;
  }

  기사목록 = 전체문서목록.filter((d) => 안전한문자열(d?.metadata?.topic) === 선택토픽);
  현재인덱스 = 0;
  렌더기사();
}

function renderTopicButtons() {
  topicBar.innerHTML = "";

  for (const t of TOPICS) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "topic-btn" + (t === 선택토픽 ? " active" : "");
    btn.textContent = t;

    btn.addEventListener("click", () => {
      선택토픽 = t;
      setStatus(`토픽: ${선택토픽}`);
      fileInput.disabled = false;

      if (전체문서목록.length) {
        applyFilterAndRender();
      } else {
        렌더기사();
      }

      renderTopicButtons();
    });

    topicBar.appendChild(btn);
  }
}

fileInput.addEventListener("change", async (e) => {
  const file = e.target.files?.[0];
  if (!file) return;

  if (!선택토픽) {
    openModal("먼저 토픽을 선택하세요.");
    return;
  }

  setStatus("로딩 중");

  try {
    const raw = await file.text();
    const json = JSON.parse(raw);

    전체문서목록 = Array.isArray(json?.document) ? json.document : [];
    applyFilterAndRender();

    setStatus(`파일 로드됨: ${선택토픽}`);
  } catch (err) {
    전체문서목록 = [];
    기사목록 = [];
    현재인덱스 = 0;
    렌더기사();
    openModal("JSON 파싱 오류: " + (err?.message || String(err)));
    setStatus("실패");
    setTimeout(() => setStatus(`토픽: ${선택토픽}`), 900);
  }
});

btnPrev.addEventListener("click", () => {
  if (현재인덱스 > 0) {
    현재인덱스 -= 1;
    렌더기사();
  }
});

btnNext.addEventListener("click", () => {
  if (현재인덱스 < 기사목록.length - 1) {
    현재인덱스 += 1;
    렌더기사();
  }
});

function getSelectedTextInArticle() {
  const sel = window.getSelection();
  if (!sel || sel.rangeCount === 0) return "";
  const range = sel.getRangeAt(0);
  if (!articleEl.contains(range.commonAncestorContainer)) return "";
  return sel.toString().trim();
}

document.addEventListener("selectionchange", () => {
  const selected = getSelectedTextInArticle();
  if (selected) {
    inputText.value = selected;
    btnParaphrase.disabled = false;
  } else {
    btnParaphrase.disabled = inputText.value.trim().length === 0;
  }
});

inputText.addEventListener("input", () => {
  btnParaphrase.disabled = inputText.value.trim().length === 0;
});

async function paraphrase(text) {
  const res = await fetch("http://localhost:8000/paraphrase", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });

  if (!res.ok) {
    throw new Error("서버 오류");
  }

  const data = await res.json();
  return data.output;
}

btnParaphrase.addEventListener("click", async () => {
  const text = inputText.value.trim();
  if (!text) return;

  btnParaphrase.disabled = true;
  setStatus("변환 중");

  try {
    const out = await paraphrase(text);
    openModal(out);
    setStatus("완료");
  } catch (err) {
    openModal("오류: " + (err?.message || String(err)));
    setStatus("실패");
  } finally {
    btnParaphrase.disabled = inputText.value.trim().length === 0;
    setTimeout(() => setStatus(선택토픽 ? `토픽: ${선택토픽}` : "토픽 선택"), 900);
  }
});

// 초기 상태
renderTopicButtons();
렌더기사();
setStatus("토픽 선택");

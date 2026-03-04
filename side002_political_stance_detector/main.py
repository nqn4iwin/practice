import sys
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

MODEL_DIR = "./redblue_cls"
device = "cuda" if torch.cuda.is_available() else "cpu"

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR).to(device).eval()

# config에서 라벨 매핑을 신뢰
id2label = {int(k): v for k, v in model.config.id2label.items()} if isinstance(model.config.id2label, dict) else dict(model.config.id2label)
label2id = dict(model.config.label2id) if isinstance(model.config.label2id, dict) else dict(model.config.label2id)

@torch.inference_mode()
def predict_proba(texts, max_length=256):
    if isinstance(texts, str):
        texts = [texts]

    enc = tokenizer(
        texts,
        truncation=True,
        padding=True,
        max_length=max_length,
        return_tensors="pt",
    )
    enc = {k: v.to(device) for k, v in enc.items()}

    logits = model(**enc).logits
    probs = torch.softmax(logits, dim=-1).cpu().tolist()

    out = []
    for p in probs:
        d = {id2label[i]: float(p[i]) for i in range(len(p))}
        out.append(d)
    return out

if __name__ == "__main__":
    # 사용법: uv run python main.py "문장"
    if len(sys.argv) >= 2:
        text = " ".join(sys.argv[1:]).strip()
    else:
        text = "윤석열"

    print("label2id =", label2id)
    print("id2label =", id2label)
    print(predict_proba(text)[0])
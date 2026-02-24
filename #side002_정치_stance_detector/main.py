import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

MODEL_DIR = "./redblue_cls"  # 압축 풀린 폴더 경로

device = "cuda" if torch.cuda.is_available() else "cpu"

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR).to(device).eval()

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
    probs = torch.softmax(logits, dim=-1).cpu().numpy()

    # label2id를 학습 때 {"red":0,"blue":1}로 썼다는 가정
    out = []
    for p in probs:
        out.append({"red": float(p[0]), "blue": float(p[1])})
    return out

if __name__ == "__main__":
    x = "북한"
    print(predict_proba(x)[0])

from __future__ import annotations

import json
import math
import random
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.config import Config
from src.text.tokenize_ko import KoreanTokenizer
from src.text.preprocess import load_json_list

def _sample_pairs(
    idx_a: list[int],
    idx_b: list[int],
    sample_size: int | None,
    rng: random.Random,
    same_group: bool,
) -> list[tuple[int, int]]:
    # same_group이면 (i<j)로 중복/자기자신 제외
    pairs: list[tuple[int, int]] = []

    if sample_size is None:
        if same_group:
            for i_pos in range(len(idx_a)):
                for j_pos in range(i_pos + 1, len(idx_a)):
                    pairs.append((idx_a[i_pos], idx_a[j_pos]))
        else:
            for i in idx_a:
                for j in idx_b:
                    pairs.append((i, j))
        return pairs

    # 샘플링 모드
    if same_group:
        if len(idx_a) < 2:
            return []
        for _ in range(sample_size):
            i, j = rng.sample(idx_a, 2)
            if i == j:
                continue
            if i > j:
                i, j = j, i
            pairs.append((i, j))
    else:
        if not idx_a or not idx_b:
            return []
        for _ in range(sample_size):
            i = rng.choice(idx_a)
            j = rng.choice(idx_b)
            pairs.append((i, j))

    return pairs


def _mean_std(x: list[float]) -> dict[str, float]:
    if not x:
        return {"mean": float("nan"), "std": float("nan"), "n": 0}
    arr = np.array(x, dtype=np.float64)
    return {"mean": float(arr.mean()), "std": float(arr.std(ddof=1) if len(arr) > 1 else 0.0), "n": int(len(arr))}


def run_similarity(cfg: Config) -> None:
    out_dir = cfg.outputs_dir / "similarity"
    examples = load_json_list(cfg.data_path)

    texts = [ex.text for ex in examples]
    labels = [ex.label for ex in examples]

    red_idx = [i for i, y in enumerate(labels) if y == cfg.red_label]
    blue_idx = [i for i, y in enumerate(labels) if y == cfg.blue_label]

    rng = random.Random(cfg.random_seed)

    rr_pairs = _sample_pairs(red_idx, red_idx, cfg.pair_sample_size, rng, same_group=True)
    bb_pairs = _sample_pairs(blue_idx, blue_idx, cfg.pair_sample_size, rng, same_group=True)
    rb_pairs = _sample_pairs(red_idx, blue_idx, cfg.pair_sample_size, rng, same_group=False)

    # 1) TF-IDF cosine
    tfidf = TfidfVectorizer(ngram_range=(1, 2), min_df=2)
    X = tfidf.fit_transform(texts)

    def tfidf_cos(pairs: list[tuple[int, int]]) -> list[float]:
        if not pairs:
            return []
        vals: list[float] = []
        for i, j in pairs:
            sim = cosine_similarity(X[i], X[j])[0, 0]
            vals.append(float(sim))
        return vals

    rr_tfidf = tfidf_cos(rr_pairs)
    bb_tfidf = tfidf_cos(bb_pairs)
    rb_tfidf = tfidf_cos(rb_pairs)

    # 2) SentenceTransformer cosine
    st = SentenceTransformer(cfg.st_model_name)
    emb = st.encode(texts, batch_size=cfg.st_batch_size, normalize_embeddings=True, show_progress_bar=True)

    def st_cos(pairs: list[tuple[int, int]]) -> list[float]:
        if not pairs:
            return []
        vals: list[float] = []
        for i, j in pairs:
            # normalize_embeddings=True라 내적이 cosine
            vals.append(float(np.dot(emb[i], emb[j])))
        return vals

    rr_st = st_cos(rr_pairs)
    bb_st = st_cos(bb_pairs)
    rb_st = st_cos(rb_pairs)

    # 3) BM25 (토큰 기반)
    tokenizer = KoreanTokenizer.build(cfg)
    tokenized = [tokenizer.word_tokens(t) for t in texts]
    bm25 = BM25Okapi(tokenized)

    def bm25_pair(pairs: list[tuple[int, int]]) -> list[float]:
        if not pairs:
            return []
        vals: list[float] = []
        for i, j in pairs:
            # query = tokenized[j] 로 전체 문서 점수 벡터를 받고 i번째를 뽑음
            scores_ji = bm25.get_scores(tokenized[j])
            s1 = float(scores_ji[i])

            scores_ij = bm25.get_scores(tokenized[i])
            s2 = float(scores_ij[j])

            vals.append((s1 + s2) / 2.0)
        return vals

    rr_bm25 = bm25_pair(rr_pairs)
    bb_bm25 = bm25_pair(bb_pairs)
    rb_bm25 = bm25_pair(rb_pairs)

    summary = {
        "pair_counts": {
            "red_red": len(rr_pairs),
            "blue_blue": len(bb_pairs),
            "red_blue": len(rb_pairs),
        },
        "tfidf_cosine": {
            "red_red": _mean_std(rr_tfidf),
            "blue_blue": _mean_std(bb_tfidf),
            "red_blue": _mean_std(rb_tfidf),
        },
        "sentence_transformer_cosine": {
            "red_red": _mean_std(rr_st),
            "blue_blue": _mean_std(bb_st),
            "red_blue": _mean_std(rb_st),
        },
        "bm25_score": {
            "red_red": _mean_std(rr_bm25),
            "blue_blue": _mean_std(bb_bm25),
            "red_blue": _mean_std(rb_bm25),
        },
    }

    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # CSV도 같이
    rows = []
    for metric, block in [
        ("tfidf_cosine", summary["tfidf_cosine"]),
        ("sentence_transformer_cosine", summary["sentence_transformer_cosine"]),
        ("bm25_score", summary["bm25_score"]),
    ]:
        for pair_name, stat in block.items():
            rows.append({"metric": metric, "pair": pair_name, **stat})
    pd.DataFrame(rows).to_csv(out_dir / "summary.csv", index=False, encoding="utf-8-sig")
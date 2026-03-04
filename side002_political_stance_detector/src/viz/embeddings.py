# src/viz/embeddings.py
# embeddings.py - train a single Word2Vec and plot red/blue words together (Korean font-safe)

from __future__ import annotations

from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import umap
from gensim.models import Word2Vec
from matplotlib.font_manager import FontProperties

from src.config import Config
from src.text.preprocess import load_json_list
from src.text.tokenize_ko import KoreanTokenizer


def _train_w2v(all_token_seqs: list[list[str]], cfg: Config) -> Word2Vec:
    return Word2Vec(
        sentences=all_token_seqs,
        vector_size=cfg.w2v_vector_size,
        window=cfg.w2v_window,
        min_count=cfg.w2v_min_count,
        workers=cfg.w2v_workers,
        sg=1,
        epochs=cfg.w2v_epochs,
    )


def _top_vocab(token_seqs: list[list[str]], top_n: int) -> list[str]:
    c = Counter()
    for seq in token_seqs:
        c.update(seq)
    return [w for w, _ in c.most_common(top_n)]


def run_embeddings(cfg: Config) -> None:
    out_dir = cfg.outputs_dir / "embeddings"
    out_dir.mkdir(parents=True, exist_ok=True)

    examples = load_json_list(cfg.data_path)

    # FontProperties로 텍스트에 직접 강제 적용 (DejaVu 폴백 방지)
    font_prop: FontProperties | None = None
    if cfg.font_path and cfg.font_path.exists():
        font_prop = FontProperties(fname=str(cfg.font_path))
        print("Using font file:", cfg.font_path)
    else:
        print("Font missing (matplotlib will fallback):", cfg.font_path)

    tokenizer = KoreanTokenizer.build(cfg)

    red_texts = [ex.text for ex in examples if ex.label == cfg.red_label]
    blue_texts = [ex.text for ex in examples if ex.label == cfg.blue_label]

    red_tokens = [tokenizer.word_tokens(t) for t in red_texts]
    blue_tokens = [tokenizer.word_tokens(t) for t in blue_texts]
    all_tokens = red_tokens + blue_tokens

    # 단어 수는 "지금의 절반"
    # 기존 cfg.embed_top_n이 150이었다면 -> 75 사용
    per_label_n = max(1, cfg.embed_top_n // 2)

    model = _train_w2v(all_tokens, cfg)

    # 라벨별 top 후보를 더 넉넉히 뽑고, 모델 vocab에 있는 것만 필터링
    red_vocab = [w for w in _top_vocab(red_tokens, per_label_n * 3) if w in model.wv][:per_label_n]
    blue_vocab = [w for w in _top_vocab(blue_tokens, per_label_n * 3) if w in model.wv][:per_label_n]

    words = red_vocab + blue_vocab
    if not words:
        print("No vocab available for plotting (check tokenization/min_count).")
        return

    vectors = np.vstack([model.wv[w] for w in words])

    reducer = umap.UMAP(
        n_neighbors=cfg.umap_n_neighbors,
        min_dist=cfg.umap_min_dist,
        metric="cosine",
        random_state=cfg.random_seed,
    )
    xy = reducer.fit_transform(vectors)

    plt.figure(figsize=(14, 10))

    # 색: red/blue로 분리
    red_xy = xy[: len(red_vocab)]
    blue_xy = xy[len(red_vocab) :]

    if len(red_vocab) > 0:
        plt.scatter(red_xy[:, 0], red_xy[:, 1], s=18, c="red", alpha=0.65, label="red")
    if len(blue_vocab) > 0:
        plt.scatter(blue_xy[:, 0], blue_xy[:, 1], s=18, c="blue", alpha=0.65, label="blue")

    # 라벨 텍스트
    for i, w in enumerate(words):
        if font_prop is not None:
            plt.text(xy[i, 0], xy[i, 1], w, fontsize=8, fontproperties=font_prop)
        else:
            plt.text(xy[i, 0], xy[i, 1], w, fontsize=8)

    title = f"Word2Vec (UMAP) red vs blue (top {per_label_n} each)"
    if font_prop is not None:
        plt.title(title, fontproperties=font_prop)
    else:
        plt.title(title)

    plt.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "red_blue_w2v.png", dpi=220)
    plt.close()
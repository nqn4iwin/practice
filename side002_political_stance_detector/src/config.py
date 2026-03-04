from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    # Paths
    project_root: Path = Path(__file__).resolve().parents[1]
    data_path: Path = project_root / "data" / "test.json"
    outputs_dir: Path = project_root / "outputs"
    font_path: Path = project_root / "NanumBarunGothic.ttf"

    # Labels
    red_label: str = "red"
    blue_label: str = "blue"

    # Similarity sampling
    # 전체쌍(O(n^2)) 대신 샘플링 권장. None이면 가능한 전체쌍(작을 때만).
    pair_sample_size: int | None = 30000
    random_seed: int = 42

    # Sentence embedding model (CPU 가능)
    # 한국어 포함 멀티링구얼 범용
    st_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    st_batch_size: int = 64

    # Tokenization
    min_token_len: int = 2
    keep_pos: tuple[str, ...] = ("Noun", "Adjective")  # Okt pos tags
    max_tokens_per_doc: int | None = None  # 너무 길면 자르기(필요 시)

    # HF tokenizer (for future model tokenization)
    hf_tokenizer_name: str = "klue/roberta-base"

    # Wordcloud
    wordcloud_max_words: int = 200

    # Word2Vec + projection
    w2v_vector_size: int = 100
    w2v_window: int = 5
    w2v_min_count: int = 3
    w2v_workers: int = 4
    w2v_epochs: int = 20
    embed_top_n: int = 150
    umap_n_neighbors: int = 15
    umap_min_dist: float = 0.1
from __future__ import annotations

from pathlib import Path

from src.config import Config
from src.similarity.compute_similarity import run_similarity
from src.viz.wordclouds import run_wordclouds
from src.viz.embeddings import run_embeddings


def _ensure_dirs(cfg: Config) -> None:
    (cfg.outputs_dir / "similarity").mkdir(parents=True, exist_ok=True)
    (cfg.outputs_dir / "wordcloud").mkdir(parents=True, exist_ok=True)
    (cfg.outputs_dir / "embeddings").mkdir(parents=True, exist_ok=True)


def main() -> None:
    cfg = Config()
    _ensure_dirs(cfg)

    run_similarity(cfg)
    run_wordclouds(cfg)
    run_embeddings(cfg)


if __name__ == "__main__":
    main()
# src/viz/wordclouds.py
# wordclouds.py - wordclouds for red and blue (Korean font + color palettes)

from __future__ import annotations

import random
from collections import Counter
from pathlib import Path
from typing import Callable

import matplotlib.pyplot as plt
import pandas as pd
from wordcloud import WordCloud

from src.config import Config
from src.text.preprocess import load_json_list
from src.text.tokenize_ko import KoreanTokenizer


def _build_freq(texts: list[str], tokenizer: KoreanTokenizer) -> Counter[str]:
    c: Counter[str] = Counter()
    for t in texts:
        c.update(tokenizer.word_tokens(t))
    return c


def _make_color_func(palette: list[tuple[int, int, int]]) -> Callable:
    rng = random.Random(42)

    def color_func(word, font_size, position, orientation, random_state=None, **kwargs):
        r, g, b = rng.choice(palette)
        return f"rgb({r},{g},{b})"

    return color_func


def _save_wordcloud(freq: Counter[str], out_path: Path, *, title: str, cfg: Config, color_func: Callable) -> None:
    # WordCloud는 font_path를 반드시 줘야 한글이 안 깨짐
    wc = WordCloud(
        width=1400,
        height=900,
        background_color="white",
        max_words=cfg.wordcloud_max_words,
        collocations=False,
        font_path=str(cfg.font_path) if cfg.font_path and cfg.font_path.exists() else None,
        prefer_horizontal=0.9,
        random_state=cfg.random_seed,
    ).generate_from_frequencies(dict(freq))

    wc = wc.recolor(color_func=color_func, random_state=cfg.random_seed)

    plt.figure(figsize=(14, 9))
    plt.imshow(wc, interpolation="bilinear")
    plt.axis("off")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(out_path, dpi=220)
    plt.close()


def run_wordclouds(cfg: Config) -> None:
    out_dir = cfg.outputs_dir / "wordcloud"
    out_dir.mkdir(parents=True, exist_ok=True)

    examples = load_json_list(cfg.data_path)
    red_texts = [ex.text for ex in examples if ex.label == cfg.red_label]
    blue_texts = [ex.text for ex in examples if ex.label == cfg.blue_label]

    tokenizer = KoreanTokenizer.build(cfg)

    red_freq = _build_freq(red_texts, tokenizer)
    blue_freq = _build_freq(blue_texts, tokenizer)

    # 같은 계열에서 채도/명도만 다르게 (구별은 되되 톤 유지)
    red_palette = [
        (180, 20, 20),
        (210, 30, 30),
        (230, 50, 50),
        (150, 10, 10),
        (255, 80, 80),
    ]
    blue_palette = [
        (20, 60, 180),
        (30, 90, 210),
        (50, 120, 230),
        (10, 40, 150),
        (80, 160, 255),
    ]

    _save_wordcloud(
        red_freq,
        out_dir / "red.png",
        title="red wordcloud",
        cfg=cfg,
        color_func=_make_color_func(red_palette),
    )
    _save_wordcloud(
        blue_freq,
        out_dir / "blue.png",
        title="blue wordcloud",
        cfg=cfg,
        color_func=_make_color_func(blue_palette),
    )

    pd.DataFrame(red_freq.most_common(200), columns=["token", "count"]).to_csv(
        out_dir / "red_top_terms.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(blue_freq.most_common(200), columns=["token", "count"]).to_csv(
        out_dir / "blue_top_terms.csv", index=False, encoding="utf-8-sig"
    )
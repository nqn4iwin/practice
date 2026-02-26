## 프로젝트 설명
original : mBERT를 LoRA로 파인튜닝해 IMDB 영화 리뷰 감성 분류(긍정/부정)
current : 한국 영화에 대한 언어별/문화권별 반응 차이

## 구조
Cinema-of-Korean-global-perception/
  README.md
  requirements.txt

  data/
    raw/                 # 크롤링 결과
    processed/           # 정제 + langdetect + split

  src/
    crawl.py             # Letterboxd 크롤링 + 파싱
    preprocess.py        # 정제 + 언어탐지 + split
    inference.py         # 감성 예측
    embed.py             # XLM-R embedding 추출
    analysis.py          # centroid / distance / UMAP / 키워드

  notebooks/
    train_xlmr.ipynb     # Colab에서 XLMR 학습한 파일
    analysis.ipynb       # 결과 확인용

  outputs/
    figures/
    tables/

## 주의사항
모델 학습은 Colab 환경에서 실행함(notebooks/train_xlmr.ipynb)
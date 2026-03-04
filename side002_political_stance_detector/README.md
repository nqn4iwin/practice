# Political Stance Detector (red vs blue)

이 프로젝트는 한국의 2개 대표 정당(더불어민주당, 국민의힘) 국회의원의 발언 데이터를 대상으로
"두 정당은 서로 얼마나 다른 언어를 사용하고 있는가?" 를 분석합니다.

1) 인코더 모델 학습: KLUE-RoBERTa(base)로 입력받은 문장에 대한 정당 이진분류기 구현
2) 평균 유사도: `red-red`, `blue-blue`, `red-blue` 관계를 3개의 유사도 지표로 계산  
3) 워드클라우드: red / blue 최다빈도 단어를 워드클라우드로 생성  
4) 워드 임베딩 시각화: Word2Vec + UMAP 기반 시각화(각 정당 별 75개 최다빈도 단어로)

---

## 입력 데이터 형식

입력 파일 `data/train|valid|test.json`

예시:
```json
[
  {"label": "red", "text": "유 전 의원은 대구에서 여전히 ‘배신자 프레임’을 벗지 못했다"},
  {"label": "blue", "text": "야당 의원들이 7월 초부터 ..."}
]
```

---

## 폴더 구조

```
root/
  data/
    test.json
    train.json
    valid.json

  main.py                    # 1번, colab에서 미리 학습된 KLUE-RoBERTa(base) 이진분류기
  redblue_cls/
    config.json
    tokenizer.json
    tokenizer_config.json
    training_args.bin
    model.safetensors        # 크기가 커서 깃허브에는 안올라갑니다ㅠㅠ 실습을 원하시면 말씀해주세요!

  src/                       # 2~4번, 유사도/워드클라우드/워드임베딩
    run_all.py
    config.py
    text/
      preprocess.py
      tokenize_ko.py         # kiwi 형태소분석기를 사용하였습니다. uv 환경에서는 잘 안될수도 있습니다ㅠㅠ
    similarity/              # 유사도 측정
      compute_similarity.py
    viz/                     # 시각화(wordcloud, word embedding)
      wordclouds.py
      embeddings.py
  outputs/                   # 2~4번 결과물
    similarity/
    wordcloud/
    embeddings/

  NanumBarunGothic.ttf       # 워드클라우드, 워드임베딩 시각화용 한글폰트
  stance_detector.ipynb      # colab에서 학습시킨 코드
```

---

## 실행 (Windows + uv)

환경 설치/동기화:
```powershell
uv sync
```

1번 실행:
```powershell
uv run python .\main.py "국민의 삶을 지키는 민생 중심의 정책으로 촛불 정신을 완수하겠다."
```

2~4번 실행:
```powershell
uv run python -m src.run_all
```

---

## 결과물

- `outputs/similarity/summary.json`
- `outputs/similarity/summary.csv`
- `outputs/wordcloud/red.png`
- `outputs/wordcloud/blue.png`
- `outputs/embeddings/red_blue_w2v.png`  
  (현재 `src/viz/embeddings.py` 구현에 따라 파일명이 다를 수 있음)

TL;DR "2개 정당 소속 국회의원의 발화는 의미적 유사도, 워드클라우드, 워드임베딩에서 큰 차이를 보이지 않습니다"

---

## 유사도 지표(3종)

아래 3개 계열로 `red-red`, `blue-blue`, `red-blue` 평균을 비교합니다.

- **TF-IDF cosine**: 표면 어휘 중복 기반(가벼움)
- **SentenceTransformer cosine**: 문장 임베딩 기반(의미 유사도)
- **BM25 score**: 토큰 기반 정보검색 점수

---

### 이슈/트러블슈팅
nqn4iwin@gmail.com 또는 디스코드 DM으로 연락주세요!
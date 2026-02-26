# 프로젝트: 한국어-영어 코드스위칭에서 양자화 영향 분석 (Google Colab)

## 0) 목적과 산출물

### 목적
decoder-only LLM에서 **양자화(quantization)**가 **한국어-영어 코드스위칭(code-switching, CS)** 능력에 미치는 영향을, **CS 레벨별(word, phrase, sentence)**과 **전환 지점(switch point)** 중심으로 정량화한다.

### 최종 산출물
1) **단일 Colab 노트북(ipynb)**: 데이터 준비 → 모델 로드 → 추론 → 자동평가 → 결과 집계 및 샘플 분석까지 재현 가능  
2) **데이터셋(JSONL)**: CS 레벨, 전환 스펙, 프롬프트 포함  
3) **결과물**  
- sample-level 결과 JSONL  
- aggregate 결과 CSV (모델 × 양자화 × CS 레벨)  
- worst-case 예시 및 오류 유형 요약(텍스트)

---

## 1) 핵심 가설과 연구 질문

### 가설
- 단일 언어 생성 대비, **코드스위칭 생성은 양자화에 더 민감**하다.
- 특히 **전환 지점에서 언어 선택 실패**가 증가한다.
- CS 레벨 중 **phrase-level**이 가장 취약할 가능성이 높다(연속 구간 유지가 필요하기 때문).

### 연구 질문
- RQ1: 양자화는 CS 성능을 단일 언어 대비 더 크게 떨어뜨리는가  
- RQ2: CS 레벨(word, phrase, sentence)별로 민감도가 다른가  
- RQ3: 양자화로 인해 under-switch, over-switch, segment contamination이 증가하는가  

---

## 2) CS 레벨 정의와 분류 규칙

### 2.1 Word-level CS
정의: 문장 내부에서 **단일 단어**만 다른 언어로 등장한다. 연속된 외국어 단어 구간이 없다.  
예: "오늘 meeting 있어"  
예: "이거 deploy 했어?"

판정 규칙(요지): Lother 언어 토큰이 **고립된 1개 단위**로만 등장.

### 2.2 Phrase-level CS
정의: 문장 내부에서 **2개 이상 연속된 단어**가 다른 언어로 등장한다.  
예: "오늘 client meeting 준비해야 돼"  
예: "이거 is not working 제대로 확인해봐"

판정 규칙(요지): Lother 언어 토큰이 **연속 2개 이상** 존재.

### 2.3 Sentence-level CS
정의: **문장 경계**에서 언어가 전환된다. 각 문장은 단일 언어로 구성되는 것을 목표로 한다.  
예: "오늘 회의 있어. Let's prepare the slides."  
예: "이거 먼저 끝내자. Then we can deploy."

판정 규칙(요지): 문장 단위 분절 후, 어떤 문장이 Lother로만 구성되면 sentence-level.

### 2.4 우선순위 기반 단일 레이블 부여
한 샘플이 여러 조건을 만족하는 경우 다음 우선순위로 **단 하나의 cs_level**만 부여한다.  
**sentence > phrase > word**

---

## 3) 실험 범위

### 3.1 모델 조건
- decoder-only LLM
- 한국어와 영어 모두 생성 가능
- 최소 1개 모델로 시작, 가능하면 2개 모델로 확장  
  - 7B급 1개는 필수 권장  
  - (선택) 13B급 1개 추가

### 3.2 양자화 조건
최소 조건:
- FP16 baseline
- 8-bit (bitsandbytes)
- 4-bit (bitsandbytes NF4)

선택 확장:
- GPTQ 또는 AWQ (가능하면 4-bit의 다른 계열 비교)

### 3.3 디코딩 조건
양자화 효과를 비교하려면 디코딩을 고정한다.
- temperature, top_p, repetition_penalty, max_new_tokens 고정
- seed 고정
- batch size 고정(가능 범위)

---

## 4) 태스크 설계

본 프로젝트는 “코드스위칭을 잘한다”를 아래 2개의 태스크로 운영 정의한다.

### 4.1 Task A: 제어된 코드스위칭 생성(Controlled CS Generation)
목표: 지정된 스펙대로만 언어를 전환하며 답변 생성  
입력: 상황/질문 + switch_spec  
출력: switch_spec을 충족하는 답변

특징:
- 전환 위치가 명시되어 평가가 쉬움
- SPA, purity, over/under를 직접 측정 가능

### 4.2 Task B: 코드스위칭 패턴 유지(Style/Pattern Preservation)
목표: 입력 문장의 CS 패턴을 유지하여 요약 또는 변환  
입력: CS 혼합 텍스트 + 패턴 유지 지시  
출력: 같은 패턴을 유지한 요약/변환

특징:
- “실사용”에 더 가깝고, instruction following 실패를 더 잘 드러냄

권장: MVP에서는 Task A만으로 시작하고, 안정화 후 Task B 추가.

---

## 5) 데이터셋 설계

### 5.1 데이터 포맷(JSONL)
각 줄이 1개 샘플이며, 아래 필드를 포함한다.

필수 필드:
- id: 문자열
- cs_level: word | phrase | sentence
- topic: daily | tech | medical | education | ...
- task: A | B
- prompt: 모델에 넣을 전체 프롬프트 문자열
- switch_spec: 전환 규칙의 기계 판독용 스펙
- gold_pattern: 기대 언어 패턴(세그먼트 단위 또는 슬롯 단위)
- meta: 생성 시 사용한 옵션(난이도, 길이 등)

선택 필드:
- allow_loanwords: true/false
- loanword_list: ["버스", "meeting", ...] 같은 허용 리스트
- notes: 사람이 읽는 주석

권장 JSON 예시:
```json
{
  "id": "A_word_0001",
  "task": "A",
  "cs_level": "word",
  "topic": "tech",
  "prompt": "...",
  "switch_spec": {
    "type": "slot",
    "ko_prefix": "한국어로 문장을 시작하고, ",
    "en_slot": "여기에는 영어 단어 하나만 넣고, ",
    "ko_suffix": "나머지는 한국어로 마무리해라.",
    "constraints": {
      "en_word_count": 1,
      "no_extra_english": true
    }
  },
  "gold_pattern": {
    "segments": [
      {"lang": "ko"},
      {"lang": "en", "max_words": 1},
      {"lang": "ko"}
    ]
  },
  "meta": {"difficulty": "easy", "target_len": 60}
}
```

### 5.2 Switch specification 표준(권장)
두 방식 중 하나를 고른다. MVP는 슬롯 기반이 구현이 단순하다.

#### 방식 1) 슬롯 기반(slot)
- ko_prefix, en_slot, ko_suffix 같이 “영역”을 정의
- 평가도 영역 기준으로 purity를 계산 가능

#### 방식 2) 세그먼트 기반(segment)
- segments 배열로 lang과 text를 함께 정의
- 더 엄격하지만 생성 다양성이 줄 수 있음

MVP 권장: 슬롯 기반

### 5.3 데이터 규모와 분할
MVP 권장:
- 총 300 샘플
  - word 100, phrase 100, sentence 100
- topic은 최소 4개로 분산
- eval만 할 것이므로 train/dev/test는 필수는 아니지만, 재현성을 위해 고정 분할 권장
  - dev 50, test 250 같이 운영 가능

### 5.4 토픽과 난이도 제어
- topic: daily, tech, medical, education (최소)
- 난이도(difficulty):
  - easy: 짧은 문장, 단순 전환
  - medium: 조금 긴 문장, 숫자나 고유명사 포함
  - hard: 부정문, 조건문, 열거, 괄호, 인용 등 포함

### 5.5 “금지 규칙”과 데이터 품질 기준
- 템플릿 반복 금지(표면 형태가 동일한 문장 다수 금지)
- task A에서는 “전환 스펙 위반”을 유발하는 프롬프트 구성 금지
- 욕설, 혐오, 성적 내용 등 민감 콘텐츠 금지
- 가능한 한 자연스러운 CS를 지향하되, 평가 가능성을 우선

---

## 6) 프롬프트 템플릿(권장)

아래는 Task A를 위한 템플릿의 뼈대다. 실제 구현에서는 switch_spec을 자연어 지시로 변환하여 삽입한다.

### 6.1 공통 시스템 지시(모델이 instruction-following을 하게)
- “규칙 위반 시 0점”을 명확히
- “출력은 단 한 개의 답변만”을 명확히
- “불필요한 메타 코멘트 금지”를 명확히

### 6.2 Word-level 템플릿 예시
- 영어 단어는 정확히 1개만 포함
- 영어 구문(2단어 이상) 금지

### 6.3 Phrase-level 템플릿 예시
- 영어 연속 단어 수를 2에서 5 같은 범위로 고정
- 영어 구간 전후는 한국어만 허용

### 6.4 Sentence-level 템플릿 예시
- 첫 문장 한국어, 둘째 문장 영어 같이 명시
- 각 문장 내부 언어 혼합 금지

---

## 7) 자동 평가 설계

### 7.1 언어 판별(language detection)
MVP는 문자 비율 기반으로 충분하다.

- 한글 범위: \uAC00-\uD7A3
- 알파벳 범위: A-Za-z

유닛:
- 전체 텍스트
- 세그먼트별 텍스트
- 전환 지점 주변 윈도(선택)

예외 처리:
- 숫자, 공백, 구두점은 무시
- loanword는 allow_loanwords 설정에 따라 예외 처리 가능(초기에는 off로 두고 단순화 가능)

### 7.2 메트릭 정의

#### (1) SPA: Switch Point Accuracy
정의: 전환이 요구된 위치에서 실제로 언어가 전환되었는지의 정확도

실용 구현:
- 슬롯 기반이면, 슬롯 경계 전후의 dominant language가 기대 언어와 일치하는지 측정
- sentence-level이면, 문장 분절 후 각 문장의 dominant language가 기대와 일치하는지 측정

#### (2) Segment Purity (SP)
정의: 세그먼트 내부에서 요구 언어가 얼마나 순수하게 유지되는지
- 예: 한국어 세그먼트 purity = 한글 카운트 / (한글 + 알파벳)

#### (3) Over-switch rate
정의: 전환이 허용되지 않은 영역에서 반대 언어 비율이 임계값 이상으로 나타난 비율

#### (4) Under-switch rate
정의: 전환이 요구된 영역에서 기대 언어 비율이 임계값 이하인 비율

권장 임계값(초기):
- dominant language 판정 임계: 0.6
- purity 합격 기준: 0.8
이 값들은 노트북에서 상수로 두고 실험 중 조정 가능하게 한다.

### 7.3 결과 저장
sample-level JSONL에 아래를 포함
- output_text
- lang_stats: 세그먼트별 한글, 알파벳, 비율
- metrics: SPA, SP, over, under
- violation_flags: 스펙 위반 여부(예: 영어 단어 1개 제한 위반)

aggregate CSV는 groupby로 생성
- by model, quant, cs_level
- mean SPA, mean SP, over_rate, under_rate
- n_samples

---

## 8) 오류 유형(taxonomy) 정의

자동 평가로 포착 가능한 오류를 우선 정의한다.

1) Switching Failure  
- switch 구간에서 기대 언어 생성 실패

2) Segment Contamination  
- 세그먼트 내부에 반대 언어가 과도하게 섞임

3) Over-switch  
- 전환 금지 구간에서 전환 발생

4) Under-switch  
- 전환 요구 구간에서 전환 미발생

5) Degeneration  
- 반복, 비정상 길이 증가, 무의미 토큰 반복  
- 간단 지표: 반복률(유니크 2그램 비율 등)로 탐지 가능

---

## 9) Colab 노트북 구조(셀 단위 설계)

### Cell 1: 환경 설정
- pip install: torch, transformers, accelerate, bitsandbytes, pandas
- (선택) datasets, sentencepiece
- 버전 출력 및 GPU 정보 출력

### Cell 2: 공통 설정
- seed 고정
- decoding 파라미터 고정
- 경로: /content/results 같은 저장 루트 설정

### Cell 3: 데이터 로드 또는 생성
- JSONL 생성 함수 또는 로드
- cs_level별 카운트 출력
- 일부 샘플 print

### Cell 4: 프롬프트 빌더
- switch_spec을 자연어 지시로 변환
- task A용 prompt 완성

### Cell 5: 모델 로더
- load_model_fp16()
- load_model_8bit()
- load_model_4bit()
- 동일한 tokenizer 설정
- device_map과 torch_dtype 처리

### Cell 6: 추론 실행
- 모델, quant 조건별 루프
- batch infer
- 출력과 함께 sample-level 결과 누적 저장

### Cell 7: 평가
- language detection
- SPA, SP, over, under 계산
- violation flag 기록

### Cell 8: 집계 리포트
- pandas groupby 집계
- 표 출력
- worst-case 샘플 상위 K개 출력(예: SP 낮은 순)

### Cell 9: 아카이브
- 결과 CSV, JSONL 저장
- 노트북 마지막에 파일 목록 출력

---

## 10) 실험 매트릭스(권장)

MVP:
- model 1개
- quant: FP16, 8bit, 4bit
- cs_level: word, phrase, sentence
- 총 3 × 300 = 900 inference

확장:
- model 2개로 늘리면 1,800 inference

---

## 11) 재현성과 운영 규칙

- 랜덤 시드 고정
- 샘플 id 고정
- 디코딩 파라미터 고정
- 동일 프롬프트를 모든 양자화 조건에 사용
- 결과 파일명에 model, quant, 날짜 포함

---

## 12) 즉시 실행 체크리스트

1) MVP 모델 1개 선택  
2) 데이터셋 300개 생성(또는 우선 60개로 smoke test)  
3) FP16, 8bit, 4bit 로딩 확인  
4) 추론 루프가 중단 없이 돌고 결과가 저장되는지 확인  
5) SPA, SP가 정상 분포를 보이는지 확인  
6) phrase-level에서 성능이 더 떨어지는지 1차 확인

---

## 13) 구현 시 권장 기본값(초기값)

- max_new_tokens: 128
- temperature: 0.2
- top_p: 0.9
- repetition_penalty: 1.05
- batch_size: GPU VRAM에 맞춰 1에서 8 사이에서 조정
- dominant language threshold: 0.6
- purity pass threshold: 0.8

---

끝

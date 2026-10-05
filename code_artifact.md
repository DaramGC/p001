# 글로벌 주식 이슈 대시보드 (Global Market Pulse) 구현 명세서

본 문서는 **"글로벌 금융 시장의 주요 이슈를 지속적으로 트래킹하고, 뉴스 ↔ 종목 간의 양방향 탐색을 지원하는 정적 웹 서비스"**의 개발 명세서입니다. GitHub Pages 무료 호스팅과 GitHub Actions 크론잡, 경량 LLM(Gemini 2.5 Flash / GPT-4o-mini)을 결합하여 비용 0원에 안정적인 데이터 파이프라인을 구축하는 것을 목표로 합니다.

---

## 1. 아키텍처 개요

```
[외부 데이터 소스]
  ├─ 글로벌/미국 금융 뉴스 RSS (Google News, Reuters, CNBC 등)
  ├─ 한국 금융 뉴스 RSS (연합인포맥스, 한경 등)
  └─ 시장 변동성/급등락 시세 데이터 (Yahoo Finance / yfinance)
            │
            ▼
[배치 처리: GitHub Actions Runner] (매 2~4시간 주기 자동 실행)
  ├─ 1. scripts/fetch_sources.py : 뉴스 헤드라인 및 시세 수집
  ├─ 2. scripts/analyze_llm.py   : LLM을 통한 정형화 (핵심 이슈, 티커 매핑, 이유 1문장 요약)
  └─ 3. scripts/build_dataset.py : public/data.json 으로 집합 저장
            │
            ▼ (자동 git commit & push)
[배포: GitHub Pages]
  └─ index.html + Tailwind CSS + TradingView Free Widget
      - 방문자는 public/data.json 만 읽어 즉각 렌더링
      - API 키 유출 위험 제로, LLM 호출 비용 극소화
```

---

## 2. 프로젝트 디렉터리 구조

```
market-pulse/
├── .github/
│   └── workflows/
│       └── update_data.yml       # 2~4시간 주기 크론잡 워크플로우
├── scripts/
│   ├── fetch_sources.py          # RSS 및 시세 수집기
│   ├── analyze_llm.py            # LLM 엔티티 추출 및 이슈 요약기
│   └── requirements.txt          # Python 의존성 목록
├── public/
│   ├── data.json                 # 배포되는 최종 데이터셋 (정적 캐시)
│   └── index.html                # 프론트엔드 대시보드 (Single-Page)
└── README.md
```

---

## 3. 핵심 스키마: `public/data.json`

프론트엔드가 렌더링할 표준 데이터 구조입니다. LLM 출력 포맷과 1:1로 대응됩니다.

```json
{
  "updated_at": "2026-10-05T18:00:00Z",
  "market_summary": {
    "us_status": "혼조세",
    "kr_status": "외인 매수세 유입"
  },
  "major_issues": [
    {
      "id": "issue-001",
      "market": "GLOBAL", // GLOBAL, US, KR
      "title": "AI 반도체 수요 확장 및 차세대 HBM 공급 경쟁",
      "summary": "빅테크 실적 발표를 앞두고 차세대 AI 가속기 공급 병목 해소 및 공급망 수혜 기업에 투자 심리 집중",
      "sentiment": "POSITIVE", // POSITIVE, NEGATIVE, NEUTRAL
      "related_tickers": [
        {
          "symbol": "NVDA",
          "name": "NVIDIA",
          "market": "NASDAQ",
          "reason": "차세대 아키텍처 기반 칩 수요 지속 및 클라우드 CSP 고객사 주문 확대"
        },
        {
          "symbol": "000660.KS",
          "name": "SK하이닉스",
          "market": "KRX",
          "reason": "주요 빅테크향 HBM 공급 우위 및 메모리 단가 상승 모멘텀 유지"
        }
      ],
      "sources": [
        { "title": "CNBC Tech Headline", "url": "https://..." }
      ]
    }
  ],
  "trending_tickers": [
    {
      "symbol": "TSLA",
      "name": "Tesla",
      "market": "NASDAQ",
      "change_rate": "+4.2%",
      "why_trending": "자율주행 소프트웨어 v13 배포 임박 및 유럽 판매 회복 기대감"
    }
  ]
}
```

---

## 4. 파이프라인 구현 단계

### 단계 1: 데이터 수집 및 LLM 파싱 (`scripts/analyze_llm.py`)

Python 3.10+ 환경에서 실행되며, 뉴스 원문을 수집하고 경량 LLM(구조화된 출력 지원 모델)으로 파싱합니다.

```python
import os
import json
import feedparser
from google import genai
from google.genai import types

# 1. 뉴스 RSS 수집 (샘플: Google News Finance & 국내 주요 피드)
FEEDS = [
    "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVd4NVNBIQFSAldT?hl=en-US&gl=US&ceid=US:en", # US Markets
    "https://news.google.com/rss/headlines/section/topic/BUSINESS.ko_kr?ned=kr&hl=ko&gl=KR" # 한국 경제
]

def collect_headlines(limit=25):
    items = []
    for url in FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries[:limit]:
            items.append({
                "title": entry.title,
                "link": entry.link,
                "summary": getattr(entry, "summary", "")
            })
    return items

# 2. LLM 분석 파이프라인
def analyze_market_news(articles):
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    
    prompt = f"""
    당신은 글로벌 헤지펀드의 수석 시장 분석가입니다.
    제공된 뉴스 목록을 분석하여 다음 기준에 맞는 JSON을 생성하세요:
    1. 현재 글로벌 및 한국 증시를 움직이는 가장 중요한 4~6개의 핵심 거시/섹터 이슈
    2. 각 이슈별 직접적인 연관 종목(미국/한국 티커 포함)과 '왜 이 종목이 주목받는지'에 대한 명확한 한 줄 이유
    3. 거래량이나 이슈로 인해 주목받는 주요 급등락/트렌딩 종목 3~5개

    입력 기사:
    {json.dumps(articles, ensure_ascii=False)}
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )
    return response.text

if __name__ == "__main__":
    articles = collect_headlines()
    structured_json_str = analyze_market_news(articles)
    
    with open("public/data.json", "w", encoding="utf-8") as f:
        f.write(structured_json_str)
```

---

### 단계 2: GitHub Actions 자동화 워크플로우 (`.github/workflows/update_data.yml`)

2시간마다 스크립트를 가동하고 업데이트된 `data.json`을 저장소에 자동 커밋합니다.

```yaml
name: Update Market Pulse Data

on:
  schedule:
    - cron: '0 */3 * * *'  # 3시간마다 실행
  workflow_dispatch:        # 수동 트리거 지원

jobs:
  build-and-commit:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install feedparser google-genai yfinance

      - name: Run extraction & LLM analysis
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: |
          python scripts/analyze_llm.py

      - name: Commit and push changes
        run: |
          git config --global user.name "MarketPulse Bot"
          git config --global user.email "bot@marketpulse.local"
          git add public/data.json
          git diff --quiet && git diff --staged --quiet || (git commit -m "chore: auto-update market data [skip ci]" && git push)
```

---

### 단계 3: 프론트엔드 UI/UX 설계 요건 (`public/index.html`)

1. **상단 네비게이션 & 시장 요약:**
   * 미국/한국 시장 상태 및 업데이트 시각 (`data.updated_at`) 표시.
   * `[전체]`, `[글로벌/미국]`, `[한국]` 필터 탭.
2. **양방향 탐색 뷰:**
   * **View A: 이슈별 탐색 (News ➔ Stock):**
     * 주요 이슈 카드 클릭 시 연결된 수혜/피해 티커 칩(`Chip`) 나열.
   * **View B: 종목별 탐색 (Stock ➔ Reason):**
     * 트렌딩 종목 리스트에서 종목을 누르면 **"왜 주목받는가?"** 1줄 요약과 함께 하단/측면 모달에 **TradingView 무료 위젯** 임베드.
3. **무료 시세 연동:**
   * TradingView의 `TradingView.widget` 스크립트를 사용하여 심볼 클릭 시 `NASDAQ:{SYMBOL}` 또는 `KRX:{SYMBOL}` 차트를 즉시 띄웁니다 (비용 0원, 최고 퀄리티).

---

## 5. 단계별 양질의 데이터 소스 확장 로드맵

초기 프로토타입 검증 후 데이터 품질을 높이기 위한 추천 소스 목록입니다.

| 단계 | 데이터 성격 | 권장 데이터 소스 | 특징 및 활용 방안 |
| :--- | :--- | :--- | :--- |
| **Phase 1 (MVP)** | 거시 뉴스 & 미국/한국 헤드라인 | Google News RSS, 연합뉴스 RSS, CNBC RSS | 무료, API 키 불필요, 피드 파서로 즉시 수집 가능 |
| **Phase 2 (정밀도 향상)** | 종목별 공시 및 시장 뉴스 API | **Finnhub (무료 티어)**, **Alpha Vantage** | 종목별 정밀 뉴스 매칭 및 당일 주가 변동률 결합 |
| **Phase 3 (한국 특화)** | 한국 시장 공시 및 수급 | **DART 오픈 API**, **KRX 정보데이터시스템** | 외국인/기관 순매수 상위 종목 및 핵심 지분 공시 요약 |
| **Phase 4 (글로벌 확장)** | 다국적 센티먼트 및 다국어 뉴스 | **Marketaux** | 다국어(영어, 일어, 유럽어) 뉴스에서 티커 자동 추출 |
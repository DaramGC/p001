# Global Market Pulse 🌐📈
> **글로벌 금융 시장의 주요 이슈를 지속적으로 트래킹하고, 뉴스 ↔ 종목 간의 양방향 탐색을 지원하는 정적 웹 서비스**

본 프로젝트는 GitHub Pages 무료 호스팅, GitHub Actions 크론잡, Gemini 2.5 Flash를 결합하여 **비용 0원에 유지되는 안정적인 금융 데이터 파이프라인**을 제공합니다.

🔗 **배포 저장소:** [https://github.com/DaramGC/p001](https://github.com/DaramGC/p001)  
🌐 **GitHub Pages 대시보드 주소:** `https://daramgc.github.io/p001/`

---

## 1. 주요 기능 & 특징

1. **양방향 탐색 인텔리전스 (Two-way Exploration)**
   - **View 1 (거시 & 밸류체인 이슈):** 글로벌/한국 시장을 움직이는 핵심 거시·섹터 이슈와 1차 직접 수혜 / 2차 낙수효과 밸류체인 매핑
   - **View 2 (중소형 강소기업 & 코스닥):** 단독 수주, 공급계약, 바이오 임상/기술이전, 신기술 특허 등 개별 모멘텀을 보유한 코스닥 및 스몰캡 발굴
   - **View 3 (경제 캘린더 & 지표):** 미국 CPI, PPI, 연준 FOMC, 한은 금통위 등 증시 파급력이 큰 주요 이벤트 일정 및 관전 포인트
2. **TradingView 실시간 인터랙티브 차트 무료 연동**
   - 미국 종목 및 한국 종목(`KRX:000660`, `KRX:005930`, `KRX:240810` 등) 트레이딩뷰 실시간 캔들 차트 및 네이버 증권 듀얼 뷰 지원.
3. **완전 무료 & 고가용성 서버리스 아키텍처**
   - GitHub Actions 크론잡(**6시간 주기 자동 실행**)이 뉴스 RSS 피드를 수집하고 Gemini LLM을 통해 정형화된 `public/data.json`을 자동 빌드 & 커밋합니다.
   - 대시보드의 **[수동 최신화]** 버튼을 통해 GitHub Actions(`workflow_dispatch`)를 원할 때 언제든 즉시 수동 가동할 수 있습니다.

---

## 2. 프로젝트 디렉터리 구조

```
p001/
├── .github/
│   └── workflows/
│       └── update_data.yml       # 6시간 주기 자동 실행 및 수동 실행 워크플로우
├── scripts/
│   ├── fetch_sources.py          # Google News 및 RSS 피드 수집 모듈
│   ├── analyze_llm.py            # Gemini 2.5 Flash 기반 정형 분석기
│   └── requirements.txt          # Python 필수 패키지 목록
├── public/
│   ├── data.json                 # 최종 정적 데이터셋 (LLM 자동 갱신)
│   └── index.html                # 프론트엔드 대시보드 (Tailwind + TradingView)
├── index.html                    # 루트 리다이렉터
├── code_artifact.md              # 초기 구현 명세서
└── README.md
```

---

## 3. GitHub 설정 가이드

### 1) Gemini API 키 등록 (필수)
자동화 워크플로우가 뉴스를 분석할 수 있도록 GitHub 저장소 Secret을 등록해야 합니다.

1. [Google AI Studio](https://aistudio.google.com/)에서 무료 API 키를 발급받습니다.
2. GitHub 저장소(`DaramGC/p001`)로 이동합니다.
3. **Settings** 탭 ➔ 좌측 사이드바 **Secrets and variables** ➔ **Actions** 클릭.
4. **New repository secret** 버튼 클릭:
   - **Name**: `GEMINI_API_KEY`
   - **Secret**: 발급받은 Gemini API 키 입력
5. **Add secret** 클릭하여 저장.

### 2) GitHub Pages 활성화
1. GitHub 저장소(`DaramGC/p001`)의 **Settings** 탭으로 이동합니다.
2. 좌측 메뉴에서 **Pages**를 클릭합니다.
3. **Build and deployment** 섹션의 **Source**를 `Deploy from a branch`로 선택합니다.
4. **Branch**를 `main` / `/(root)`로 지정하고 **Save**를 누릅니다.
5. 수 분 내로 `https://daramgc.github.io/p001/` 주소로 대시보드가 라이브 호스팅됩니다.

### 3) GitHub Actions 권한 설정
Actions 봇이 `public/data.json`을 자동 커밋할 수 있도록 쓰기 권한을 확인합니다.
1. 저장소 **Settings** ➔ **Actions** ➔ **General** 로 이동.
2. **Workflow permissions** 섹션에서 **Read and write permissions**를 선택하고 **Save**를 클릭합니다.

---

## 4. 로컬 실행 및 테스트 방법

### 1) 의존성 설치
```bash
pip install -r scripts/requirements.txt
```

### 2) 뉴스 수집 테스트
```bash
python scripts/fetch_sources.py
```

### 3) LLM 분석 파이프라인 수동 실행
```bash
# Windows PowerShell
$env:GEMINI_API_KEY="your-api-key"
python scripts/analyze_llm.py

# macOS/Linux
export GEMINI_API_KEY="your-api-key"
python scripts/analyze_llm.py
```
> `GEMINI_API_KEY`가 설정되지 않은 경우에도 안전하게 기본 샘플 데이터셋으로 `public/data.json`을 생성합니다.

### 4) 로컬 웹 대시보드 확인
```bash
# Python 내장 웹 서버 실행
python -m http.server 8000
```
브라우저에서 `http://localhost:8000/public/` 또는 `http://localhost:8000`에 접속하여 대시보드를 테스트할 수 있습니다.

---

## 5. 데이터 소스 확장 로드맵

- **Phase 1 (MVP - 현재):** Google News RSS, CNBC Market RSS, 연합뉴스 RSS
- **Phase 2 (정밀도 향상):** Finnhub 무료 티어, Alpha Vantage (종목별 실시간 변동률 결합)
- **Phase 3 (한국 특화):** DART 오픈 API, KRX 정보데이터시스템 (외인/기관 순매수 및 지분 공시)
- **Phase 4 (글로벌 확장):** Marketaux 등 다국어 뉴스 센티먼트 엔진

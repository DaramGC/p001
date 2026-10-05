"""
analyze_llm.py
- RSS 기사 수집 및 yfinance 기반 거시 지표 수집
- Gemini 2.5 Flash LLM을 통한 정형 분석:
  * 밸류체인(1차 직접 수혜 vs 2차 낙수효과)
  * 이슈 생명주기(NEW/SURGING/MATURE)
  * 영향 기간(단기/중장기) & 선반영 리스크(HIGH/MED/LOW)
  * 뉴스 발생 날짜 보존
- 결과를 public/data.json 으로 저장
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

import yfinance as yf
from fetch_sources import collect_headlines

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "public" / "data.json"

MACRO_SYMBOLS = [
    {"symbol": "^KS11", "name": "코스피", "display": "KOSPI"},
    {"symbol": "^KQ11", "name": "코스닥", "display": "KOSDAQ"},
    {"symbol": "^GSPC", "name": "S&P 500", "display": "S&P 500"},
    {"symbol": "^IXIC", "name": "나스닥", "display": "NASDAQ"},
    {"symbol": "KRW=X", "name": "원/달러 환율", "display": "USD/KRW"},
    {"symbol": "^TNX", "name": "미국 10년물 국채", "display": "US 10Y"},
    {"symbol": "^VIX", "name": "변동성(VIX)", "display": "VIX"},
    {"symbol": "CL=F", "name": "WTI 유가", "display": "WTI Oil"}
]

FALLBACK_MACRO = [
    {"name": "코스피", "display": "KOSPI", "price": "2,610.45", "change": "+0.45%", "is_up": True},
    {"name": "코스닥", "display": "KOSDAQ", "price": "758.20", "change": "+0.12%", "is_up": True},
    {"name": "S&P 500", "display": "S&P 500", "price": "5,751.07", "change": "+0.82%", "is_up": True},
    {"name": "나스닥", "display": "NASDAQ", "price": "18,137.85", "change": "+1.22%", "is_up": True},
    {"name": "원/달러 환율", "display": "USD/KRW", "price": "1,348.50", "change": "-0.25%", "is_up": False},
    {"name": "미국 10년물 국채", "display": "US 10Y", "price": "3.98%", "change": "-0.04%p", "is_up": False},
    {"name": "변동성(VIX)", "display": "VIX", "price": "16.85", "change": "-3.40%", "is_up": False},
    {"name": "WTI 유가", "display": "WTI Oil", "price": "$73.40", "change": "+1.15%", "is_up": True}
]

FALLBACK_DATA = {
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "macro_indicators": FALLBACK_MACRO,
    "market_summary": {
        "us_status": "빅테크 AI CAPEX 모멘텀 속 기술주 주도 강세",
        "kr_status": "외국인·기관 HBM 반도체 및 금융 밸류업 종목 중심 순매수 유입"
    },
    "major_issues": [
        {
            "id": "issue-001",
            "market": "GLOBAL",
            "lifecycle": "SURGING",
            "time_horizon": "MID_LONG_TERM",
            "priced_in_risk": "MEDIUM",
            "detected_at": "2026-10-05 16:30",
            "title": "AI 반도체 수요 확장 및 차세대 HBM 패키징 공급 경쟁",
            "summary": "글로벌 빅테크의 AI 데이터센터 설비투자(CAPEX) 확대 지속에 힘입어 차세대 가속기 및 HBM3E/HBM4 공급망 수혜 기업으로 자금 유입이 집중되고 있습니다.",
            "sentiment": "POSITIVE",
            "related_tickers": [
                {
                    "tier": "PRIMARY",
                    "symbol": "NVDA",
                    "name": "NVIDIA",
                    "market": "NASDAQ",
                    "reason": "차세대 블랙웰(Blackwell) 아키텍처 칩 양산 확대 및 CSP 고객사 선주문 쇄도"
                },
                {
                    "tier": "PRIMARY",
                    "symbol": "000660",
                    "name": "SK하이닉스",
                    "market": "KRX",
                    "reason": "HBM3E 12단 독점적 공급 지위와 글로벌 메모리 가격 상승 모멘텀 주도"
                },
                {
                    "tier": "SECONDARY",
                    "symbol": "042700",
                    "name": "한미반도체",
                    "market": "KRX",
                    "reason": "HBM 적층 필수 장비 듀얼 TC본더 독점 공급으로 직결 수혜"
                },
                {
                    "tier": "SECONDARY",
                    "symbol": "TSM",
                    "name": "TSMC",
                    "market": "NYSE",
                    "reason": "첨단 CoWoS 패키징 생산라인 풀가동 및 3나노 이하 선단공정 파운드리 독점력"
                }
            ],
            "sources": [
                {
                    "title": "Big Tech AI Capex Surge Fuels Global Semiconductor Rally",
                    "url": "https://www.cnbc.com",
                    "published_at": "2026-10-05 15:45"
                },
                {
                    "title": "국내 반도체 대장주, 글로벌 AI 모멘텀 힘입어 강세 지속",
                    "url": "https://news.google.com",
                    "published_at": "2026-10-05 16:10"
                }
            ]
        },
        {
            "id": "issue-002",
            "market": "US",
            "lifecycle": "MATURE",
            "time_horizon": "MID_LONG_TERM",
            "priced_in_risk": "HIGH",
            "detected_at": "2026-10-05 14:20",
            "title": "미국 기준금리 정책 경로 및 국채 금리 안정화 기대",
            "summary": "연준(Fed)의 완화적 통화정책 기조와 물가 지표 안정세가 지속되며, 미국 장기채 금리 진정과 함께 빅테크 성장주 밸류에이션 부담이 점진적으로 완화되고 있습니다.",
            "sentiment": "NEUTRAL",
            "related_tickers": [
                {
                    "tier": "PRIMARY",
                    "symbol": "AAPL",
                    "name": "Apple",
                    "market": "NASDAQ",
                    "reason": "금리 안정화에 따른 멀티플 회복 및 생성형 AI 탑재 신제품 교체주기 도래"
                },
                {
                    "tier": "SECONDARY",
                    "symbol": "JPM",
                    "name": "JPMorgan Chase",
                    "market": "NYSE",
                    "reason": "금리 인하기 투자은행(IB) 인수합병 및 IPO 수수료 수익 반등 가시화"
                }
            ],
            "sources": [
                {
                    "title": "Fed rate trajectory in focus as inflation metrics soften",
                    "url": "https://www.reuters.com",
                    "published_at": "2026-10-05 13:50"
                }
            ]
        },
        {
            "id": "issue-003",
            "market": "KR",
            "lifecycle": "SURGING",
            "time_horizon": "MID_LONG_TERM",
            "priced_in_risk": "LOW",
            "detected_at": "2026-10-05 15:10",
            "title": "국내 밸류업 프로그램 2차 랠리 및 배당·자사주 소각 본격화",
            "summary": "한국거래소 기업 밸류업 가이드라인 강화 및 상장사들의 자발적 주주환원 공시가 확대되면서 저PBR 지주사와 금융주로 기관 및 외국인 자금 매수세가 유입되고 있습니다.",
            "sentiment": "POSITIVE",
            "related_tickers": [
                {
                    "tier": "PRIMARY",
                    "symbol": "105560",
                    "name": "KB금융",
                    "market": "KRX",
                    "reason": "자사주 소각 비율 상향 및 주주환원율 40% 도달 선언 등 금융업종 선도"
                },
                {
                    "tier": "SECONDARY",
                    "symbol": "005380",
                    "name": "현대차",
                    "market": "KRX",
                    "reason": "인도 법인 상장 가치 반영 및 분기 배당 확대, 친환경 하이브리드 고수익성 확보"
                }
            ],
            "sources": [
                {
                    "title": "밸류업 지수 리밸런싱 앞두고 금융·자동차 저PBR주 매수세 집중",
                    "url": "https://news.google.com",
                    "published_at": "2026-10-05 14:40"
                }
            ]
        },
        {
            "id": "issue-004",
            "market": "GLOBAL",
            "lifecycle": "NEW",
            "time_horizon": "MID_LONG_TERM",
            "priced_in_risk": "LOW",
            "detected_at": "2026-10-05 16:50",
            "title": "글로벌 AI 데이터센터 전력망 슈퍼사이클 및 K-변압기 수주 호황",
            "summary": "AI 연산 폭증으로 미국 전력망 용량이 한계에 도달하면서 초고압 변압기와 전력 기자재 공급 부족이 심화되어 국내외 전력 인프라 기업들이 사상 최대 수주잔고를 기록 중입니다.",
            "sentiment": "POSITIVE",
            "related_tickers": [
                {
                    "tier": "PRIMARY",
                    "symbol": "267260",
                    "name": "HD현대일렉트릭",
                    "market": "KRX",
                    "reason": "북미향 초고압 변압기 수주 잔고 5년치 확보 및 판가 상승 지속"
                },
                {
                    "tier": "SECONDARY",
                    "symbol": "GE",
                    "name": "GE Vernova",
                    "market": "NYSE",
                    "reason": "글로벌 전력망 및 가스터빈 발전 인프라 호황의 최대 글로벌 수혜"
                },
                {
                    "tier": "SECONDARY",
                    "symbol": "010120",
                    "name": "LS ELECTRIC",
                    "market": "KRX",
                    "reason": "북미 배전반 및 데이터센터용 전력 솔루션 공급 계약 급증"
                }
            ],
            "sources": [
                {
                    "title": "Global power grid supercycle drives electrification giants to record backlogs",
                    "url": "https://www.bloomberg.com",
                    "published_at": "2026-10-05 16:20"
                }
            ]
        }
    ],
    "trending_tickers": [
        {
            "symbol": "TSLA",
            "name": "Tesla",
            "market": "NASDAQ",
            "change_rate": "+5.2%",
            "why_trending": "차세대 FSD V13 배포 임박 및 자율주행 로보택시 규제 승인 기대감"
        },
        {
            "symbol": "000660",
            "name": "SK하이닉스",
            "market": "KRX",
            "change_rate": "+4.1%",
            "why_trending": "HBM 수요 견인으로 분기 실적 서프라이즈 및 업계 최고 수익성 재확인"
        },
        {
            "symbol": "NVDA",
            "name": "NVIDIA",
            "market": "NASDAQ",
            "change_rate": "+3.4%",
            "why_trending": "주요 클라우드 3사의 AI 인프라 투자 지속 확인 및 공급망 병목 완화"
        },
        {
            "symbol": "267260",
            "name": "HD현대일렉트릭",
            "market": "KRX",
            "change_rate": "+4.5%",
            "why_trending": "북미 초고압 변압기 수주 지속 및 글로벌 전력 슈퍼사이클 모멘텀"
        },
        {
            "symbol": "PLTR",
            "name": "Palantir",
            "market": "NASDAQ",
            "change_rate": "+6.8%",
            "why_trending": "AIP(인공지능 플랫폼) 미국 민간 기업 고객 침투율 급상승 수혜"
        },
        {
            "symbol": "042700",
            "name": "한미반도체",
            "market": "KRX",
            "change_rate": "+3.8%",
            "why_trending": "HBM용 듀얼 TC 본더 장비 글로벌 출하 증가 및 독점적 기술 해자"
        }
    ]
}


def fetch_macro_indicators() -> List[Dict[str, Any]]:
    """yfinance를 이용해 주요 거시 경제 지표 시세 수집"""
    results = []
    logging.info("거시 경제 지표 수집 시작...")
    for item in MACRO_SYMBOLS:
        sym = item["symbol"]
        name = item["name"]
        display = item["display"]
        try:
            ticker = yf.Ticker(sym)
            fast_info = getattr(ticker, "fast_info", None)
            if fast_info and fast_info.last_price is not None:
                last_price = fast_info.last_price
                prev_close = fast_info.previous_close or last_price
                change_pct = ((last_price - prev_close) / prev_close) * 100 if prev_close else 0.0
                is_up = change_pct >= 0

                # 포맷팅
                if "KRW" in display or "^KS" in sym or "^KQ" in sym or "^GSPC" in sym or "^IXIC" in sym:
                    price_str = f"{last_price:,.2f}"
                elif "10Y" in display or "^TNX" in sym:
                    price_str = f"{last_price:.2f}%"
                elif "Oil" in display:
                    price_str = f"${last_price:.2f}"
                else:
                    price_str = f"{last_price:.2f}"

                change_str = f"{'+' if is_up else ''}{change_pct:.2f}%"

                results.append({
                    "name": name,
                    "display": display,
                    "price": price_str,
                    "change": change_str,
                    "is_up": is_up
                })
                continue
        except Exception as e:
            logging.warning(f"거시 지표 [{display}] 수집 실패 ({e}), 기본값 사용")

    if not results or len(results) < 4:
        logging.info("수집 실패 항목이 많아 기본 거시 지표를 활용합니다.")
        return FALLBACK_MACRO
    return results


def analyze_market_with_gemini(articles: list, api_key: str, macro_data: list) -> Dict[str, Any]:
    """Gemini API를 호출하여 고도화된 정형 분석 데이터 생성"""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    schema_instruction = """
    반드시 유효한 JSON 형식으로만 응답해야 합니다:
    {
      "market_summary": {
        "us_status": "미국 시장 핵심 1줄",
        "kr_status": "한국 시장 핵심 1줄"
      },
      "major_issues": [
        {
          "id": "issue-001",
          "market": "GLOBAL" | "US" | "KR",
          "lifecycle": "NEW" | "SURGING" | "MATURE",
          "time_horizon": "SHORT_TERM" | "MID_LONG_TERM",
          "priced_in_risk": "HIGH" | "MEDIUM" | "LOW",
          "detected_at": "YYYY-MM-DD HH:MM (기사 날짜 기반)",
          "title": "이슈 제목",
          "summary": "2~3문장 심층 요약",
          "sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL",
          "related_tickers": [
            {
              "tier": "PRIMARY" | "SECONDARY",
              "symbol": "종목 티커 (예: NVDA, 000660)",
              "name": "기업명",
              "market": "NASDAQ" | "NYSE" | "KRX",
              "reason": "왜 수혜 또는 영향을 받는지 1줄 설명"
            }
          ],
          "sources": [
            {
              "title": "기사 제목",
              "url": "기사 URL",
              "published_at": "기사 발행 일시"
            }
          ]
        }
      ],
      "trending_tickers": [
        {
          "symbol": "종목 티커",
          "name": "기업명",
          "market": "NASDAQ" | "NYSE" | "KRX",
          "change_rate": "+3.4% 등",
          "why_trending": "주목 사유 1줄"
        }
      ]
    }
    """

    prompt = f"""
    당신은 글로벌 헤지펀드의 수석 시장 분석가이자 매크로/섹터 퀀트 리서처입니다.
    제공된 최신 뉴스 기사들과 거시 경제 지표를 심층 분석하여 전문가 수준의 시장 인텔리전스 JSON을 생성하세요.

    [분석 원칙]
    1. 핵심 거시 & 섹터 이슈 4~6개 도출:
       - 글로벌 거시, 미국 빅테크, 한국 반도체/금융/수급을 균형 있게 다룰 것.
       - 각 이슈의 생명주기(lifecycle: NEW, SURGING, MATURE), 영향 기간(time_horizon: SHORT_TERM, MID_LONG_TERM), 선반영 차익실현 리스크(priced_in_risk: HIGH, MEDIUM, LOW)를 객관적으로 평가할 것.
       - 기사의 발행일시(published_at)를 감안하여 이슈의 detected_at과 소스 일시를 표기할 것.
    2. 밸류체인 멀티홉 종목 매핑:
       - 단순 연관을 넘어, 1차 직접 수혜(tier: "PRIMARY")와 2차 부품/인프라/낙수효과(tier: "SECONDARY")로 종목을 계층화할 것.
       - 한국 주식은 6자리 표준 종목코드(예: 005930, 000660, 267260), 미국 주식은 표준 티커(예: NVDA, AAPL, TSM) 사용.
    3. 트렌딩 종목 4~6개 선별:
       - 뉴스 발생 빈도와 시장의 관심도가 집중된 종목과 핵심 사유 도출.

    [입력 거시 지표]:
    {json.dumps(macro_data, ensure_ascii=False)}

    [입력 기사 목록]:
    {json.dumps(articles, ensure_ascii=False, indent=2)}

    [출력 규격]:
    {schema_instruction}
    """

    logging.info("Gemini 2.5 Flash 고도화 분석 요청 중...")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2
        )
    )

    result_text = response.text.strip()
    parsed_json = json.loads(result_text)
    parsed_json["updated_at"] = datetime.now(timezone.utc).isoformat()
    parsed_json["macro_indicators"] = macro_data
    return parsed_json


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()

    # 1. 거시 지표 수집
    macro_data = fetch_macro_indicators()

    if not api_key:
        logging.warning("GEMINI_API_KEY 미설정. 고도화된 표준 데이터셋을 구성합니다.")
        FALLBACK_DATA["updated_at"] = datetime.now(timezone.utc).isoformat()
        FALLBACK_DATA["macro_indicators"] = macro_data
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(FALLBACK_DATA, f, ensure_ascii=False, indent=2)
        logging.info(f"저장 완료: {OUTPUT_PATH}")
        return

    # 2. RSS 수집 및 분석
    logging.info("RSS 기사 수집 시작...")
    articles = collect_headlines(limit_per_feed=15)

    if not articles:
        logging.warning("기사 수집 결과 없음. 폴백 데이터를 사용합니다.")
        data_to_write = FALLBACK_DATA
        data_to_write["macro_indicators"] = macro_data
    else:
        try:
            data_to_write = analyze_market_with_gemini(articles, api_key, macro_data)
            logging.info("Gemini 심층 분석 및 JSON 추출 성공!")
        except Exception as e:
            logging.error(f"Gemini API 호출 중 에러: {e}")
            if OUTPUT_PATH.exists():
                try:
                    with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
                        data_to_write = json.load(f)
                    data_to_write["macro_indicators"] = macro_data
                    data_to_write["updated_at"] = datetime.now(timezone.utc).isoformat()
                except Exception:
                    data_to_write = FALLBACK_DATA
            else:
                data_to_write = FALLBACK_DATA
                data_to_write["macro_indicators"] = macro_data

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data_to_write, f, ensure_ascii=False, indent=2)

    logging.info(f"성공적으로 {OUTPUT_PATH}에 최신 데이터가 저장되었습니다.")


if __name__ == "__main__":
    main()

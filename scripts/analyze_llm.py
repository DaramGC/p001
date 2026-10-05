"""
analyze_llm.py
- 대형 매크로 뉴스 + 중소형 특징주/수주/임상 RSS 피드 수집
- yfinance 거시 지표 수집
- Gemini 2.5 Flash를 통한 고도화 인텔리전스 추출:
  1. 거시 & 섹터 밸류체인 이슈 (대형주 1·2차 밸류체인)
  2. 중소형 강소기업 & 코스닥/스몰캡 개별 모멘텀주 (수주/공급계약/임상/특허/테마)
  3. 주요 경제 지표 발표 캘린더 (미국 CPI, FOMC, 고용, 한은 금통위 등)
  4. 트렌딩 종목 리스트
- public/data.json 으로 저장
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

FALLBACK_CALENDAR = [
    {
        "id": "cal-01",
        "date": "2026-10-10",
        "d_day": "D-5",
        "country": "US",
        "event_name": "미국 9월 소비자물가지수 (CPI) 발표",
        "importance": "HIGH",
        "forecast_vs_previous": "예상치: 전년비 +2.3% (전월치: +2.5%)",
        "market_impact": "근원 CPI의 둔화 지속 여부가 연준의 11월 FOMC 추가 25bp/50bp 금리 인하 강도를 결정짓는 분수령이 됩니다."
    },
    {
        "id": "cal-02",
        "date": "2026-10-11",
        "d_day": "D-6",
        "country": "KR",
        "event_name": "한국은행 금융통화위원회 기준금리 결정",
        "importance": "HIGH",
        "forecast_vs_previous": "현행: 3.50% ➔ 기준금리 25bp 인하 가능성 고조",
        "market_impact": "가계부채 추이와 수도권 집값 안정을 저울질하며 국내 통화정책 완화 피벗(Pivot) 본격 개시 여부 주목."
    },
    {
        "id": "cal-03",
        "date": "2026-10-16",
        "d_day": "D-11",
        "country": "US",
        "event_name": "미국 9월 소매판매 (Retail Sales)",
        "importance": "MEDIUM",
        "forecast_vs_previous": "예상치: 전월비 +0.3% (전월치: +0.1%)",
        "market_impact": "미국 GDP의 70%를 차지하는 소비 건전성을 검증하여 경제 '노랜딩(No Landing)' 또는 연착륙 시나리오를 지지할지 판단."
    },
    {
        "id": "cal-04",
        "date": "2026-11-04",
        "d_day": "D-30",
        "country": "US",
        "event_name": "미국 연준 FOMC 정례회의 기준금리 결정",
        "importance": "HIGH",
        "forecast_vs_previous": "시장 컨센서스: 25bp 추가 인하 (연 4.50~4.75%)",
        "market_impact": "점도표와 제롬 파월 의장의 기자회견을 통해 2026년 최종 종착 금리(Terminal Rate) 수준 제시."
    }
]

FALLBACK_SMALL_MID_CAPS = [
    {
        "symbol": "240810",
        "name": "원익IPS",
        "market": "KRX",
        "cap_category": "코스닥 중형주 (소부장)",
        "catalyst_type": "TECH_ORDER",
        "title": "차세대 ALD(원자층증착) 장비 글로벌 파운드리 2나노 양산 라인 공급",
        "summary": "글로벌 선단공정 미세화로 ALD 증착 장비 주문이 급증하며 북미 및 국내 대형 팹향 신규 수주 사이클이 본격화되고 있습니다.",
        "change_rate": "+8.4%",
        "reason": "첨단 선단공정 게이트올어라운드(GAA) 전환에 따른 전공정 장비 공급 모멘텀"
    },
    {
        "symbol": "141080",
        "name": "레고켐바이오",
        "market": "KRX",
        "cap_category": "코스닥 바이오",
        "catalyst_type": "BIO_PIPELINE",
        "title": "차세대 ADC(항체약물접합체) 글로벌 빅파마 기술수출 마일스톤 유입",
        "summary": "자체 링커 플랫폼 기반 파이프라인의 글로벌 임상 진입과 함께 단계별 기술료 수령이 가시화되며 바이오 섹터 투자심리를 견인하고 있습니다.",
        "change_rate": "+6.7%",
        "reason": "빅파마향 공동개발 마일스톤 조기 수령 및 후속 파이프라인 L/O 기대감"
    },
    {
        "symbol": "403870",
        "name": "HPSP",
        "market": "KRX",
        "cap_category": "코스닥 강소기업",
        "catalyst_type": "TECH_PATENT",
        "title": "고압 수소 어닐링 장비 독점적 해자 지속 및 메모리향 적용 확대",
        "summary": "선단 D램 및 낸드 적층 수 증가로 고압 열처리 장비 수요가 폭증하며 고수익성(영업이익률 50%대) 프리미엄이 부각되고 있습니다.",
        "change_rate": "+5.2%",
        "reason": "HBM 고다층화에 따른 계면 결함 개선 필수 장비 독점 지위 유지"
    },
    {
        "symbol": "SMCI",
        "name": "Super Micro Computer",
        "market": "NASDAQ",
        "cap_category": "미국 테크 모멘텀주",
        "catalyst_type": "AI_INFRA",
        "title": "액체냉각(DLC) AI 서버 랙 대규모 출하 개시 소식",
        "summary": "엔비디아 블랙웰 가속기 탑재를 위한 직접 액체 냉각 솔루션 탑재 서버 출하가 증가하며 단기 실적 반등 기대감이 반영되고 있습니다.",
        "change_rate": "+9.8%",
        "reason": "고발열 AI 가속기용 액체냉각 랙 시스템 주문 급증"
    },
    {
        "symbol": "095610",
        "name": "테스",
        "market": "KRX",
        "cap_category": "코스닥 소부장",
        "catalyst_type": "SUPPLY_CONTRACT",
        "title": "메모리 팹 가동률 정상화에 따른 건식 식각·박막 장비 공급 재개",
        "summary": "국내 양대 메모리 제조사의 레거시 및 첨단 팹 보수 투자가 재개되면서 식각(Etch) 장비 납품이 전분기 대비 40% 이상 증가세로 전환했습니다.",
        "change_rate": "+7.1%",
        "reason": "고객사 CAPEX 집행 재개에 따른 반도체 전공정 장비 턴어라운드"
    }
]

FALLBACK_DATA = {
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "macro_indicators": FALLBACK_MACRO,
    "economic_calendar": FALLBACK_CALENDAR,
    "small_mid_caps": FALLBACK_SMALL_MID_CAPS,
    "market_summary": {
        "us_status": "빅테크 실적 및 CPI 발표 앞둔 경계감 속 기술주 중심 선별 랠리",
        "kr_status": "금통위 피벗 기대감과 HBM·소부장 중심 코스닥·코스피 동반 매수세"
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
        except Exception as e:
            logging.warning(f"거시 지표 [{display}] 수집 실패 ({e})")

    if not results or len(results) < 4:
        return FALLBACK_MACRO
    return results


def analyze_market_with_gemini(articles: list, api_key: str, macro_data: list) -> Dict[str, Any]:
    """Gemini API를 호출하여 고도화된 정형 분석 데이터 생성 (중소형주 + 캘린더 포함)"""
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
      "small_mid_caps": [
        {
          "symbol": "종목 티커 (한국은 6자리 숫자, 미국은 티커)",
          "name": "기업명",
          "market": "KRX" | "NASDAQ",
          "cap_category": "코스닥 중소형주 / 소부장 / 바이오 / 스몰캡",
          "catalyst_type": "SUPPLY_CONTRACT" | "BIO_PIPELINE" | "TECH_PATENT" | "M_AND_A" | "THEME",
          "title": "핵심 호재/모멘텀 요약 (수주, 특허, 기술수출, 임상 등)",
          "summary": "세부 내용 2문장",
          "change_rate": "+7.5% 등 변동률",
          "reason": "주목 사유 1줄"
        }
      ],
      "economic_calendar": [
        {
          "id": "cal-01",
          "date": "YYYY-MM-DD",
          "d_day": "D-N 또는 D-Day",
          "country": "US" | "KR",
          "event_name": "이벤트명 (예: 미국 CPI, FOMC 금리결정, 한은 금통위)",
          "importance": "HIGH" | "MEDIUM",
          "forecast_vs_previous": "예상치 vs 이전치 요약",
          "market_impact": "발표 결과가 증시(성장주/가치주/환율)에 미칠 영향 1문장"
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
    당신은 글로벌 헤지펀드의 수석 시장 분석가이자 매크로/섹터/스몰캡 퀀트 리서처입니다.
    제공된 최신 뉴스 기사들과 거시 경제 지표를 심층 분석하여 전문가 수준의 종합 시장 인텔리전스 JSON을 생성하세요.

    [핵심 분석 요구사항]
    1. 거시 & 대형 섹터 밸류체인 이슈 (major_issues, 3~5개):
       - 빅테크 및 반도체/금융/에너지 등 시장 주도 섹터 이슈.
       - 1차 직접 수혜(PRIMARY)와 2차 부품/인프라/낙수효과(SECONDARY)로 밸류체인을 분리할 것.
    2. 중소형 강소기업 & 코스닥/스몰캡 개별 모멘텀주 (small_mid_caps, 4~6개):
       - 대형주(삼성전자, SK하이닉스 등) 외에, 시가총액이 크지 않지만 **독점 수주, 대규모 공급 계약 체결, 바이오 임상/기술이전, 특허, 신기술 상용화, 경영권 지분 경쟁 등 강력한 개별 촉매(Catalyst)**를 보유한 코스닥 및 나스닥 중소형주를 반드시 도출할 것.
    3. 주요 경제 지표 발표 캘린더 (economic_calendar, 3~5개):
       - 다가오는 미국 CPI, FOMC 금리결정, 고용보고서(NFP), 한국은행 금통위 등 증시에 직접적인 파급력을 미칠 주요 경제 이벤트 일정과 관전 포인트를 구성할 것.
    4. 트렌딩 종목 (trending_tickers, 4~6개):
       - 시장에서 현재 거래량과 급등락으로 가장 주목받는 종목 및 사유.

    [입력 거시 지표]:
    {json.dumps(macro_data, ensure_ascii=False)}

    [입력 기사 목록]:
    {json.dumps(articles, ensure_ascii=False, indent=2)}

    [출력 규격]:
    {schema_instruction}
    """

    logging.info("Gemini 2.5 Flash 종합 심층 분석(매크로+중소형주+캘린더) 요청 중...")
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
    if "economic_calendar" not in parsed_json or not parsed_json["economic_calendar"]:
        parsed_json["economic_calendar"] = FALLBACK_CALENDAR
    if "small_mid_caps" not in parsed_json or not parsed_json["small_mid_caps"]:
        parsed_json["small_mid_caps"] = FALLBACK_SMALL_MID_CAPS

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
            logging.info("Gemini 종합 심층 분석 및 JSON 추출 성공!")
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

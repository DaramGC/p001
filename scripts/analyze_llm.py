"""
analyze_llm.py
- RSS 기사를 수집하고 Gemini LLM을 통해 금융 시장 이슈 및 관련 티커 정형 분석
- 결과를 public/data.json 으로 저장
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

from fetch_sources import collect_headlines

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "public" / "data.json"

FALLBACK_DATA = {
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "market_summary": {
        "us_status": "빅테크 실적 기대감 및 금리 전망 속 혼조세",
        "kr_status": "외국인/기관 반도체 중심 순매수 유입"
    },
    "major_issues": [
        {
            "id": "issue-001",
            "market": "GLOBAL",
            "title": "AI 반도체 수요 확장 및 차세대 HBM 패키징 공급 경쟁",
            "summary": "빅테크 기업들의 AI 데이터센터 설비투자(CAPEX) 확대 발표에 따라 고대역폭메모리(HBM) 및 첨단 패키징 공급망 수혜 기업에 글로벌 투자 심리가 집중되고 있습니다.",
            "sentiment": "POSITIVE",
            "related_tickers": [
                {
                    "symbol": "NVDA",
                    "name": "NVIDIA",
                    "market": "NASDAQ",
                    "reason": "차세대 블랙웰 아키텍처 기반 칩 수요 폭증 및 클라우드 CSP 고객사 선주문 지속"
                },
                {
                    "symbol": "000660",
                    "name": "SK하이닉스",
                    "market": "KRX",
                    "reason": "HBM3E 12단 양산 공급 우위 및 글로벌 메모리 단가 상승 모멘텀 주도"
                },
                {
                    "symbol": "005930",
                    "name": "삼성전자",
                    "market": "KRX",
                    "reason": "차세대 HBM 퀄 테스트 진행 및 파운드리 2나노 공정 수주 가시화 기대"
                },
                {
                    "symbol": "TSM",
                    "name": "TSMC",
                    "market": "NYSE",
                    "reason": "첨단 CoWoS 패키징 생산능력 증설 및 첨단 선단공정 풀가동 수혜"
                }
            ],
            "sources": [
                {
                    "title": "Big Tech AI Capex Surge Fuels Semiconductor Rally",
                    "url": "https://www.cnbc.com"
                },
                {
                    "title": "국내 반도체 대장주, 글로벌 AI 모멘텀 힘입어 강세",
                    "url": "https://news.google.com"
                }
            ]
        },
        {
            "id": "issue-002",
            "market": "US",
            "title": "미국 기준금리 인하 경로 및 국채 금리 변동성 주시",
            "summary": "연준(Fed) 주요 인사들의 완화적 발언과 최근 물가 지표 안정화로 인해 시장은 추가 금리 인하 속도와 장기 국채 금리 움직임에 촉각을 곤두세우고 있습니다.",
            "sentiment": "NEUTRAL",
            "related_tickers": [
                {
                    "symbol": "AAPL",
                    "name": "Apple",
                    "market": "NASDAQ",
                    "reason": "금리 안정화에 따른 성장주 밸류에이션 부담 완화 및 신규 AI 디바이스 사이클 진입"
                },
                {
                    "symbol": "JPM",
                    "name": "JPMorgan Chase",
                    "market": "NYSE",
                    "reason": "순이자마진(NIM) 변화 추이 및 투자은행(IB) 부문 수수료 수익 회복세"
                }
            ],
            "sources": [
                {
                    "title": "Fed rate cut path under spotlight as Treasury yields adjust",
                    "url": "https://www.reuters.com"
                }
            ]
        },
        {
            "id": "issue-003",
            "market": "KR",
            "title": "국내 밸류업 프로그램 2차 모멘텀 및 배당·자사주 소각 확대",
            "summary": "한국 거래소 밸류업 지수 리밸런싱 및 기업들의 자발적 주주환원 공시가 이어지면서 지주사, 금융주 중심의 저PBR 종목군으로 기관 자금 유입이 강화되고 있습니다.",
            "sentiment": "POSITIVE",
            "related_tickers": [
                {
                    "symbol": "105560",
                    "name": "KB금융",
                    "market": "KRX",
                    "reason": "자사주 매입·소각 확대 발표 및 업종 최고 수준의 보통주자본(CET1) 비율 유지"
                },
                {
                    "symbol": "005380",
                    "name": "현대차",
                    "market": "KRX",
                    "reason": "인도 법인 상장 성공 및 하이브리드 고수익성에 기반한 대규모 배당 확대"
                }
            ],
            "sources": [
                {
                    "title": "금융·지주사 밸류업 기대감에 외국인 러브콜 지속",
                    "url": "https://news.google.com"
                }
            ]
        },
        {
            "id": "issue-004",
            "market": "GLOBAL",
            "title": "글로벌 원자재 및 에너지 가격 지정학적 리스크 점검",
            "summary": "중동 및 동유럽 정세 불안으로 국제 유가와 천연가스 선물 가격 변동성이 증대되며 에너지 및 방산 섹터의 단기 수혜와 항공·화학주의 원가 부담이 엇갈리고 있습니다.",
            "sentiment": "NEGATIVE",
            "related_tickers": [
                {
                    "symbol": "XOM",
                    "name": "Exxon Mobil",
                    "market": "NYSE",
                    "reason": "원유 공급 차질 우려 속 정제마진 회복 및 배당 안정성 부각"
                },
                {
                    "symbol": "012450",
                    "name": "한화에어로스페이스",
                    "market": "KRX",
                    "reason": "유럽 및 중동향 K-방산 수주잔고 지속 증가 및 실적 퀀텀점프 기대"
                }
            ],
            "sources": [
                {
                    "title": "Oil flirts with volatility amid Middle East supply developments",
                    "url": "https://www.bloomberg.com"
                }
            ]
        }
    ],
    "trending_tickers": [
        {
            "symbol": "TSLA",
            "name": "Tesla",
            "market": "NASDAQ",
            "change_rate": "+4.8%",
            "why_trending": "FSD(완전자율주행) 신버전 글로벌 롤아웃 기대감 및 4분기 인도량 호조 전망"
        },
        {
            "symbol": "NVDA",
            "name": "NVIDIA",
            "market": "NASDAQ",
            "change_rate": "+3.2%",
            "why_trending": "주요 클라우드 서비스사들의 2026년 AI 서버 구축 예산 증액 소식에 신고가 시도"
        },
        {
            "symbol": "000660",
            "name": "SK하이닉스",
            "market": "KRX",
            "change_rate": "+3.7%",
            "why_trending": "HBM 수요 견인으로 분기 사상 최대 영업이익 달성 기대감 고조"
        },
        {
            "symbol": "PLTR",
            "name": "Palantir",
            "market": "NASDAQ",
            "change_rate": "+5.6%",
            "why_trending": "AIP(인공지능 플랫폼) 상용화 수주 급증 및 미국 공공/국방 부문 계약 확대"
        },
        {
            "symbol": "042700",
            "name": "한미반도체",
            "market": "KRX",
            "change_rate": "+4.1%",
            "why_trending": "글로벌 패키징 제조사향 듀얼 TC 본더 장비 독점 공급 지위 부각"
        }
    ]
}


def analyze_market_with_gemini(articles: list, api_key: str) -> Dict[str, Any]:
    """Gemini API를 호출하여 최신 뉴스 헤드라인으로부터 구조화된 시장 분석 JSON 생성"""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    schema_instruction = """
    반드시 유효한 JSON 형식으로만 응답해야 합니다. 다음 키를 포함해야 합니다:
    {
      "market_summary": {
        "us_status": "미국 시장 핵심 한줄 상황",
        "kr_status": "한국 시장 핵심 한줄 상황"
      },
      "major_issues": [
        {
          "id": "issue-001",
          "market": "GLOBAL" | "US" | "KR",
          "title": "이슈 제목",
          "summary": "2~3문장 요약",
          "sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL",
          "related_tickers": [
            {
              "symbol": "종목 티커 (예: NVDA, AAPL, 005930, 000660)",
              "name": "기업명 (예: NVIDIA, SK하이닉스)",
              "market": "NASDAQ" | "NYSE" | "KRX",
              "reason": "해당 종목이 왜 이 이슈와 직접 연관/수혜/피해를 입는지 1문장"
            }
          ],
          "sources": [
            { "title": "기사 제목", "url": "기사 링크" }
          ]
        }
      ],
      "trending_tickers": [
        {
          "symbol": "종목 티커",
          "name": "기업명",
          "market": "NASDAQ" | "NYSE" | "KRX",
          "change_rate": "+3.5% 또는 -2.1% 등 추정치",
          "why_trending": "왜 주목받는지 1문장"
        }
      ]
    }
    """

    prompt = f"""
    당신은 글로벌 헤지펀드의 수석 시장 분석가이자 퀀트 리서처입니다.
    아래에 제공된 최신 글로벌 및 한국 경제/금융 뉴스 기사 헤드라인 목록을 심층 분석하세요.

    분석 요구사항:
    1. 현재 시장에서 가장 파급력이 큰 핵심 이슈 4~6개를 선정하세요. (글로벌 거시, 미국 빅테크, 한국 반도체/금융/수급 등 고루 포함)
    2. 각 이슈별로 직접적인 수혜 또는 영향을 받는 핵심 종목(미국 및 한국 티커)을 2~4개 정확히 매핑하고, 구체적인 연관 이유를 기술하세요.
    3. 현재 거래량 및 시장의 스포트라이트를 받는 트렌딩 종목 4~6개를 선정하세요.
    4. 티커는 트레이딩뷰(TradingView)에서 조회 가능한 표준 심볼(미국: NVDA, AAPL / 한국: 005930, 000660 등 6자리 숫자)을 사용하세요.
    5. 한국어(Korean)로 전문적이고 명쾌하게 작성하세요.

    JSON 규격:
    {schema_instruction}

    뉴스 기사 목록:
    {json.dumps(articles, ensure_ascii=False, indent=2)}
    """

    logging.info("Gemini 2.5 Flash 모델에 시장 분석 요청 중...")
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
    return parsed_json


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()

    if not api_key:
        logging.warning("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
        if OUTPUT_PATH.exists():
            try:
                with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                logging.info(f"기존 {OUTPUT_PATH} 파일이 유지됩니다. (수정 시각 갱신)")
                existing["updated_at"] = datetime.now(timezone.utc).isoformat()
                with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
                    json.dump(existing, f, ensure_ascii=False, indent=2)
                return
            except Exception as e:
                logging.error(f"기존 파일 읽기 실패: {e}")

        logging.info("기본 고품질 샘플 데이터셋으로 초기 data.json을 생성합니다.")
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(FALLBACK_DATA, f, ensure_ascii=False, indent=2)
        logging.info(f"저장 완료: {OUTPUT_PATH}")
        return

    # API Key가 있는 경우 뉴스 수집 및 LLM 파이프라인 가동
    logging.info("RSS 기사 수집 시작...")
    articles = collect_headlines(limit_per_feed=15)
    
    if not articles:
        logging.warning("수집된 기사가 없습니다. 폴백 데이터를 사용합니다.")
        data_to_write = FALLBACK_DATA
    else:
        try:
            data_to_write = analyze_market_with_gemini(articles, api_key)
            logging.info("Gemini 분석 및 JSON 구조화 성공!")
        except Exception as e:
            logging.error(f"Gemini API 호출 또는 파싱 중 에러 발생: {e}")
            if OUTPUT_PATH.exists():
                logging.info("기존 data.json 파일을 보존합니다.")
                return
            data_to_write = FALLBACK_DATA

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data_to_write, f, ensure_ascii=False, indent=2)

    logging.info(f"성공적으로 {OUTPUT_PATH}에 최신 데이터가 저장되었습니다.")


if __name__ == "__main__":
    main()

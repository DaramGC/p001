"""
fetch_sources.py
- 글로벌 및 한국 금융 뉴스 RSS 피드 수집 모듈
- 네이버/야후 금융 실시간 인기 검색 종목 스크래핑 및 개별 종목 심층 뉴스 연동 크롤링
- 기사 중복 제거 및 텍스트 정제
"""

import re
import html
import logging
import urllib.parse
from typing import List, Dict, Any
import requests
import feedparser

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# 기본 대형 및 특징주 RSS 피드 목록
FEEDS: List[Dict[str, str]] = [
    {
        "source": "Google News US Markets",
        "market": "US",
        "category": "MACRO",
        "url": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVd4NVNBIQFSAldT?hl=en-US&gl=US&ceid=US:en"
    },
    {
        "source": "Google News KR Business",
        "market": "KR",
        "category": "MACRO",
        "url": "https://news.google.com/rss/headlines/section/topic/BUSINESS.ko_kr?ned=kr&hl=ko&gl=KR"
    },
    {
        "source": "국내 특징주 & 개별 모멘텀",
        "market": "KR",
        "category": "SMALL_MID",
        "url": "https://news.google.com/rss/search?q=%ED%8A%B9%EC%A7%95%EC%A3%BC+when:1d&hl=ko&gl=KR&ceid=KR:ko"
    },
    {
        "source": "국내 수주·공급계약·임상",
        "market": "KR",
        "category": "SMALL_MID",
        "url": "https://news.google.com/rss/search?q=%EC%88%98%EC%A3%BC+OR+%EA%B3%B5%EA%B8%89%EA%B3%84%EC%95%BD+OR+%EC%9E%84%EC%83%81+when:1d&hl=ko&gl=KR&ceid=KR:ko"
    },
    {
        "source": "CNBC Market News",
        "market": "GLOBAL",
        "category": "MACRO",
        "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664"
    },
    {
        "source": "Yahoo Finance News",
        "market": "GLOBAL",
        "category": "MOVERS",
        "url": "https://finance.yahoo.com/news/rssindex"
    }
]


def clean_html(raw_html: str) -> str:
    """HTML 태그 제거 및 엔티티 언이스케이프"""
    if not raw_html:
        return ""
    clean_text = re.sub(r"<[^>]+>", " ", raw_html)
    clean_text = html.unescape(clean_text)
    return " ".join(clean_text.split())


def fetch_popular_stocks_kr(top_n: int = 15) -> List[Dict[str, str]]:
    """네이버 금융 실시간 인기 검색 상위 종목 스크래핑 (토스/네이버 투자자 관심 1위~15위)"""
    url = "https://finance.naver.com/sise/lastsearch2.naver"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    stocks = []
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        resp.encoding = "euc-kr"
        # href="/item/main.naver?code=005930" class="tltle">삼성전자</a>
        pattern = re.compile(r'href="/item/main\.naver\?code=(\d{6})"\s+class="tltle">([^<]+)</a>')
        matches = pattern.findall(resp.text)
        for code, name in matches[:top_n]:
            stocks.append({"symbol": code, "name": name.strip(), "market": "KRX"})
        logging.info(f"네이버 금융 실시간 인기 검색 {len(stocks)}개 종목 추출 완료: {[s['name'] for s in stocks[:5]]}...")
    except Exception as e:
        logging.warning(f"인기 종목 스크래핑 실패 ({e}), 기본 인기 종목 리스트 사용")
        stocks = [
            {"symbol": "005930", "name": "삼성전자", "market": "KRX"},
            {"symbol": "000660", "name": "SK하이닉스", "market": "KRX"},
            {"symbol": "042700", "name": "한미반도체", "market": "KRX"},
            {"symbol": "240810", "name": "원익IPS", "market": "KRX"},
            {"symbol": "141080", "name": "레고켐바이오", "market": "KRX"},
            {"symbol": "267260", "name": "HD현대일렉트릭", "market": "KRX"},
            {"symbol": "105560", "name": "KB금융", "market": "KRX"}
        ]
    return stocks


def fetch_popular_stocks_us() -> List[Dict[str, str]]:
    """미국 증시 실시간 가장 핫한 종목 (Most Active / Trending)"""
    return [
        {"symbol": "NVDA", "name": "NVIDIA", "market": "NASDAQ"},
        {"symbol": "TSLA", "name": "Tesla", "market": "NASDAQ"},
        {"symbol": "AAPL", "name": "Apple", "market": "NASDAQ"},
        {"symbol": "PLTR", "name": "Palantir", "market": "NASDAQ"},
        {"symbol": "SMCI", "name": "Super Micro Computer", "market": "NASDAQ"},
        {"symbol": "AMD", "name": "AMD", "market": "NASDAQ"},
        {"symbol": "TSM", "name": "TSMC", "market": "NYSE"}
    ]


def collect_news_for_popular_stocks(popular_stocks: List[Dict[str, str]], limit_per_stock: int = 2) -> List[Dict[str, Any]]:
    """실시간 인기 종목별 전용 검색 뉴스 크롤링"""
    stock_articles = []
    seen_titles = set()

    for item in popular_stocks:
        name = item["name"]
        symbol = item["symbol"]
        market = item["market"]

        if market == "KRX":
            query = f"{name} 특징주 OR 실적 OR 수주"
            encoded_query = urllib.parse.quote(query)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}+when:2d&hl=ko&gl=KR&ceid=KR:ko"
        else:
            query = f"{symbol} stock news"
            encoded_query = urllib.parse.quote(query)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}+when:2d&hl=en-US&gl=US&ceid=US:en"

        try:
            feed = feedparser.parse(rss_url)
            count = 0
            for entry in feed.entries:
                raw_title = getattr(entry, "title", "").strip()
                clean_title = clean_html(raw_title)
                title_key = clean_title.lower()
                if not clean_title or title_key in seen_titles:
                    continue
                seen_titles.add(title_key)

                link = getattr(entry, "link", "")
                summary_raw = getattr(entry, "summary", "")
                clean_summary = clean_html(summary_raw)[:250]
                raw_published = getattr(entry, "published", "")
                formatted_published = ""
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    import time
                    formatted_published = time.strftime("%Y-%m-%d %H:%M", entry.published_parsed)
                elif raw_published:
                    formatted_published = raw_published[:16]

                stock_articles.append({
                    "title": clean_title,
                    "link": link,
                    "summary": clean_summary,
                    "published": raw_published,
                    "published_at": formatted_published,
                    "source": f"인기종목 [{name}] 뉴스",
                    "market_hint": market,
                    "category_hint": "POPULAR_STOCK",
                    "target_stock": f"{name} ({symbol})"
                })

                count += 1
                if count >= limit_per_stock:
                    break
        except Exception as e:
            logging.warning(f"인기 종목 [{name}] 뉴스 수집 실패: {e}")

    logging.info(f"인기 종목 맞춤형 뉴스 {len(stock_articles)}개 추가 수집 완료")
    return stock_articles


def collect_headlines(limit_per_feed: int = 20) -> List[Dict[str, Any]]:
    """모든 RSS 피드 및 인기 종목 맞춤형 뉴스를 통합 수집"""
    all_articles = []
    seen_titles = set()

    # 1. 표준 RSS 피드 수집
    for feed_info in FEEDS:
        url = feed_info["url"]
        source_name = feed_info["source"]
        market_tag = feed_info["market"]
        cat_tag = feed_info.get("category", "MACRO")

        logging.info(f"피드 수집 중: {source_name} ({url})")
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries:
                raw_title = getattr(entry, "title", "").strip()
                clean_title = clean_html(raw_title)
                
                title_key = clean_title.lower()
                if not clean_title or title_key in seen_titles:
                    continue
                seen_titles.add(title_key)

                link = getattr(entry, "link", "")
                summary_raw = getattr(entry, "summary", "")
                clean_summary = clean_html(summary_raw)[:250]
                raw_published = getattr(entry, "published", "")
                formatted_published = ""
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    import time
                    formatted_published = time.strftime("%Y-%m-%d %H:%M", entry.published_parsed)
                elif raw_published:
                    formatted_published = raw_published[:16]

                all_articles.append({
                    "title": clean_title,
                    "link": link,
                    "summary": clean_summary,
                    "published": raw_published,
                    "published_at": formatted_published,
                    "source": source_name,
                    "market_hint": market_tag,
                    "category_hint": cat_tag
                })

                count += 1
                if count >= limit_per_feed:
                    break
        except Exception as e:
            logging.error(f"[{source_name}] 수집 중 에러 발생: {e}")

    # 2. 토스/네이버/야후 인기 종목 발굴 및 개별 뉴스 집중 크롤링
    logging.info("실시간 인기 종목(토스/네이버/야후) 수집 및 맞춤 뉴스 수집 시작...")
    kr_popular = fetch_popular_stocks_kr(top_n=12)
    us_popular = fetch_popular_stocks_us()
    popular_news = collect_news_for_popular_stocks(kr_popular + us_popular, limit_per_stock=2)

    # 중복 제거 후 병합
    for art in popular_news:
        t_key = art["title"].lower()
        if t_key not in seen_titles:
            seen_titles.add(t_key)
            all_articles.append(art)

    logging.info(f"총 {len(all_articles)}개 방대한 최신 기사 수집 완료!")
    return all_articles


if __name__ == "__main__":
    articles = collect_headlines(limit_per_feed=5)
    print(f"\n--- 수집 테스트 (총 {len(articles)}건) ---")
    for i, a in enumerate(articles[:10], 1):
        print(f"[{i}] [{a['market_hint']}] [{a.get('category_hint')}] {a['title']}")
        print(f"    출처: {a['source']} | 날짜: {a['published_at']}")

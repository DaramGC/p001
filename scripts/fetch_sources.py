"""
fetch_sources.py
- 글로벌 및 한국 금융 뉴스 RSS 피드 수집 모듈
- 기사 중복 제거 및 텍스트 정제
"""

import re
import html
import logging
from typing import List, Dict, Any
import feedparser

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# RSS 피드 목록 (대형 매크로 + 중소형 특징주 및 수주/임상/테마 집중 피드)
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


def collect_headlines(limit_per_feed: int = 15) -> List[Dict[str, Any]]:
    """모든 RSS 피드에서 뉴스 헤드라인을 수집하여 정제된 리스트 반환"""
    all_articles = []
    seen_titles = set()

    for feed_info in FEEDS:
        url = feed_info["url"]
        source_name = feed_info["source"]
        market_tag = feed_info["market"]

        logging.info(f"피드 수집 중: {source_name} ({url})")
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries:
                raw_title = getattr(entry, "title", "").strip()
                clean_title = clean_html(raw_title)
                
                # 중복 및 빈 제목 필터링
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

                market_tag = feed_info["market"]
                cat_tag = feed_info.get("category", "MACRO")

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

            logging.info(f"[{source_name}] {count}개 기사 수집 완료")
        except Exception as e:
            logging.error(f"[{source_name}] 수집 중 에러 발생: {e}")

    logging.info(f"총 {len(all_articles)}개 고유 기사 수집됨")
    return all_articles


if __name__ == "__main__":
    articles = collect_headlines(limit_per_feed=5)
    print(f"\n--- 수집 테스트 (총 {len(articles)}건) ---")
    for i, a in enumerate(articles[:5], 1):
        print(f"[{i}] [{a['market_hint']}] {a['title']}")
        print(f"    출처: {a['source']} | 링크: {a['link']}")

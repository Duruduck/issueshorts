"""
scripts/collect.py
국내외 소스에서 트렌딩 이슈를 수집해 public/topics.json 생성

소스 구성 (API 키 불필요):
  [해외 - K-pop]   Soompi RSS, AllKPop RSS
  [해외 - 이슈]    Google Trends RSS, Hacker News API
  [국내]           에펨코리아, 루리웹, 클리앙 RSS
  [국내 선택]       네이버 DataLab (NAVER_CLIENT_ID/SECRET 필요)

환경변수:
  선택: NAVER_CLIENT_ID, NAVER_CLIENT_SECRET
"""

import os
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

try:
    import feedparser
    FEED_OK = True
except ImportError:
    FEED_OK = False

try:
    import requests
    REQ_OK = True
except ImportError:
    REQ_OK = False

OUTPUT = Path(__file__).parent.parent / "public" / "topics.json"

# ── 카테고리 자동 분류 ────────────────────────────────────────

CATEGORY_RULES = {
    "kpop":    ["kpop","k-pop","bts","blackpink","aespa","newjeans","ive","stray kids",
                "seventeen","twice","exo","nct","idol","아이돌","케이팝","컴백","팬덤",
                "concert","comeback","jennie","lisa","jimin","jungkook","taehyung"],
    "social":  ["탈북","북한","사건","사고","논란","화제","유튜버","실화","인물","스토리",
                "korea","korean","seoul"],
    "culture": ["food","recipe","korean food","kimchi","bibimbap","ramen","tteokbokki",
                "bulgogi","한식","요리","레시피","맛집","음식","k-food","mukbang"],
    "beauty":  ["skincare","makeup","beauty","sunscreen","serum","moisturizer","toner",
                "뷰티","스킨케어","화장품","선크림","세럼","k-beauty","foundation"],
    "living":  ["kitchen","home","organizer","cleaning","daiso","gadget","product",
                "다이소","주방","청소","생활용품","정리","가전","review"],
    "season":  ["summer","winter","season","시즌","여름","겨울","필수템","품절","seasonal",
                "spring","fall","trend"],
}

def classify(text: str) -> str:
    t = text.lower()
    for cat, kws in CATEGORY_RULES.items():
        if any(kw in t for kw in kws):
            return cat
    return None

def format_ago(dt: datetime) -> str:
    diff = datetime.now() - dt
    mins = int(diff.total_seconds() / 60)
    if mins < 60:
        return f"{mins}분 전"
    hours = mins // 60
    if hours < 24:
        return f"{hours}시간 전"
    return f"{hours // 24}일 전"

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


# ── 1. 해외 RSS (API 키 불필요) ──────────────────────────────

OVERSEAS_RSS = [
    # K-pop / 연예
    {
        "name": "Soompi",
        "url":  "https://www.soompi.com/feed",
        "source": "해외",
        "type": "kpop",
    },
    {
        "name": "AllKPop",
        "url":  "https://www.allkpop.com/rss",
        "source": "해외",
        "type": "kpop",
    },
    # 한식/문화 해외 반응
    {
        "name": "Korean Bapsang",
        "url":  "https://www.koreanbapsang.com/feed/",
        "source": "해외",
        "type": "culture",
    },
    # 해외 트렌드
    {
        "name": "Google Trends (US)",
        "url":  "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US",
        "source": "해외",
        "type": "overseas",
    },
    {
        "name": "Google Trends (KR)",
        "url":  "https://trends.google.com/trends/trendingsearches/daily/rss?geo=KR",
        "source": "국내",
        "type": "social",
    },
]

def collect_overseas_rss() -> list[dict]:
    if not FEED_OK:
        print("[해외RSS] feedparser 없음, 스킵"); return []
    results = []
    for f in OVERSEAS_RSS:
        try:
            feed = feedparser.parse(f["url"])
            count = 0
            for entry in feed.entries[:15]:
                title = entry.get("title", "").strip()
                if not title:
                    continue
                cat = classify(title) or f["type"]
                results.append({
                    "type":   cat,
                    "title":  title,
                    "source": f["source"],
                    "from":   f["name"],
                    "url":    entry.get("link", ""),
                    "score":  100,   # RSS 기준 점수 기본값
                    "comments": 0,
                    "collected_at": now_str(),
                })
                count += 1
            print(f"  [{f['name']}] {count}개")
            time.sleep(0.5)
        except Exception as e:
            print(f"  [{f['name']}] 실패: {e}")
    print(f"[해외RSS] 총 {len(results)}개 수집")
    return results


# ── 2. Hacker News (API 키 불필요) ──────────────────────────

HN_TOP_URL  = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"

def collect_hackernews(limit: int = 20) -> list[dict]:
    if not REQ_OK:
        print("[HackerNews] requests 없음, 스킵"); return []
    results = []
    try:
        ids = requests.get(HN_TOP_URL, timeout=10).json()[:limit]
        for story_id in ids:
            try:
                item = requests.get(HN_ITEM_URL.format(story_id), timeout=5).json()
                title = item.get("title", "").strip()
                if not title:
                    continue
                cat = classify(title) or "overseas"
                results.append({
                    "type":   cat,
                    "title":  title,
                    "source": "해외",
                    "from":   "Hacker News",
                    "url":    item.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                    "score":  item.get("score", 0),
                    "comments": item.get("descendants", 0),
                    "collected_at": now_str(),
                })
            except Exception:
                continue
        print(f"[HackerNews] {len(results)}개 수집")
    except Exception as e:
        print(f"[HackerNews] 실패: {e}")
    return results


# ── 3. 국내 RSS ──────────────────────────────────────────────

DOMESTIC_RSS = [
    {"name":"에펨코리아/핫딜",  "url":"https://www.fmkorea.com/index.php?mid=hotdeal&act=rss", "source":"국내","type":"living"},
    {"name":"에펨코리아/가성비", "url":"https://www.fmkorea.com/index.php?mid=frugal&act=rss",  "source":"국내","type":"living"},
    {"name":"루리웹/핫딜",      "url":"https://bbs.ruliweb.com/news/board/1020?type=rss",       "source":"국내","type":"living"},
    {"name":"클리앙/알뜰구매",  "url":"https://www.clien.net/service/board/jiboard?rss=true",  "source":"국내","type":"living"},
]

def collect_domestic_rss() -> list[dict]:
    if not FEED_OK:
        print("[국내RSS] feedparser 없음, 스킵"); return []
    results = []
    for f in DOMESTIC_RSS:
        try:
            feed = feedparser.parse(f["url"])
            count = 0
            for entry in feed.entries[:10]:
                title = entry.get("title", "").strip()
                if not title:
                    continue
                results.append({
                    "type":   classify(title) or f["type"],
                    "title":  title,
                    "source": f["source"],
                    "from":   f["name"],
                    "url":    entry.get("link", ""),
                    "score":  len(title),
                    "comments": 0,
                    "collected_at": now_str(),
                })
                count += 1
            print(f"  [{f['name']}] {count}개")
            time.sleep(0.3)
        except Exception as e:
            print(f"  [{f['name']}] 실패: {e}")
    print(f"[국내RSS] 총 {len(results)}개 수집")
    return results


# ── 4. 네이버 DataLab (선택) ─────────────────────────────────

NAVER_CATS = [
    {"name":"뷰티",     "categoryId":"50000002", "type":"beauty"},
    {"name":"패션의류",  "categoryId":"50000000", "type":"beauty"},
    {"name":"생활/건강", "categoryId":"50000006", "type":"living"},
    {"name":"주방용품",  "categoryId":"50000003", "type":"living"},
]

def collect_naver() -> list[dict]:
    if not REQ_OK: return []
    cid = os.environ.get("NAVER_CLIENT_ID", "")
    cs  = os.environ.get("NAVER_CLIENT_SECRET", "")
    if not cid:
        print("[Naver] 환경변수 없음, 스킵"); return []
    today = datetime.now()
    results = []
    try:
        resp = requests.post(
            "https://openapi.naver.com/v1/datalab/shopping/categories",
            headers={
                "X-Naver-Client-Id": cid,
                "X-Naver-Client-Secret": cs,
                "Content-Type": "application/json",
            },
            json={
                "startDate": (today - timedelta(days=7)).strftime("%Y-%m-%d"),
                "endDate":   today.strftime("%Y-%m-%d"),
                "timeUnit":  "date",
                "category":  [{"name":c["name"],"param":[{"name":c["name"],"categoryId":c["categoryId"]}]} for c in NAVER_CATS],
            },
            timeout=10,
        )
        for item in resp.json().get("results", []):
            ratios = [d["ratio"] for d in item.get("data", [])]
            if len(ratios) >= 2 and ratios[-1] > ratios[-2]:
                cat = next((c for c in NAVER_CATS if c["name"] == item["title"]), None)
                results.append({
                    "type":   cat["type"] if cat else "living",
                    "title":  f"[네이버 급상승] {item['title']} 카테고리 검색량 급증",
                    "source": "국내",
                    "from":   "네이버 DataLab",
                    "url":    "https://datalab.naver.com/shoppingInsight/sCategory.naver",
                    "score":  round(ratios[-1] * 10),
                    "comments": 0,
                    "collected_at": now_str(),
                })
        print(f"[Naver] {len(results)}개 수집")
    except Exception as e:
        print(f"[Naver] 실패: {e}")
    return results


# ── 점수 산정 & TOP 20 선별 ──────────────────────────────────

def score_and_select(items: list[dict], n: int = 20) -> list[dict]:
    if not items: return []
    max_score = max((i["score"] for i in items), default=1) or 1
    for item in items:
        buzz = item["score"] * 1 + item["comments"] * 2
        item["heat"] = min(99, round(buzz / max_score * 100))

    from collections import Counter
    cat_count: Counter = Counter()
    top = []
    for item in sorted(items, key=lambda x: x["heat"], reverse=True):
        limit = 5 if item["type"] in ("overseas", "kpop") else 4
        if cat_count[item["type"]] < limit:
            top.append(item)
            cat_count[item["type"]] += 1
        if len(top) >= n:
            break
    return top


# ── 출력 포맷 ─────────────────────────────────────────────────

def format_output(items: list[dict]) -> list[dict]:
    result = []
    for i, item in enumerate(items, start=1):
        try:
            dt  = datetime.strptime(item.get("collected_at", ""), "%Y-%m-%d %H:%M")
            ago = format_ago(dt)
        except Exception:
            ago = "방금 전"
        result.append({
            "id":           i,
            "type":         item["type"],
            "title":        item["title"],
            "source":       item["source"],
            "from":         item["from"],
            "ago":          ago,
            "heat":         item["heat"],
            "url":          item.get("url", ""),
            "collected_at": item.get("collected_at", ""),
        })
    return result


# ── 메인 ─────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print(f"  이슈 수집 시작: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 55)

    all_items = []

    print("\n[1/4] 해외 RSS 수집...")
    all_items.extend(collect_overseas_rss())

    print("\n[2/4] Hacker News 수집...")
    all_items.extend(collect_hackernews(limit=20))

    print("\n[3/4] 국내 RSS 수집...")
    all_items.extend(collect_domestic_rss())

    print("\n[4/4] 네이버 DataLab 수집...")
    all_items.extend(collect_naver())

    print(f"\n총 {len(all_items)}개 수집")

    if not all_items:
        print("수집 결과 없음 — 빈 배열 저장")
        OUTPUT.write_text("[]", encoding="utf-8")
        return

    top    = score_and_select(all_items, n=20)
    output = format_output(top)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    from collections import Counter
    type_dist = Counter(item["type"]   for item in output)
    src_dist  = Counter(item["source"] for item in output)
    print(f"\n✅ {len(output)}개 저장 완료")
    print(f"  카테고리: {dict(type_dist)}")
    print(f"  소스:     {dict(src_dist)}")


if __name__ == "__main__":
    main()

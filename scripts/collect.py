"""
scripts/collect.py
국내외 소스에서 트렌딩 이슈를 수집해 public/topics.json 생성

소스:
  [국내 커뮤니티]  에펨코리아, 루리웹, 클리앙 RSS
  [국내 뉴스]      연합뉴스 연예/사회 RSS
  [해외 이슈]      Google Trends (US), Hacker News API
  [국내 선택]       네이버 DataLab

핵심 원칙:
  - 점수는 소스별 순위 기반 정규화 (원시 숫자 비교 X)
  - 국내/해외 균형 보장 (각 최소 40%)
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
    "kpop":    ["bts","blackpink","aespa","newjeans","ive","stray kids","seventeen",
                "twice","exo","nct","kpop","k-pop","아이돌","케이팝","컴백","팬덤",
                "concert","comeback","뮤비","음반","데뷔","걸그룹","보이그룹"],
    "social":  ["탈북","북한","사건","사고","논란","화제","유튜버","실화","인물",
                "스토리","검찰","경찰","정치","사회","연예인","배우","가수"],
    "culture": ["한식","요리","레시피","맛집","음식","food","recipe","kimchi",
                "bibimbap","ramen","k-food","mukbang","먹방"],
    "beauty":  ["뷰티","스킨케어","화장품","선크림","세럼","립","쿠션","파운데이션",
                "beauty","skincare","makeup","sunscreen","serum","k-beauty"],
    "living":  ["다이소","주방","청소","생활용품","정리","가전","핫딜","할인",
                "가성비","추천","구매","kitchen","home","gadget","deal"],
    "season":  ["시즌","여름","겨울","봄","가을","필수템","품절","seasonal",
                "summer","winter","spring","fall","신상","출시"],
}

def classify(text: str) -> str:
    t = text.lower()
    for cat, kws in CATEGORY_RULES.items():
        if any(kw in t for kw in kws):
            return cat
    return None

def rank_score(rank: int, total: int = 20) -> int:
    """순위 기반 점수 (1위=100, 꼴찌=50) — 소스 간 공평 비교"""
    return max(50, 100 - int((rank - 1) / max(total - 1, 1) * 50))

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


# ── 1. 국내 커뮤니티 RSS ──────────────────────────────────────

COMMUNITY_RSS = [
    {"name":"에펨코리아/핫딜",  "url":"https://www.fmkorea.com/index.php?mid=hotdeal&act=rss",
     "source":"국내", "type":"living"},
    {"name":"에펨코리아/가성비", "url":"https://www.fmkorea.com/index.php?mid=frugal&act=rss",
     "source":"국내", "type":"living"},
    {"name":"루리웹/핫딜",      "url":"https://bbs.ruliweb.com/news/board/1020?type=rss",
     "source":"국내", "type":"living"},
    {"name":"클리앙/알뜰구매",  "url":"https://www.clien.net/service/board/jiboard?rss=true",
     "source":"국내", "type":"living"},
]

def collect_community_rss() -> list[dict]:
    if not FEED_OK:
        print("[커뮤니티RSS] feedparser 없음, 스킵"); return []
    results = []
    for f in COMMUNITY_RSS:
        try:
            feed = feedparser.parse(f["url"])
            entries = [e for e in feed.entries if e.get("title","").strip()][:15]
            for rank, entry in enumerate(entries, start=1):
                title = entry["title"].strip()
                results.append({
                    "type":   classify(title) or f["type"],
                    "title":  title,
                    "source": f["source"],
                    "from":   f["name"],
                    "url":    entry.get("link",""),
                    "score":  rank_score(rank, len(entries)),
                    "collected_at": now_str(),
                })
            print(f"  [{f['name']}] {len(entries)}개")
            time.sleep(0.3)
        except Exception as e:
            print(f"  [{f['name']}] 실패: {e}")
    print(f"[커뮤니티RSS] 총 {len(results)}개")
    return results


# ── 2. 국내 뉴스 RSS ──────────────────────────────────────────

NEWS_RSS = [
    {"name":"연합뉴스/연예",  "url":"https://www.yna.co.kr/rss/entertainment.xml",
     "source":"국내", "type":"kpop"},
    {"name":"연합뉴스/사회",  "url":"https://www.yna.co.kr/rss/society.xml",
     "source":"국내", "type":"social"},
    {"name":"연합뉴스/생활",  "url":"https://www.yna.co.kr/rss/lifestyle.xml",
     "source":"국내", "type":"living"},
]

def collect_news_rss() -> list[dict]:
    if not FEED_OK:
        print("[뉴스RSS] feedparser 없음, 스킵"); return []
    results = []
    for f in NEWS_RSS:
        try:
            feed = feedparser.parse(f["url"])
            entries = [e for e in feed.entries if e.get("title","").strip()][:10]
            for rank, entry in enumerate(entries, start=1):
                title = entry["title"].strip()
                results.append({
                    "type":   classify(title) or f["type"],
                    "title":  title,
                    "source": f["source"],
                    "from":   f["name"],
                    "url":    entry.get("link",""),
                    "score":  rank_score(rank, len(entries)),
                    "collected_at": now_str(),
                })
            print(f"  [{f['name']}] {len(entries)}개")
            time.sleep(0.3)
        except Exception as e:
            print(f"  [{f['name']}] 실패: {e}")
    print(f"[뉴스RSS] 총 {len(results)}개")
    return results


# ── 3. Google Trends (해외) ──────────────────────────────────

def collect_google_trends() -> list[dict]:
    if not FEED_OK:
        print("[Google Trends] feedparser 없음, 스킵"); return []
    results = []
    url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US"
    try:
        feed = feedparser.parse(url)
        entries = [e for e in feed.entries if e.get("title","").strip()][:15]
        for rank, entry in enumerate(entries, start=1):
            title = entry["title"].strip()
            results.append({
                "type":   classify(title) or "overseas",
                "title":  title,
                "source": "해외",
                "from":   "Google Trends (US)",
                "url":    entry.get("link",""),
                "score":  rank_score(rank, len(entries)),
                "collected_at": now_str(),
            })
        print(f"[Google Trends] {len(results)}개")
    except Exception as e:
        print(f"[Google Trends] 실패: {e}")
    return results


# ── 4. Hacker News ───────────────────────────────────────────

def collect_hackernews(limit: int = 15) -> list[dict]:
    if not REQ_OK:
        print("[HackerNews] requests 없음, 스킵"); return []
    results = []
    try:
        ids = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            timeout=10
        ).json()[:limit]

        for rank, story_id in enumerate(ids, start=1):
            try:
                item = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                    timeout=5
                ).json()
                title = item.get("title","").strip()
                if not title:
                    continue
                results.append({
                    "type":   classify(title) or "overseas",
                    "title":  title,
                    "source": "해외",
                    "from":   "Hacker News",
                    "url":    item.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                    "score":  rank_score(rank, limit),   # 순위 기반 (원시 업보트 X)
                    "collected_at": now_str(),
                })
            except Exception:
                continue
        print(f"[HackerNews] {len(results)}개")
    except Exception as e:
        print(f"[HackerNews] 실패: {e}")
    return results


# ── 5. 네이버 DataLab (선택) ─────────────────────────────────

NAVER_CATS = [
    {"name":"뷰티",     "categoryId":"50000002", "type":"beauty"},
    {"name":"패션의류",  "categoryId":"50000000", "type":"beauty"},
    {"name":"생활/건강", "categoryId":"50000006", "type":"living"},
    {"name":"주방용품",  "categoryId":"50000003", "type":"living"},
]

def collect_naver() -> list[dict]:
    if not REQ_OK: return []
    cid = os.environ.get("NAVER_CLIENT_ID","")
    cs  = os.environ.get("NAVER_CLIENT_SECRET","")
    if not cid:
        print("[Naver] 환경변수 없음, 스킵"); return []
    today = datetime.now()
    results = []
    try:
        resp = requests.post(
            "https://openapi.naver.com/v1/datalab/shopping/categories",
            headers={"X-Naver-Client-Id":cid,"X-Naver-Client-Secret":cs,"Content-Type":"application/json"},
            json={
                "startDate": (today - timedelta(days=7)).strftime("%Y-%m-%d"),
                "endDate":   today.strftime("%Y-%m-%d"),
                "timeUnit":  "date",
                "category":  [{"name":c["name"],"param":[{"name":c["name"],"categoryId":c["categoryId"]}]} for c in NAVER_CATS],
            },
            timeout=10,
        )
        for item in resp.json().get("results",[]):
            ratios = [d["ratio"] for d in item.get("data",[])]
            if len(ratios) >= 2 and ratios[-1] > ratios[-2]:
                cat = next((c for c in NAVER_CATS if c["name"]==item["title"]), None)
                results.append({
                    "type":   cat["type"] if cat else "living",
                    "title":  f"[급상승] {item['title']} 검색량 증가 중",
                    "source": "국내",
                    "from":   "네이버 DataLab",
                    "url":    "https://datalab.naver.com/shoppingInsight/sCategory.naver",
                    "score":  80,
                    "collected_at": now_str(),
                })
        print(f"[Naver] {len(results)}개")
    except Exception as e:
        print(f"[Naver] 실패: {e}")
    return results


# ── 점수 산정 & 국내/해외 균형 TOP 20 ────────────────────────

def select_balanced(items: list[dict], n: int = 20) -> list[dict]:
    if not items: return []

    domestic = [i for i in items if i["source"] == "국내"]
    overseas = [i for i in items if i["source"] == "해외"]

    from collections import Counter

    def pick(pool, count, cat_limit=3):
        cat_count: Counter = Counter()
        selected = []
        for item in sorted(pool, key=lambda x: x["score"], reverse=True):
            if cat_count[item["type"]] < cat_limit:
                selected.append(item)
                cat_count[item["type"]] += 1
            if len(selected) >= count:
                break
        return selected

    # 국내 40% 이상, 해외 40% 이상 보장
    domestic_n = max(int(n * 0.45), 8)
    overseas_n = max(n - domestic_n, 8)

    top = pick(domestic, domestic_n) + pick(overseas, overseas_n)

    # 부족하면 나머지로 채우기
    if len(top) < n:
        used = set(id(i) for i in top)
        rest = [i for i in items if id(i) not in used]
        top += pick(rest, n - len(top))

    return top[:n]


# ── 출력 포맷 ─────────────────────────────────────────────────

def format_output(items: list[dict]) -> list[dict]:
    result = []
    for i, item in enumerate(items, start=1):
        try:
            dt  = datetime.strptime(item.get("collected_at",""), "%Y-%m-%d %H:%M")
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
            "heat":         item["score"],
            "url":          item.get("url",""),
            "collected_at": item.get("collected_at",""),
        })
    return result


# ── 메인 ─────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print(f"  이슈 수집 시작: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 55)

    all_items = []

    print("\n[1/5] 국내 커뮤니티 RSS...")
    all_items.extend(collect_community_rss())

    print("\n[2/5] 국내 뉴스 RSS...")
    all_items.extend(collect_news_rss())

    print("\n[3/5] Google Trends (US)...")
    all_items.extend(collect_google_trends())

    print("\n[4/5] Hacker News...")
    all_items.extend(collect_hackernews(limit=15))

    print("\n[5/5] 네이버 DataLab...")
    all_items.extend(collect_naver())

    print(f"\n총 {len(all_items)}개 수집")

    if not all_items:
        print("수집 결과 없음 — 빈 배열 저장")
        OUTPUT.write_text("[]", encoding="utf-8")
        return

    top    = select_balanced(all_items, n=20)
    output = format_output(top)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    from collections import Counter
    type_dist = Counter(item["type"]   for item in output)
    src_dist  = Counter(item["source"] for item in output)
    print(f"\n✅ {len(output)}개 저장")
    print(f"  카테고리: {dict(type_dist)}")
    print(f"  소스:     국내 {src_dist['국내']}개 | 해외 {src_dist['해외']}개")


if __name__ == "__main__":
    main()

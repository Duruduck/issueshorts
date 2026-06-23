"""
scripts/collect.py
국내외 소스에서 트렌딩 이슈를 수집해 public/topics.json 생성

소스 구성:
  [해외 - 한국관련]  Reddit r/kpop, r/korea, r/KoreanFood 등
  [해외 - 해외이슈]  Reddit r/worldnews, r/technology, r/BuyItForLife 등
  [국내]            에펨코리아, 루리웹, 클리앙 RSS
  [국내 선택]        네이버 DataLab

환경변수:
  필수: REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET
  선택: NAVER_CLIENT_ID, NAVER_CLIENT_SECRET
"""

import os
import json
import time
import random
from datetime import datetime, timedelta
from pathlib import Path

try:
    import praw
    PRAW_OK = True
except ImportError:
    PRAW_OK = False

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
    "kpop":    ["kpop","k-pop","bts","blackpink","aespa","newjeans","ive",
                "stray kids","seventeen","twice","exo","nct","idol",
                "아이돌","케이팝","컴백","팬덤","concert","comeback"],
    "social":  ["탈북","북한","사건","사고","논란","화제","유튜버","실화","인물","스토리"],
    "culture": ["food","recipe","korean food","kimchi","bibimbap","ramen",
                "tteokbokki","bulgogi","한식","요리","레시피","맛집","음식","k-food"],
    "beauty":  ["skincare","makeup","beauty","sunscreen","serum","moisturizer",
                "뷰티","스킨케어","화장품","선크림","세럼","k-beauty"],
    "living":  ["kitchen","home","organizer","cleaning","daiso","gadget","amazon",
                "다이소","주방","청소","생활용품","정리","가전"],
    "season":  ["summer","winter","season","시즌","여름","겨울","필수템","품절","seasonal"],
}

def classify(text: str) -> str:
    """제목에서 카테고리 자동 분류. 매칭 없으면 None 반환."""
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


# ── 1. Reddit 수집 ────────────────────────────────────────────
#
# 그룹 A: 한국 관련 서브레딧
#   source = "해외" (Reddit 플랫폼)
#   type   = 키워드 분류 우선, 없으면 서브레딧 기본값
#
# 그룹 B: 해외 트렌드 서브레딧
#   source = "해외"
#   type   = "overseas" 고정 (키워드 분류 무시)
#   → 앱의 "해외 이슈" 카테고리를 채움

# 그룹 A: 한국 관련 (키워드로 type 분류)
KOREA_SUBS = {
    "kpop":        "kpop",     # K-pop 전반
    "korea":       "social",   # 한국 사회/인물
    "KoreanFood":  "culture",  # 한식 문화
    "korean":      "culture",  # 한국어/문화 일반
    "asianbeauty": "beauty",   # K-뷰티 해외 반응
}

# 그룹 B: 해외 트렌드 (항상 type="overseas")
OVERSEAS_SUBS = [
    "worldnews",     # 세계 뉴스
    "technology",    # 테크 트렌드
    "BuyItForLife",  # 해외 소비 트렌드
    "todayilearned", # 화제 지식
    "interestingasfuck",  # 바이럴 콘텐츠
]

def _fetch_sub(reddit, sub_name: str, limit: int = 15, cutoff: datetime = None) -> list[dict]:
    results = []
    try:
        for post in reddit.subreddit(sub_name).hot(limit=limit):
            created = datetime.fromtimestamp(post.created_utc)
            if cutoff and created < cutoff:
                continue
            results.append({
                "_sub":     sub_name,
                "title":    post.title,
                "url":      f"https://reddit.com{post.permalink}",
                "score":    post.score,
                "comments": post.num_comments,
                "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
        time.sleep(random.uniform(0.5, 1.0))
    except Exception as e:
        print(f"[Reddit] r/{sub_name} 실패: {e}")
    return results

def collect_reddit() -> list[dict]:
    if not PRAW_OK:
        print("[Reddit] praw 없음, 스킵"); return []
    cid = os.environ.get("REDDIT_CLIENT_ID", "")
    cs  = os.environ.get("REDDIT_CLIENT_SECRET", "")
    if not cid or not cs:
        print("[Reddit] 환경변수 없음, 스킵"); return []

    cutoff = datetime.now() - timedelta(hours=48)
    results = []

    try:
        reddit = praw.Reddit(
            client_id=cid, client_secret=cs,
            user_agent="IssueShortsCollector/1.0"
        )

        # 그룹 A: 한국 관련 서브레딧
        for sub_name, default_type in KOREA_SUBS.items():
            for raw in _fetch_sub(reddit, sub_name, cutoff=cutoff):
                cat = classify(raw["title"]) or default_type
                results.append({
                    "type":   cat,
                    "title":  raw["title"],
                    "source": "해외",
                    "from":   f"r/{sub_name}",
                    "url":    raw["url"],
                    "score":  raw["score"],
                    "comments": raw["comments"],
                    "collected_at": raw["collected_at"],
                })

        # 그룹 B: 해외 트렌드 (type 항상 overseas)
        for sub_name in OVERSEAS_SUBS:
            for raw in _fetch_sub(reddit, sub_name, limit=10, cutoff=cutoff):
                results.append({
                    "type":   "overseas",   # 고정
                    "title":  raw["title"],
                    "source": "해외",
                    "from":   f"r/{sub_name}",
                    "url":    raw["url"],
                    "score":  raw["score"],
                    "comments": raw["comments"],
                    "collected_at": raw["collected_at"],
                })

    except Exception as e:
        print(f"[Reddit] 초기화 실패: {e}")

    a_count = sum(1 for r in results if r["type"] != "overseas")
    b_count = sum(1 for r in results if r["type"] == "overseas")
    print(f"[Reddit] 한국관련: {a_count}개 | 해외이슈: {b_count}개 | 합계: {len(results)}개")
    return results


# ── 2. 국내 RSS ──────────────────────────────────────────────

RSS_FEEDS = [
    {"name":"에펨코리아/핫딜",  "url":"https://www.fmkorea.com/index.php?mid=hotdeal&act=rss", "source":"국내","type":"living"},
    {"name":"에펨코리아/가성비", "url":"https://www.fmkorea.com/index.php?mid=frugal&act=rss",  "source":"국내","type":"living"},
    {"name":"루리웹/핫딜",      "url":"https://bbs.ruliweb.com/news/board/1020?type=rss",       "source":"국내","type":"living"},
    {"name":"클리앙/알뜰구매",  "url":"https://www.clien.net/service/board/jiboard?rss=true",  "source":"국내","type":"living"},
]

def collect_rss() -> list[dict]:
    if not FEED_OK:
        print("[RSS] feedparser 없음, 스킵"); return []
    results = []
    for f in RSS_FEEDS:
        try:
            feed = feedparser.parse(f["url"])
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
                    "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                })
        except Exception as e:
            print(f"[RSS] {f['name']} 실패: {e}")
    print(f"[RSS] {len(results)}개 수집")
    return results


# ── 3. 네이버 DataLab (선택) ─────────────────────────────────

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
                    "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                })
    except Exception as e:
        print(f"[Naver] 실패: {e}")
    print(f"[Naver] {len(results)}개 수집")
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
        # 카테고리별 최대 4개, 해외이슈(overseas)는 최대 5개 허용
        limit = 5 if item["type"] == "overseas" else 4
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
    all_items.extend(collect_reddit())
    all_items.extend(collect_rss())
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

    print(f"\n✅ {len(output)}개 저장 완료 → {OUTPUT}")
    from collections import Counter
    type_dist = Counter(item["type"] for item in output)
    src_dist  = Counter(item["source"] for item in output)
    print(f"  카테고리: {dict(type_dist)}")
    print(f"  소스:     {dict(src_dist)}")


if __name__ == "__main__":
    main()

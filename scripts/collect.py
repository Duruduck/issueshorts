"""
scripts/collect.py
국내외 소스에서 트렌딩 이슈를 수집해 public/topics.json 생성

선발 원칙: 카테고리별 TOP 5 보장 (빈 카테고리 방지)
"""

import os
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

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

CATEGORIES = ["kpop", "social", "culture", "overseas", "beauty", "living", "season"]

# ── 카테고리 자동 분류 ────────────────────────────────────────

CATEGORY_RULES = {
    "kpop":    ["bts","blackpink","aespa","newjeans","ive","stray kids","seventeen",
                "twice","exo","nct","kpop","k-pop","아이돌","케이팝","컴백","팬덤",
                "뮤비","음반","데뷔","걸그룹","보이그룹","콘서트","팬미팅","월드투어",
                "melon","gaon","hanteo","빌보드","그래미","엠카","인기가요"],
    "social":  ["탈북","북한","사건","사고","논란","화제","유튜버","실화","인물",
                "검찰","경찰","정치","연예인","배우","가수","스캔들","논란","고소",
                "결혼","이혼","열애","열정","폭로","사망","부고"],
    "culture": ["한식","요리","레시피","맛집","음식","먹방","food","recipe","kimchi",
                "bibimbap","ramen","tteokbokki","bulgogi","k-food","mukbang",
                "식당","쉐프","맛집","미슐랭","스트리트푸드"],
    "beauty":  ["뷰티","스킨케어","화장품","선크림","세럼","립","쿠션","파운데이션",
                "마스크팩","토너","에센스","클렌저","비비크림","틴트","글로우",
                "beauty","skincare","makeup","sunscreen","serum","k-beauty",
                "올리브영","화해","아이오페","라네즈","설화수","이니스프리"],
    "living":  ["다이소","주방","청소","생활용품","정리","가전","핫딜","할인",
                "가성비","추천","구매","리뷰","언박싱","직구","쿠팡","11번가",
                "kitchen","home","gadget","deal","amazon","product"],
    "season":  ["여름","겨울","봄","가을","시즌","필수템","품절","신상","출시",
                "여행","휴가","피서","캠핑","페스티벌","summer","winter","spring",
                "fall","seasonal","무더위","장마","태풍","한파","황사"],
}

def classify(text: str) -> str:
    t = text.lower()
    for cat, kws in CATEGORY_RULES.items():
        if any(kw in t for kw in kws):
            return cat
    return None

def rank_score(rank: int, total: int) -> int:
    """순위 기반 점수 100→50 (소스 간 공평 비교)"""
    return max(50, 100 - int((rank - 1) / max(total - 1, 1) * 50))

def format_ago(dt: datetime) -> str:
    diff = datetime.now() - dt
    mins = int(diff.total_seconds() / 60)
    if mins < 60:
        return f"{mins}분 전"
    hours = mins // 60
    return f"{hours}시간 전" if hours < 24 else f"{hours // 24}일 전"

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")

def parse_rss(feeds: list[dict], limit: int = 15) -> list[dict]:
    """공통 RSS 파싱 함수"""
    if not FEED_OK:
        return []
    results = []
    for f in feeds:
        try:
            entries = [e for e in feedparser.parse(f["url"]).entries
                       if e.get("title","").strip()][:limit]
            for rank, e in enumerate(entries, 1):
                title = e["title"].strip()
                results.append({
                    "type":   classify(title) or f["type"],
                    "title":  title,
                    "source": f["source"],
                    "from":   f["name"],
                    "url":    e.get("link",""),
                    "score":  rank_score(rank, len(entries)),
                    "collected_at": now_str(),
                })
            print(f"  [{f['name']}] {len(entries)}개")
            time.sleep(0.3)
        except Exception as ex:
            print(f"  [{f['name']}] 실패: {ex}")
    return results


# ── 1. K-pop/연예 전용 ────────────────────────────────────────

KPOP_RSS = [
    {"name":"연합뉴스/연예",    "url":"https://www.yna.co.kr/rss/entertainment.xml",
     "source":"국내", "type":"kpop"},
    {"name":"마이데일리/연예",   "url":"https://www.mydaily.co.kr/rss/allnews.xml",
     "source":"국내", "type":"kpop"},
    {"name":"스포츠경향/연예",   "url":"https://sports.khan.co.kr/rss/entertainments.xml",
     "source":"국내", "type":"kpop"},
]

# ── 2. 사회/인물 전용 ─────────────────────────────────────────

SOCIAL_RSS = [
    {"name":"연합뉴스/사회",   "url":"https://www.yna.co.kr/rss/society.xml",
     "source":"국내", "type":"social"},
    {"name":"연합뉴스/정치",   "url":"https://www.yna.co.kr/rss/politics.xml",
     "source":"국내", "type":"social"},
]

# ── 3. 한식/문화 전용 ─────────────────────────────────────────

CULTURE_RSS = [
    {"name":"연합뉴스/생활",   "url":"https://www.yna.co.kr/rss/lifestyle.xml",
     "source":"국내", "type":"culture"},
    {"name":"연합뉴스/문화",   "url":"https://www.yna.co.kr/rss/culture.xml",
     "source":"국내", "type":"culture"},
]

# ── 4. 뷰티/패션 전용 ─────────────────────────────────────────

BEAUTY_RSS = [
    {"name":"연합뉴스/패션뷰티", "url":"https://www.yna.co.kr/rss/fashion-beauty.xml",
     "source":"국내", "type":"beauty"},
    {"name":"헬스조선",          "url":"https://health.chosun.com/rss/contents.xml",
     "source":"국내", "type":"beauty"},
]

# ── 5. 생활용품/주방 전용 ─────────────────────────────────────

LIVING_RSS = [
    {"name":"에펨코리아/핫딜",  "url":"https://www.fmkorea.com/index.php?mid=hotdeal&act=rss",
     "source":"국내", "type":"living"},
    {"name":"에펨코리아/가성비", "url":"https://www.fmkorea.com/index.php?mid=frugal&act=rss",
     "source":"국내", "type":"living"},
    {"name":"루리웹/핫딜",      "url":"https://bbs.ruliweb.com/news/board/1020?type=rss",
     "source":"국내", "type":"living"},
    {"name":"클리앙/알뜰구매",  "url":"https://www.clien.net/service/board/jiboard?rss=true",
     "source":"국내", "type":"living"},
]

# ── 6. 시즌아이템 전용 ────────────────────────────────────────

SEASON_RSS = [
    {"name":"연합뉴스/경제",   "url":"https://www.yna.co.kr/rss/economy.xml",
     "source":"국내", "type":"season"},
]

# ── 7. 해외 이슈 ──────────────────────────────────────────────

def collect_google_trends() -> list[dict]:
    if not FEED_OK:
        return []
    results = []
    try:
        feed = feedparser.parse(
            "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US"
        )
        entries = [e for e in feed.entries if e.get("title","").strip()][:15]
        for rank, e in enumerate(entries, 1):
            title = e["title"].strip()
            results.append({
                "type":   classify(title) or "overseas",
                "title":  title,
                "source": "해외",
                "from":   "Google Trends (US)",
                "url":    e.get("link",""),
                "score":  rank_score(rank, len(entries)),
                "collected_at": now_str(),
            })
        print(f"[Google Trends] {len(results)}개")
    except Exception as e:
        print(f"[Google Trends] 실패: {e}")
    return results

def collect_hackernews(limit: int = 15) -> list[dict]:
    if not REQ_OK:
        return []
    results = []
    try:
        ids = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10
        ).json()[:limit]
        for rank, sid in enumerate(ids, 1):
            try:
                item = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=5
                ).json()
                title = item.get("title","").strip()
                if not title:
                    continue
                results.append({
                    "type":   classify(title) or "overseas",
                    "title":  title,
                    "source": "해외",
                    "from":   "Hacker News",
                    "url":    item.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                    "score":  rank_score(rank, limit),
                    "collected_at": now_str(),
                })
            except Exception:
                continue
        print(f"[HackerNews] {len(results)}개")
    except Exception as e:
        print(f"[HackerNews] 실패: {e}")
    return results

# ── 8. 네이버 DataLab (선택) ─────────────────────────────────

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
            headers={"X-Naver-Client-Id":cid,"X-Naver-Client-Secret":cs,
                     "Content-Type":"application/json"},
            json={
                "startDate": (today - timedelta(days=7)).strftime("%Y-%m-%d"),
                "endDate":   today.strftime("%Y-%m-%d"),
                "timeUnit":  "date",
                "category":  [{"name":c["name"],"param":[{"name":c["name"],
                               "categoryId":c["categoryId"]}]} for c in NAVER_CATS],
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


# ── 카테고리별 TOP 5 선발 ────────────────────────────────────

def select_per_category(items: list[dict], top_n: int = 5) -> list[dict]:
    """
    각 카테고리에서 점수 상위 top_n개 선발.
    빈 카테고리 방지 — 수집 부족 시 overseas/social에서 재분류해 채움.
    """
    # 카테고리별 그룹화
    by_cat: dict[str, list] = defaultdict(list)
    for item in sorted(items, key=lambda x: x["score"], reverse=True):
        by_cat[item["type"]].append(item)

    # 카테고리별 TOP N 선발
    result = []
    for cat in CATEGORIES:
        result.extend(by_cat[cat][:top_n])

    return result


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

    print("\n[K-pop/연예] 수집...")
    all_items.extend(parse_rss(KPOP_RSS))

    print("\n[사회/인물] 수집...")
    all_items.extend(parse_rss(SOCIAL_RSS))

    print("\n[한식/문화] 수집...")
    all_items.extend(parse_rss(CULTURE_RSS))

    print("\n[뷰티/패션] 수집...")
    all_items.extend(parse_rss(BEAUTY_RSS))

    print("\n[생활용품/주방] 수집...")
    all_items.extend(parse_rss(LIVING_RSS))

    print("\n[시즌아이템] 수집...")
    all_items.extend(parse_rss(SEASON_RSS))

    print("\n[해외 이슈] Google Trends...")
    all_items.extend(collect_google_trends())

    print("\n[해외 이슈] Hacker News...")
    all_items.extend(collect_hackernews(limit=15))

    print("\n[국내 선택] 네이버 DataLab...")
    all_items.extend(collect_naver())

    print(f"\n총 {len(all_items)}개 수집")

    if not all_items:
        print("수집 결과 없음")
        OUTPUT.write_text("[]", encoding="utf-8")
        return

    # 카테고리별 TOP 5 선발
    top    = select_per_category(all_items, top_n=5)
    output = format_output(top)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    from collections import Counter
    type_dist = Counter(item["type"]   for item in output)
    src_dist  = Counter(item["source"] for item in output)
    print(f"\n✅ 총 {len(output)}개 저장")
    for cat in CATEGORIES:
        cnt = type_dist.get(cat, 0)
        bar = "█" * cnt + "░" * (5 - cnt)
        print(f"  {cat:10} {bar} {cnt}/5")
    print(f"\n  국내: {src_dist.get('국내',0)}개 | 해외: {src_dist.get('해외',0)}개")


if __name__ == "__main__":
    main()

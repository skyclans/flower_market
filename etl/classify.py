# -*- coding: utf-8 -*-
"""
품목명 → 부류(절화/난/관엽) 분류기.

aT 일자별 경매 Excel에는 부류 컬럼이 없다(품목명·품종명·등급·속수량·최저/최고/평균단가만).
PRD의 ItemMaster(화훼 품목 마스터 = 도메인 사전)를 구축하기 위한 결정적(deterministic) 분류기.

분류 원리
---------
경매 운영 캘린더만으로는 부류를 가를 수 없다: 절화(월~토)는 난(월·목)·관엽(화·금)과
요일이 겹치기 때문이다. 따라서 **품목명 키워드 사전**이 유일하게 신뢰할 수 있는 신호다.

  - 난/관엽: 큐레이션된 키워드 부분일치로 분류 (classify_method = 'keyword')
  - 그 외: 절화로 분류 (classify_method = 'default')

절화는 품목 종류·거래량 모두 압도적 다수이므로 기본값으로 타당하다.
'default'로 분류된 품목 중 분화일 가능성이 있는 것은 운영자(도메인 전문가)가
주기적으로 감수해 키워드 사전에 추가하는 방식으로 정밀도를 높인다.
classify_method 컬럼이 곧 신뢰 신호이며, 본 사전은 '시드'다 — 완성형이 아니다.
"""

# 난(蘭) — 부분 문자열 매칭
ORCHID_KEYWORDS = [
    "동양란", "심비", "호접", "서양란", "덴파레", "덴드로", "온시디움", "온시듐",
    "카틀레야", "카틀레아", "풍란", "석곡", "보세", "한란", "춘란", "만천홍",
    "소심", "콜만", "팔레놉", "반다", "셀로지네", "리카스테", "파피오",
    "양란", "동양심", "서양심", "나비난", "독구리난", "사철란", "새우란",
]

# 관엽(觀葉)·분화(盆花) — 분(盆) 단위로 거래되는 관상식물 전반
FOLIAGE_KEYWORDS = [
    # 대표 관엽
    "관엽", "고무나무", "극락조", "고사리", "산세", "스파티", "스파트필름",
    "스킨답", "테이블야자", "아레카", "행운목", "드라세나", "디펜바", "칼라데아",
    "칼라디움", "몬스테라", "아이비", "박쥐란", "여인초", "율마", "아디안텀",
    "필로덴드론", "싱고니움", "신고니움", "셀렘", "벤자민", "떡갈", "벵갈",
    "수채화고무", "광나무", "여정목", "스투키", "금전수", "홍콩야자", "파키라",
    "아글라오", "마란타", "페페", "양치", "콤팩타", "맛상게아나", "워네키",
    "송오브인디아", "마지나타", "드라코", "산데리아", "콩고", "인삼펜다",
    "관음죽", "죽백나무", "측백", "화백", "은행목", "황금죽", "팔손이",
    "푸미라", "필레아", "폴리샤스", "아라리아", "트리쳐스", "아나나스",
    "틸란데시아", "수경식물", "수경", "박쥐",
    # 분화(꽃이 피는 화분) — 분 단위 거래
    "군자란", "글록시니아", "시클라멘", "제라늄", "페라고늄", "페라고니움",
    "칼란코에", "칼랑코에", "만데빌라", "부겐베리아", "부겐빌레아", "히비스커스",
    "후쿠샤", "후크시아", "익소라", "크로산데라", "아펠란트라", "아브틸론",
    "샤피니아", "밀리온벨", "비덴스", "바코바", "로벨리아", "아메리칸블루",
    "썬로즈", "포테리카", "다이콘드라", "유리호프스", "오스테우스", "마가렛트",
    "제스민", "쟈스민", "야스민", "야리향", "야향화",
    # 다육·선인장
    "선인장", "다육", "염자", "세덤", "알로에", "게발선인장",
    "불로초", "석화", "콩짜개", "거미바위솔",
    # 식충·기타 분
    "식충식물", "벌레잡이", "네펜데스",
    # 관목·정원수(분 거래)
    "커피나무", "수련목", "보리수", "천냥금", "산호수", "백량금", "마삭줄",
    "홍가시", "피어리스", "호주매화", "무궁화", "라일락",
    "분갈이", "완제품",
]


def classify_item(item_name: str) -> tuple[str, str]:
    """품목명 → (부류, 신뢰도). 신뢰도: 'keyword' | 'default'."""
    name = (item_name or "").strip()
    for kw in ORCHID_KEYWORDS:
        if kw in name:
            return "난", "keyword"
    for kw in FOLIAGE_KEYWORDS:
        if kw in name:
            return "관엽", "keyword"
    return "절화", "default"


def build_item_master(records: list[dict]) -> list[dict]:
    """수집 레코드 → ItemMaster 행 목록."""
    from collections import defaultdict
    import datetime as dt

    agg = defaultdict(lambda: {
        "varieties": set(), "grades": set(), "weekdays": set(),
        "dates": set(), "volume": 0,
    })
    for r in records:
        a = agg[r["item_name"]]
        a["varieties"].add(r["variety_name"])
        a["grades"].add(r["grade"])
        a["dates"].add(r["auction_date"])
        a["weekdays"].add(dt.date.fromisoformat(r["auction_date"]).weekday())
        a["volume"] += r["trade_volume"] or 0

    wd_map = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}
    rows = []
    for item, a in sorted(agg.items()):
        category, method = classify_item(item)
        rows.append({
            "item_name": item,
            "category": category,
            "classify_method": method,   # keyword=확정, default=절화 기본값(감수 권장)
            "observed_weekdays": "".join(wd_map[w] for w in sorted(a["weekdays"])),
            "variety_count": len(a["varieties"]),
            "grade_set": ",".join(sorted(a["grades"])),
            "obs_dates": len(a["dates"]),
            "total_volume": a["volume"],
        })
    return rows

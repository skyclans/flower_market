# Phase 1 — 라이브 데이터 + 비교 슬라이스 (스캐폴드)

Phase 0 가 "데이터를 구할 수 있다"를 증명했다면, Phase 1 의 목표는 데이터를
**항상 최신·쿼리 가능한 상태**로 만들고 그 위에 **최소 비교 화면**을 올리는 것이다.
백엔드는 그 화면을 받치는 딱 최소한만 만든다.

## 구성

```
etl/
  sources/
    base.py            AuctionRecord + AuctionSource (소스 공통 계약)
    excel_source.py    flower.at.or.kr (Phase 0 검증, 화훼 지원, 기본 소스)
    openapi_source.py  data.go.kr 15141808 (운영 후보, 건별→집계)
    __init__.py        get_source(SOURCE) 팩토리
  db.py                auction_price upsert (멱등)
  run_daily.py         일배치 진입점 (소스 무관)
api/
  main.py              FastAPI: today / trend / compare / items / health
  queries.py           읽기 SQL
  db.py                커넥션 풀
.github/workflows/
  daily.yml            매일 20:00 KST 배치 cron
```

## 핵심 설계: 소스 교체 가능성

엑셀 소스와 Open API 소스는 **같은 인터페이스**(`AuctionSource`)를 구현하고
**같은 타입**(`AuctionRecord`)을 내놓는다. 그래서 적재·배치·API 계층은 소스가
무엇인지 모른다. 환경변수 `SOURCE=excel|openapi` 하나로 갈아끼운다.

- **지금**: `SOURCE=excel` — Phase 0 에서 검증됐고 화훼를 확실히 싣는다.
- **운영 후보**: `SOURCE=openapi` — 공식·실시간·안정적. 단, 두 가지를 확인해야:
  1. 이 API가 화훼(양재)를 싣는가? (농수산물 32개 시장 중심)
  2. `whsl_mrkt_code` ↔ 우리 표준코드 매핑 (15141818 표준코드 API로 조회)

  확인되면 env 만 바꿔 무중단 전환. 안 되면 엑셀 소스 영구 유지.

## 엑셀 vs API 데이터 형태 차이 (중요)

- 엑셀: (품목·품종·등급)별로 **이미 집계된** 최저/최고/평균/속수량.
- API: **거래 건별** 행(`prce`, `unit_qyt`). → `openapi_source` 가
  (일자·시장·품목·품종·등급)으로 그룹핑해 min/max/avg(수량가중)/volume 을 집계.

두 경로 모두 동일한 `auction_price` 행으로 수렴한다.

## 적재 멱등성

`auction_price` 의 `UNIQUE(auction_date, market_code, item_name, variety_name, grade)`
위에서 `ON CONFLICT DO UPDATE`. 배치를 몇 번 돌려도 중복이 안 쌓이고 최신값으로
갱신된다. 정합성 위반 행(avg>max·음수·결측)은 적재 전 `is_valid()` 로 걸러
스키마 CHECK 충돌을 막는다.

## 로컬 실행

```bash
pip install -r requirements.txt
cp .env.example .env            # DATABASE_URL 채우기

# 1) DB 준비
psql "$DATABASE_URL" < schema/auction_price.sql

# 2) 최신 시세 적재 (엑셀 소스, 양재)
SOURCE=excel MARKETS=0000000001 LAST_N=1 \
  DATABASE_URL="$DATABASE_URL" python etl/run_daily.py

# 3) API 기동
DATABASE_URL="$DATABASE_URL" uvicorn api.main:app --reload
#   http://localhost:8000/docs
```

## API 빠른 점검

```bash
curl "localhost:8000/items?market=0000000001"
curl "localhost:8000/prices/today?market=0000000001"
curl "localhost:8000/items/장미/trend?market=0000000001&days=30"
curl -X POST localhost:8000/compare \
  -H 'Content-Type: application/json' \
  -d '{"item_name":"장미","my_price":6000,"market":"0000000001"}'
```

`/compare` 응답의 `my_price_vs_avg_pct` 가 양수면 경매 평균보다 비싸게 매입,
음수면 싸게 매입. 본경매/온라인 각각에 대해 따로 보여준다 — 이게 제품의 핵심 한 줄.

## 다음

- 화원 매입가 입력 UI(즐겨찾기 품목 10~20개) + 오늘 카드(본경매 vs 온라인 vs 전주)
- 화원 3~5명 실사용 테스트 → 수요 검증 (North Star = WATU)
- 주간 요약 알림 훅 (리텐션)

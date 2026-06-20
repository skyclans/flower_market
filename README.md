# flower_market

꽃장부(Flower Ledger) MVP — **Phase 0 데이터 파이프라인 PoC**

오프라인 화원을 위한 버티컬 SaaS '꽃장부'의 가장 치명적인 리스크(R1)인 **양재 화훼공판장 경매가 데이터 파이프라인**을 실제로 검증한 결과물입니다. PRD가 정의한 Phase 0 Exit Criteria(`ETL 성공률 ≥ 90%`)를 **양재 25/25일 = 100%** 로 통과했습니다.

---

## 무엇이 검증되었나 (de-risked)

| 항목 | PRD 가정 | 실측 결과 |
|---|---|---|
| 데이터 소스 존재 | 양재 경매가를 안정적으로 수집 가능한가? | ✅ 공식 엑셀 다운로드 엔드포인트 확보 |
| ETL 성공률 | ≥ 90% (Exit Criteria) | ✅ **100%** (양재 25/25일) |
| 스키마 매핑 | `AuctionPrice` 엔티티(§9.3)로 정규화 가능한가? | ✅ 엑셀 컬럼 1:1 매핑 |
| 경매 캘린더 | 절화 월~토 / 난 월·목 / 관엽 화·금 | ✅ 일별 물량 분포가 정확히 일치 |
| 본경매 vs 온라인 가격차 | 도메인 모델의 핵심 변수 | ✅ 장미 -40%, 거베라 -61% 관측 |

요약: **"데이터를 못 구할 리스크"는 사라졌다.** 양재 단일 시장은 물론, 전국 7개 공판장까지 같은 방식으로 수집됨을 확인.

---

## 수집된 데이터 (`data/`)

- `auction_prices.csv` — **20,551 레코드** (utf-8-sig). 7개 시장 × 2026-05-23 ~ 06-20 (양재 25일치 + 타 시장 최신 스냅샷)
  - 부류: 절화 17,245 / 난 1,562 / 관엽 1,744
  - 무결성: avg>max 위반 0건, 음수가 0건, 결측 0건 (min>avg 17행 ≈ 0.08%만 docs에 플래그)
- `item_master.csv` — **404개 품목** 도메인 사전 시드 (품목→부류 분류 + 관측 메타)
- `collection_report.json` — ETL 실행 로그 + 성공률 + Exit Criteria 충족 여부
- `data/raw/*.xls` — 원본 엑셀 31개 (`{cmpCd}_{date}.xls`). 네트워크 없이 재처리 가능한 안전망

상위 물량 품목: 호접란 290,839속 / 장미 277,508속 / 거베라 142,619속.

---

## 데이터 소스 (역설계 결과)

신규 사이트: `flower.at.or.kr` (구 PRD의 `aucPrice.do` URL은 폐기됨)

| 엔드포인트 | 용도 |
|---|---|
| `POST /main/getSaleDate.json` | 시장별 경매 개장일 목록 |
| `GET /excel/excelDownLoad.do` | **일자별 경매동향 전체 엑셀** (권위 있는 완전 소스) |

세션 쿠키(KHANUSER/JSESSIONID)와 Referer 헤더 필요. 상세는 `etl/codes.py`, `docs/data_dictionary.md` 참조.

> **프로덕션 권장 경로 (Stage 2):** 공공데이터포털 Open API `15141808`
> (전국 공영도매시장 실시간 경매정보) — 무료, 실시간, REST(JSON/XML), 이용제한 없음.
> serviceKey만 발급받으면 엑셀 스크래핑을 대체 가능. 장기적으로 이 API로 이관 권장.

---

## 실행 방법

```bash
pip install -r requirements.txt

# 1) 라이브 수집 (양재 최근 10 영업일)
python etl/collect_auction.py --market 0000000001 --last 10

# 전체 시장
python etl/collect_auction.py --market all --last 5

# 기간 지정
python etl/collect_auction.py --market 0000000001 --from 2026-06-01 --to 2026-06-20

# 2) 네트워크 없이 원본 엑셀만 재처리 (Stage 0 안전망)
python etl/rebuild_from_raw.py
```

산출물은 `data/auction_prices.csv`, `data/item_master.csv`, `data/collection_report.json`.

---

## DB 적재

```bash
psql -d flower < schema/auction_price.sql   # 스키마 + 7개 시장 시드 + \copy 예시
```

`schema/auction_price.sql` 는 PRD §9.3 `AuctionPrice` / `ItemMaster` 를 Postgres 15 DDL로 구현 (ENUM, 핫패스 인덱스 포함).

---

## 디렉터리 구조

```
flower_market/
├── etl/
│   ├── codes.py             # 시장/부류 코드, 엔드포인트, 경매 캘린더
│   ├── classify.py          # 품목→부류 결정론적 분류기
│   ├── collect_auction.py   # 라이브 수집기 (세션+재시도)
│   ├── rebuild_from_raw.py  # 원본 엑셀 재처리 (오프라인)
│   ├── db.py                # auction_price 멱등 upsert (Phase 1)
│   ├── run_daily.py         # 일배치 진입점, 소스 무관 (Phase 1)
│   └── sources/             # 소스 추상화 (Phase 1)
│       ├── base.py          #   AuctionRecord + AuctionSource 계약
│       ├── excel_source.py  #   flower.at.or.kr (검증된 기본 소스)
│       ├── openapi_source.py#   data.go.kr 15141808 (운영 후보)
│       └── __init__.py      #   get_source(SOURCE) 팩토리
├── api/                     # FastAPI 비교 슬라이스 (Phase 1)
│   ├── main.py              # today / trend / compare / items / health
│   ├── queries.py           # 읽기 SQL
│   └── db.py                # 커넥션 풀
├── schema/
│   └── auction_price.sql    # Postgres DDL + 시드
├── data/
│   ├── auction_prices.csv   # 정규화된 경매가 (20,551행)
│   ├── item_master.csv      # 품목 사전 (404개)
│   ├── collection_report.json
│   └── raw/*.xls            # 원본 31개
├── docs/
│   ├── data_dictionary.md   # 필드 정의 + 소스 노트 + 한계
│   ├── phase0_findings.md   # Phase 0 PoC 결과 분석
│   └── phase1_architecture.md # Phase 1 구조/운영
├── .github/workflows/daily.yml  # 일배치 cron
├── .env.example
├── requirements.txt
├── CLAUDE.md                # Claude Code 작업용 컨텍스트
└── README.md
```

---

## Phase 1 — 라이브 데이터 + 비교 API (스캐폴드)

정적 CSV를 항상 최신·쿼리 가능한 상태로 만들고 최소 비교 화면을 올리는 단계.
상세는 `docs/phase1_architecture.md`.

```bash
pip install -r requirements.txt
cp .env.example .env                      # DATABASE_URL 채우기
psql "$DATABASE_URL" < schema/auction_price.sql

# 최신 시세 적재 (엑셀 소스 = 검증됨, 기본)
SOURCE=excel MARKETS=0000000001 LAST_N=1 \
  DATABASE_URL="$DATABASE_URL" python etl/run_daily.py

# 비교 API 기동 → http://localhost:8000/docs
DATABASE_URL="$DATABASE_URL" uvicorn api.main:app --reload
```

**소스 교체**: 엑셀 소스와 data.go.kr Open API 소스는 같은 인터페이스라
`SOURCE=excel|openapi` 한 줄로 갈아끼웁니다. OpenAPI 전환 전 (1) 화훼 포함 여부,
(2) `whsl_mrkt_code` 매핑(API 15141818)을 serviceKey로 확인해야 합니다. 미확인 시
엑셀 소스가 영구 폴백입니다.

---

## 한계 / 주의

- `item_master.csv` 의 부류 분류는 **시드**입니다. 키워드 매칭(난 12 + 관엽 104) 외 나머지는 절화 기본값(`classify_method=default`)이며, 도메인 큐레이션이 필요합니다. `classify_method` 컬럼이 신뢰 신호입니다.
- 양재 외 6개 시장은 현재 **최신 1일치 스냅샷**만 수집됨 (히스토리 백필은 동일 스크립트로 가능).
- 엑셀에는 `부류` 컬럼이 없어 품목명 기반으로 추론합니다.

---

## 웹 앱 (web/) — 디자인을 코드로

Figma MVP 디자인을 Vite + React 로 구현했고, FastAPI 를 통해 Neon 의 1년치 데이터를
실시간으로 그린다. 차트 값은 하드코딩이 아니라 백엔드 집계(`/items/{item}/trend`)를
통해 자동으로 채워진다.

**한 번에 실행** (권장): repo 루트 `.env` 에 `DATABASE_URL` 한 줄 넣고:
```bash
./run-local.sh        # 백엔드+프론트 동시 기동, Ctrl+C 로 둘 다 종료
```

수동 실행:
```bash
# 백엔드
export DATABASE_URL='postgresql://...neon.../neondb?sslmode=require'
uvicorn api.main:app --reload          # :8000

# 프론트
cd web && npm install && npm run dev   # :5173
```

자세한 내용은 `web/README.md`.

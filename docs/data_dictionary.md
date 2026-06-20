# 데이터 사전 (Data Dictionary)

꽃장부 Phase 0 시세 데이터셋의 필드 정의·출처·주의사항.

---

## 1. 출처 (Source)

| 항목 | 내용 |
|---|---|
| 1차 출처 | 화훼유통정보시스템 `flower.at.or.kr` — 일자별 경매동향 Excel (`/excel/excelDownLoad.do`) |
| 운영 주체 | 한국농수산식품유통공사 (aT) |
| 수집 방식 | HTTP 세션 + Excel 다운로드 (PRD §9.4 Stage 1). `etl/collect_auction.py` |
| 수집 시점 | 2026-06-20 (KST) |
| 갱신 캘린더 | 절화 월~토 / 난 월·목 / 관엽 화·금 / 일·공휴일 휴장 |

> **운영 전환 권고**: 본 데이터는 PoC·백업용이다. 운영 단계에서는 공공데이터포털
> [전국 공영도매시장 실시간 경매정보 Open API](https://www.data.go.kr/data/15141808/openapi.do)
> (무료·실시간·이용허락 제한 없음, serviceKey 발급 필요)로 이관하는 것이 법적·안정성 면에서 권장된다.
> 이는 PRD §9.4 Stage 2에 해당한다.

---

## 2. `auction_prices.csv` — 정규화 경매시세 (long-format)

| 컬럼 | 타입 | 설명 | 원본 |
|---|---|---|---|
| `auction_date` | DATE | 경매 일자 (YYYY-MM-DD) | saleDate |
| `market_code` | STR | 공판장 코드 (aT cmpCd) | — |
| `market_name` | STR | 공판장명 | codes.py |
| `category` | ENUM | 부류: 절화/난/관엽 | classify.py 추론 |
| `item_name` | STR | 품목명 | 품목명 |
| `variety_name` | STR | 품종명 (난·관엽은 규격 인코딩: "화이트(8송이)"=8꽃대, "떡갈5″"=5인치 분) | 품종명 |
| `grade` | STR | 등급 (특/상/보/중 + 세부: 특1, 상2 …) | 등급 |
| `unit` | STR | 거래 단위: 속(절화) / 분(난·관엽) | category 기반 |
| `trade_volume` | INT | 거래 수량 (속 또는 분) | 속수량 |
| `min_price` | INT | 최저 단가 (원) | 최저단가 |
| `max_price` | INT | 최고 단가 (원) | 최고단가 |
| `avg_price` | INT | 평균 단가 (원) ★ 마진 계산 기준 | 평균단가 |
| `auction_type` | ENUM | main(본경매 월·수·금) / online(온라인거래 화·목·토) | 요일 기반 |
| `source` | STR | 출처 식별자 | — |
| `fetched_at` | TS | 수집 시각 | — |

**중복 제거 키**: `(auction_date, market_code, item_name, variety_name, grade)`

---

## 3. `item_master.csv` — 화훼 품목 마스터 (도메인 사전)

| 컬럼 | 설명 |
|---|---|
| `item_name` | 품목명 (PK) |
| `category` | 부류 (절화/난/관엽) |
| `classify_method` | **`keyword`**=키워드 사전 확정 / **`default`**=절화 기본값(감수 권장) |
| `observed_weekdays` | 데이터에서 관측된 경매 요일 (예: "월수금") |
| `variety_count` | 관측 품종 수 |
| `grade_set` | 관측 등급 집합 |
| `obs_dates` | 관측 일수 |
| `total_volume` | 누적 거래량 |

---

## 4. ⚠️ 부류 분류의 한계 (중요)

aT Excel에는 **부류(절화/난/관엽) 컬럼이 없다.** 또한 경매 운영 요일도 부류를 가르지
못한다 — 절화(월~토)가 난(월·목)·관엽(화·금)과 요일이 겹치기 때문이다.

따라서 `category`는 **품목명 키워드 사전**(`etl/classify.py`)으로 추론한 **결정적 시드**다:

- **난·관엽** (`classify_method=keyword`): 큐레이션 키워드 부분일치. 비교적 정밀.
- **그 외** (`classify_method=default`): 절화로 분류. 절화가 품목·물량 모두 압도적이라 타당하나,
  키워드 사전에 없는 분화 품목이 절화로 잘못 분류될 수 있다.

**권장 운영**: 도메인 전문가가 `classify_method=default` 품목을 주기적으로 감수하여
`ORCHID_KEYWORDS`/`FOLIAGE_KEYWORDS`에 추가 → `rebuild_from_raw.py`로 재생성.
이 사전은 **완성형이 아니라 시드**이며, 거래량 축적과 함께 정밀화하는 자산이다.

---

## 5. 데이터 품질 노트

- **가격 역전**: 원본에 `최저단가 > 평균단가`인 행이 극소수(약 0.08%) 존재. 적재 스키마는
  `avg ≤ max`만 강제하고, `min > avg` 행은 적재 전 정제하거나 플래그 처리 권장.
- **관측 기간**: 양재 4주(2026-05-23~06-20, 25 거래일) + 타 공판장 6곳 최신 1일 스냅샷.
- 본 데이터셋은 운영 DB가 아니라 **Phase 0 검증용 샘플**이다.

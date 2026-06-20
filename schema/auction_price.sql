-- =============================================================================
-- 꽃장부 — 시세 데이터 스키마 (PRD §9.3 Core Entities 중 시세 파이프라인 부분)
-- PostgreSQL 15+
--
-- 본 파일은 양재(aT) 화훼 경매시세 적재에 필요한 테이블만 정의한다.
-- (User/Transaction/TransactionLine/OcrJob/Watchlist 등 앱 측 엔티티는 별도)
-- data/auction_prices.csv 및 data/item_master.csv 를 그대로 COPY 적재할 수 있도록 설계.
-- =============================================================================

-- 부류 / 단위 / 경매유형 ENUM
DO $$ BEGIN
    CREATE TYPE flower_category AS ENUM ('절화', '난', '관엽');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE auction_kind AS ENUM ('main', 'online');  -- 본경매(월·수·금) / 온라인거래(화·목·토)
EXCEPTION WHEN duplicate_object THEN NULL; END $$;


-- -----------------------------------------------------------------------------
-- 공판장 마스터
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS market (
    market_code   VARCHAR(10) PRIMARY KEY,     -- aT cmpCd (예: 0000000001 = 양재)
    market_name   TEXT        NOT NULL,
    region        TEXT,
    is_primary    BOOLEAN     NOT NULL DEFAULT FALSE
);


-- -----------------------------------------------------------------------------
-- 화훼 품목 마스터 (도메인 사전) — PRD ItemMaster
--   etl/classify.py 가 생성. category 는 키워드 분류 시드(운영자 감수로 정밀화).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS item_master (
    item_name        TEXT             PRIMARY KEY,
    category         flower_category  NOT NULL,
    classify_method  VARCHAR(10)      NOT NULL DEFAULT 'default',  -- keyword | default
    default_unit     VARCHAR(4)       NOT NULL DEFAULT '속',        -- 절화=속, 난·관엽=분
    common_aliases   TEXT[]           DEFAULT '{}',                -- OCR fuzzy match 용
    typical_grades   TEXT[]           DEFAULT '{}',
    updated_at       TIMESTAMPTZ      NOT NULL DEFAULT now()
);


-- -----------------------------------------------------------------------------
-- 경매시세 (일별 적재) — PRD AuctionPrice
--   원본: flower.at.or.kr 일자별 경매동향 Excel → etl/collect_auction.py 정규화
--   갱신 주기: 절화 D+0, 분화(난·관엽) D+1 / 휴장일(일·공휴일) 제외
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auction_price (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    auction_date  DATE             NOT NULL,
    market_code   VARCHAR(10)      NOT NULL REFERENCES market(market_code),
    category      flower_category  NOT NULL,
    item_name     TEXT             NOT NULL,
    variety_name  TEXT             NOT NULL,
    grade         TEXT             NOT NULL,                 -- 특/상/보/중 + 세부(특1, 상2 …)
    unit          VARCHAR(4)       NOT NULL,                 -- 속 | 분
    trade_volume  INTEGER          NOT NULL CHECK (trade_volume >= 0),
    min_price     INTEGER          NOT NULL CHECK (min_price >= 0),
    max_price     INTEGER          NOT NULL CHECK (max_price >= 0),
    avg_price     INTEGER          NOT NULL CHECK (avg_price >= 0),
    auction_type  auction_kind     NOT NULL,                -- main | online
    source        TEXT             NOT NULL DEFAULT 'flower.at.or.kr/excelDownLoad',
    fetched_at    TIMESTAMPTZ      NOT NULL DEFAULT now(),

    -- 동일 일자·공판장·품목·품종·등급은 1건 (PRD UNIQUE 제약 변형)
    CONSTRAINT uq_auction UNIQUE (auction_date, market_code, item_name, variety_name, grade),
    -- 가격 정합성: 최저 ≤ 평균 ≤ 최고 (원본 데이터에 드물게 위반 존재 → 적재 시 점검)
    CONSTRAINT ck_price_order CHECK (avg_price <= max_price)
);

-- 조회 패턴별 인덱스
--   1) 거래 입력 시 "오늘 이 품목 평균가" 핫패스
CREATE INDEX IF NOT EXISTS ix_auction_lookup
    ON auction_price (market_code, item_name, auction_date DESC);
--   2) 시세 트렌드 차트 (품목별 기간 추이)
CREATE INDEX IF NOT EXISTS ix_auction_trend
    ON auction_price (item_name, auction_date);
--   3) 부류 탭 필터
CREATE INDEX IF NOT EXISTS ix_auction_category
    ON auction_price (category, auction_date DESC);


-- -----------------------------------------------------------------------------
-- 시드: 공판장 7곳
-- -----------------------------------------------------------------------------
INSERT INTO market (market_code, market_name, region, is_primary) VALUES
    ('0000000001', 'aT화훼(양재)',   '서울 서초', TRUE),
    ('1508500020', '부산화훼(엄궁)', '부산',     FALSE),
    ('6068207466', '부경화훼(강동)', '부산',     FALSE),
    ('4108212335', '광주원예(풍암)', '광주',     FALSE),
    ('3848200087', '한국화훼(음성)', '충북 음성', FALSE),
    ('7368200686', '한국화훼(고양)', '경기 고양', FALSE),
    ('6158209828', '영남화훼(김해)', '경남 김해', FALSE)
ON CONFLICT (market_code) DO NOTHING;


-- =============================================================================
-- 적재 예시 (psql):
--   \copy item_master(item_name,category,classify_method,observed_weekdays,
--         variety_count,grade_set,obs_dates,total_volume)
--         FROM 'data/item_master.csv' CSV HEADER;
--   -- ※ item_master.csv 는 분석 컬럼 포함. 운영 적재 시 필요한 컬럼만 매핑하거나
--   --    스테이징 테이블에 적재 후 item_master 로 UPSERT 권장.
--
--   \copy auction_price(auction_date,market_code,category,item_name,variety_name,
--         grade,unit,trade_volume,min_price,max_price,avg_price,auction_type,
--         source,fetched_at)
--         FROM PROGRAM 'tail -n +2 data/auction_prices.csv' CSV;
--   -- ※ market_name 컬럼은 스킵(스테이징 경유). 위 ck_price_order 위반 행은 사전 정제.
-- =============================================================================

-- 꽃장부 장부(거래 기록) 스키마 — PRD §9.3 Transaction/TransactionLine 구현
-- auction_price 스키마(auction_price.sql) 적용 후 실행.

DO $$ BEGIN CREATE TYPE tx_type AS ENUM ('purchase','sale');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS app_transaction (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id TEXT NOT NULL DEFAULT 'demo',
  tx_type tx_type NOT NULL,
  occurred_on DATE NOT NULL,
  market_code VARCHAR(10),
  total_amount BIGINT NOT NULL DEFAULT 0,
  payment_method TEXT,
  memo TEXT,
  receipt_image_url TEXT,                 -- OCR 영수증 (P0, 추후)
  source TEXT NOT NULL DEFAULT 'manual',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app_transaction_line (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  transaction_id BIGINT NOT NULL REFERENCES app_transaction(id) ON DELETE CASCADE,
  item_name TEXT NOT NULL,
  category flower_category,
  grade TEXT,
  unit VARCHAR(4),                        -- 속 | 분 | 단 | 본
  quantity INTEGER NOT NULL DEFAULT 1,
  unit_price INTEGER NOT NULL DEFAULT 0,
  line_total BIGINT NOT NULL DEFAULT 0,
  auction_avg_at_purchase INTEGER,        -- 매입 시점 본경매 시세 스냅샷
  margin_pct NUMERIC                       -- (unit_price - auction_avg)/auction_avg*100
);

CREATE INDEX IF NOT EXISTS ix_tx_user_date ON app_transaction (user_id, occurred_on DESC);
CREATE INDEX IF NOT EXISTS ix_txline_tx   ON app_transaction_line (transaction_id);

-- 세무 전문가 연결 · 빠른 절세 상담 요청
CREATE TABLE IF NOT EXISTS app_consult_request (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id TEXT NOT NULL DEFAULT 'demo',
  name TEXT NOT NULL,
  phone TEXT NOT NULL,
  biz_type TEXT,                          -- tax_free | general | simplified
  channel TEXT NOT NULL DEFAULT 'phone',  -- phone | kakao
  memo TEXT,
  month_purchase BIGINT NOT NULL DEFAULT 0,  -- 제출 시점 이번 달 매입액
  month_count INTEGER NOT NULL DEFAULT 0,    -- 제출 시점 이번 달 거래 건수
  status TEXT NOT NULL DEFAULT 'new',      -- new | contacted | done
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_consult_status ON app_consult_request (status, created_at DESC);

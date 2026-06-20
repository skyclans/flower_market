# -*- coding: utf-8 -*-
"""
적재 계층 — AuctionRecord 를 Postgres auction_price 테이블에 멱등 upsert.

스키마: schema/auction_price.sql
  UNIQUE (auction_date, market_code, item_name, variety_name, grade)
  → ON CONFLICT DO UPDATE 로 재실행해도 중복 없이 최신값 반영.

연결: 환경변수 DATABASE_URL (예: postgresql://user:pw@host:5432/flower)
"""
from __future__ import annotations

import os
from typing import Iterable, Sequence

import psycopg
from psycopg.rows import dict_row

from base import AuctionRecord


def get_dsn() -> str:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL 환경변수가 필요합니다.")
    return dsn


def connect():
    return psycopg.connect(get_dsn(), row_factory=dict_row)


UPSERT_SQL = """
INSERT INTO auction_price
    (auction_date, market_code, category, item_name, variety_name, grade,
     unit, trade_volume, min_price, max_price, avg_price, auction_type, source, fetched_at)
VALUES
    (%(auction_date)s, %(market_code)s, %(category)s, %(item_name)s, %(variety_name)s,
     %(grade)s, %(unit)s, %(trade_volume)s, %(min_price)s, %(max_price)s, %(avg_price)s,
     %(auction_type)s, %(source)s, %(fetched_at)s)
ON CONFLICT (auction_date, market_code, item_name, variety_name, grade)
DO UPDATE SET
    category     = EXCLUDED.category,
    unit         = EXCLUDED.unit,
    trade_volume = EXCLUDED.trade_volume,
    min_price    = EXCLUDED.min_price,
    max_price    = EXCLUDED.max_price,
    avg_price    = EXCLUDED.avg_price,
    auction_type = EXCLUDED.auction_type,
    source       = EXCLUDED.source,
    fetched_at   = EXCLUDED.fetched_at;
"""


def upsert_records(records: Iterable[AuctionRecord], conn=None) -> tuple[int, int]:
    """레코드 적재. (적재건수, 스킵건수) 반환.

    is_valid() 실패 행(avg>max, 음수, 결측)은 적재 전 제외 — 스키마 CHECK 위반 방지.
    """
    own = conn is None
    conn = conn or connect()
    valid, skipped = [], 0
    for r in records:
        if r.is_valid():
            valid.append(r)
        else:
            skipped += 1

    if valid:
        rows = [
            {
                "auction_date": r.auction_date, "market_code": r.market_code,
                "category": r.category, "item_name": r.item_name,
                "variety_name": r.variety_name, "grade": r.grade, "unit": r.unit,
                "trade_volume": r.trade_volume, "min_price": r.min_price,
                "max_price": r.max_price, "avg_price": r.avg_price,
                "auction_type": r.auction_type, "source": r.source,
                "fetched_at": r.fetched_at,
            }
            for r in valid
        ]
        with conn.cursor() as cur:
            cur.executemany(UPSERT_SQL, rows)
        conn.commit()
    if own:
        conn.close()
    return len(valid), skipped


def ensure_markets(market_codes: Sequence[str], names: dict[str, str], conn=None) -> None:
    """auction_price 의 FK(market) 충족용 — 시장 행이 없으면 생성."""
    own = conn is None
    conn = conn or connect()
    with conn.cursor() as cur:
        for code in market_codes:
            cur.execute(
                "INSERT INTO market (market_code, market_name) VALUES (%s, %s) "
                "ON CONFLICT (market_code) DO NOTHING;",
                (code, names.get(code, code)),
            )
    conn.commit()
    if own:
        conn.close()


__all__ = ["connect", "get_dsn", "upsert_records", "ensure_markets"]

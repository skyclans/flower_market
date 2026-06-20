# -*- coding: utf-8 -*-
"""장부(거래 기록) 라우터 — 매입/매출 입력, 거래 목록, 월 리포트, 실시간 마진 견적."""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from db import pool, fetch_all

router = APIRouter()
PRIMARY_MARKET = "0000000001"
USER = "demo"   # 단일 데모 사용자 (멀티유저 인증 전)

LATEST_MAIN = """
SELECT ROUND(SUM(avg_price*trade_volume)::numeric/NULLIF(SUM(trade_volume),0)) AS v
FROM auction_price
WHERE market_code=%(market)s AND item_name=%(item)s AND auction_type='main'
  AND auction_date=(SELECT MAX(auction_date) FROM auction_price
                    WHERE market_code=%(market)s AND item_name=%(item)s AND auction_type='main');
"""

def _latest_main(market: str, item: str):
    rows = fetch_all(LATEST_MAIN, {"market": market, "item": item})
    return int(rows[0]["v"]) if rows and rows[0]["v"] is not None else None

def _margin(price: int, av):
    return None if not av else round((price - av) / av * 100, 1)


@router.get("/quote")
def quote(item: str, unit_price: int = Query(..., ge=0), market: str = Query(PRIMARY_MARKET)):
    """입력 중 실시간 마진 미리보기 — 매입 시점 본경매 시세 대비."""
    av = _latest_main(market, item)
    return {"item": item, "auction_avg": av, "unit_price": unit_price, "margin_pct": _margin(unit_price, av)}


class LineIn(BaseModel):
    item_name: str
    grade: str | None = None
    unit: str | None = None
    category: str | None = None
    quantity: int = Field(1, ge=1)
    unit_price: int = Field(0, ge=0)

class TxIn(BaseModel):
    tx_type: str = Field("purchase", pattern="^(purchase|sale)$")
    occurred_on: str | None = None
    market_code: str | None = PRIMARY_MARKET
    payment_method: str | None = None
    memo: str | None = None
    lines: list[LineIn]

INSERT_TX = """
INSERT INTO app_transaction (user_id, tx_type, occurred_on, market_code, total_amount, payment_method, memo, source)
VALUES (%(user)s, %(tx_type)s, %(occurred_on)s, %(market)s, %(total)s, %(pay)s, %(memo)s, 'manual')
RETURNING id;
"""
INSERT_LINE = """
INSERT INTO app_transaction_line
  (transaction_id, item_name, category, grade, unit, quantity, unit_price, line_total, auction_avg_at_purchase, margin_pct)
VALUES (%(tx)s, %(item)s, %(cat)s, %(grade)s, %(unit)s, %(qty)s, %(price)s, %(total)s, %(av)s, %(margin)s);
"""

@router.post("/transactions")
def create_tx(body: TxIn):
    occurred = body.occurred_on or dt.date.today().isoformat()
    market = body.market_code or PRIMARY_MARKET
    # 마진 스냅샷 먼저 계산 (쓰기 트랜잭션 밖에서)
    enriched = []
    for l in body.lines:
        av = _latest_main(market, l.item_name) if body.tx_type == "purchase" else None
        enriched.append((l, av, _margin(l.unit_price, av)))
    total = sum(l.quantity * l.unit_price for l in body.lines)
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(INSERT_TX, {"user": USER, "tx_type": body.tx_type, "occurred_on": occurred,
                                "market": market, "total": total, "pay": body.payment_method, "memo": body.memo})
        tx_id = cur.fetchone()["id"]
        for l, av, margin in enriched:
            cur.execute(INSERT_LINE, {"tx": tx_id, "item": l.item_name, "cat": l.category, "grade": l.grade,
                                      "unit": l.unit, "qty": l.quantity, "price": l.unit_price,
                                      "total": l.quantity * l.unit_price, "av": av, "margin": margin})
    return {"id": tx_id, "occurred_on": occurred, "total_amount": total, "line_count": len(body.lines)}

LIST_TX = """
SELECT t.id, t.tx_type, t.occurred_on::text AS occurred_on, t.total_amount,
       t.payment_method, t.memo,
       COALESCE(json_agg(json_build_object(
         'item_name', l.item_name, 'grade', l.grade, 'unit', l.unit,
         'quantity', l.quantity, 'unit_price', l.unit_price, 'line_total', l.line_total,
         'auction_avg', l.auction_avg_at_purchase, 'margin_pct', l.margin_pct
       ) ORDER BY l.id) FILTER (WHERE l.id IS NOT NULL), '[]') AS lines
FROM app_transaction t
LEFT JOIN app_transaction_line l ON l.transaction_id=t.id
WHERE t.user_id=%(user)s
  AND (%(tx_type)s::text IS NULL OR t.tx_type = %(tx_type)s::tx_type)
  AND (%(date_from)s::date IS NULL OR t.occurred_on >= %(date_from)s::date)
  AND (%(date_to)s::date   IS NULL OR t.occurred_on <= %(date_to)s::date)
GROUP BY t.id
ORDER BY t.occurred_on DESC, t.id DESC
LIMIT %(limit)s;
"""

@router.get("/transactions")
def list_tx(tx_type: str | None = Query(None, pattern="^(purchase|sale)$"),
            date_from: str | None = None, date_to: str | None = None,
            limit: int = Query(100, ge=1, le=500)):
    rows = fetch_all(LIST_TX, {"user": USER, "tx_type": tx_type,
                               "date_from": date_from, "date_to": date_to, "limit": limit})
    return {"count": len(rows), "transactions": rows}

REPORT = """
SELECT
  COALESCE(SUM(total_amount) FILTER (WHERE tx_type='purchase'),0) AS purchase_total,
  COALESCE(SUM(total_amount) FILTER (WHERE tx_type='sale'),0)     AS sale_total,
  COUNT(*) FILTER (WHERE tx_type='purchase')                      AS purchase_count,
  COUNT(*) FILTER (WHERE tx_type='sale')                          AS sale_count
FROM app_transaction
WHERE user_id=%(user)s
  AND (%(date_from)s::date IS NULL OR occurred_on >= %(date_from)s::date)
  AND (%(date_to)s::date   IS NULL OR occurred_on <= %(date_to)s::date);
"""
REPORT_ITEMS = """
SELECT l.item_name, SUM(l.line_total) AS amount, SUM(l.quantity) AS qty
FROM app_transaction_line l JOIN app_transaction t ON t.id=l.transaction_id
WHERE t.user_id=%(user)s AND t.tx_type='purchase'
  AND (%(date_from)s::date IS NULL OR t.occurred_on >= %(date_from)s::date)
  AND (%(date_to)s::date   IS NULL OR t.occurred_on <= %(date_to)s::date)
GROUP BY l.item_name ORDER BY amount DESC LIMIT 5;
"""

@router.get("/reports/summary")
def report(date_from: str | None = None, date_to: str | None = None):
    tot = fetch_all(REPORT, {"user": USER, "date_from": date_from, "date_to": date_to})[0]
    items = fetch_all(REPORT_ITEMS, {"user": USER, "date_from": date_from, "date_to": date_to})
    pt, st = int(tot["purchase_total"]), int(tot["sale_total"])
    return {
        "date_from": date_from, "date_to": date_to,
        "purchase_total": pt, "sale_total": st, "est_margin": st - pt,
        "purchase_count": int(tot["purchase_count"]), "sale_count": int(tot["sale_count"]),
        "top_items": [{"item_name": r["item_name"], "amount": int(r["amount"]), "qty": int(r["qty"])} for r in items],
    }

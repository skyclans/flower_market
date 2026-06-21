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

# 화원 평균 매출원가율(보수적 추정치). 매출 대비 기대 매입을 역산해 '미기록 추정'을 낸다.
COGS_RATIO = 0.45


@router.get("/reports/summary")
def report(date_from: str | None = None, date_to: str | None = None):
    tot = fetch_all(REPORT, {"user": USER, "date_from": date_from, "date_to": date_to})[0]
    items = fetch_all(REPORT_ITEMS, {"user": USER, "date_from": date_from, "date_to": date_to})
    pt, st = int(tot["purchase_total"]), int(tot["sale_total"])
    # 미기록 추정: 매출이 시사하는 기대 매입(매출×원가율)에서 실제 기록 매입을 뺀 양(음수면 0).
    unrecorded_est = max(0, round(st * COGS_RATIO) - pt)
    return {
        "date_from": date_from, "date_to": date_to,
        "purchase_total": pt, "sale_total": st, "est_margin": st - pt,
        "purchase_count": int(tot["purchase_count"]), "sale_count": int(tot["sale_count"]),
        "top_items": [{"item_name": r["item_name"], "amount": int(r["amount"]), "qty": int(r["qty"])} for r in items],
        "deduction": {
            "recorded_purchase": pt,
            "unrecorded_est": unrecorded_est,
            "basis": f"매출 추정 매입(매출원가율 {int(COGS_RATIO * 100)}%) − 기록 매입",
        },
    }


# ===== 매입/매출 시계열 (일·주·월·연 그래프용) =====
# granularity는 화이트리스트로만 SQL에 주입(인젝션 차단). (unit, interval, 기본 버킷 수)
_GRAN = {
    "day":   ("day",   "1 day",   30),
    "week":  ("week",  "1 week",  12),
    "month": ("month", "1 month", 12),
    "year":  ("year",  "1 year",  5),
}

def _default_range(gran: str) -> tuple[str, str]:
    """granularity별 기본 조회 구간(최근 N버킷 ~ 오늘)."""
    today = dt.date.today()
    n = _GRAN[gran][2]
    if gran == "day":
        start = today - dt.timedelta(days=n - 1)
    elif gran == "week":
        monday = today - dt.timedelta(days=today.weekday())
        start = monday - dt.timedelta(weeks=n - 1)
    elif gran == "month":
        y, m = today.year, today.month - (n - 1)
        while m <= 0:
            m += 12; y -= 1
        start = dt.date(y, m, 1)
    else:  # year
        start = dt.date(today.year - (n - 1), 1, 1)
    return start.isoformat(), today.isoformat()

SERIES_SQL = """
WITH buckets AS (
  SELECT generate_series(
    date_trunc('{unit}', %(from)s::date),
    date_trunc('{unit}', %(to)s::date),
    interval '{interval}') AS b
), agg AS (
  SELECT date_trunc('{unit}', occurred_on) AS b,
    COALESCE(SUM(total_amount) FILTER (WHERE tx_type='purchase'),0) AS purchase,
    COALESCE(SUM(total_amount) FILTER (WHERE tx_type='sale'),0)     AS sale,
    COUNT(*) FILTER (WHERE tx_type='purchase')                      AS pc,
    COUNT(*) FILTER (WHERE tx_type='sale')                          AS sc
  FROM app_transaction
  WHERE user_id=%(user)s
    AND occurred_on >= %(from)s::date AND occurred_on <= %(to)s::date
  GROUP BY 1
)
SELECT to_char(b.b, 'YYYY-MM-DD') AS bucket,
       COALESCE(a.purchase,0)::bigint AS purchase,
       COALESCE(a.sale,0)::bigint     AS sale,
       COALESCE(a.pc,0)::int          AS purchase_count,
       COALESCE(a.sc,0)::int          AS sale_count
FROM buckets b LEFT JOIN agg a ON a.b = b.b
ORDER BY b.b;
"""

@router.get("/reports/series")
def report_series(granularity: str = Query("month", pattern="^(day|week|month|year)$"),
                  date_from: str | None = None, date_to: str | None = None):
    """매입/매출 시계열 — 일·주·월·연 버킷별 합계. 빈 버킷도 0으로 채워 반환(차트 연속성)."""
    unit, interval, _ = _GRAN[granularity]
    df, dt_ = (date_from, date_to)
    if not df or not dt_:
        d0, d1 = _default_range(granularity)
        df, dt_ = (df or d0), (dt_ or d1)
    sql = SERIES_SQL.format(unit=unit, interval=interval)
    rows = fetch_all(sql, {"user": USER, "from": df, "to": dt_})
    points = [{
        "bucket": r["bucket"],
        "purchase": int(r["purchase"]), "sale": int(r["sale"]),
        "margin": int(r["sale"]) - int(r["purchase"]),
        "purchase_count": int(r["purchase_count"]), "sale_count": int(r["sale_count"]),
    } for r in rows]
    tot_p = sum(p["purchase"] for p in points)
    tot_s = sum(p["sale"] for p in points)
    return {
        "granularity": granularity, "date_from": df, "date_to": dt_,
        "points": points,
        "totals": {"purchase": tot_p, "sale": tot_s, "margin": tot_s - tot_p},
    }


# ===== 세무 전문가 연결 · 빠른 절세 상담 =====
class ConsultIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=40)
    phone: str = Field(..., min_length=1, max_length=20)
    biz_type: str | None = Field(None, pattern="^(tax_free|general|simplified)$")
    channel: str = Field("phone", pattern="^(phone|kakao)$")
    memo: str | None = None
    month_purchase: int = Field(0, ge=0)
    month_count: int = Field(0, ge=0)

INSERT_CONSULT = """
INSERT INTO app_consult_request
  (user_id, name, phone, biz_type, channel, memo, month_purchase, month_count)
VALUES (%(user)s, %(name)s, %(phone)s, %(biz_type)s, %(channel)s, %(memo)s, %(month_purchase)s, %(month_count)s)
RETURNING id, created_at;
"""

@router.post("/consult")
def create_consult(body: ConsultIn):
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(INSERT_CONSULT, {
            "user": USER, "name": body.name, "phone": body.phone, "biz_type": body.biz_type,
            "channel": body.channel, "memo": body.memo,
            "month_purchase": body.month_purchase, "month_count": body.month_count,
        })
        row = cur.fetchone()
    return {"id": row["id"], "status": "new", "created_at": str(row["created_at"])}

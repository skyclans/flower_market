# -*- coding: utf-8 -*-
"""
꽃장부 API — 비교 슬라이스 (Neon 연결).

엔드포인트:
  GET  /health
  GET  /items?market=                          품목 목록(피커)
  GET  /home?market=&items=장미,거베라          홈 카드용 요약(본경매/온라인/지난주)
  GET  /prices/today?market=&date=             일자 시세(본경매/온라인)
  GET  /items/{item}/trend?market=&period=     기간별 추세 + 통계
  POST /compare                                매입가 vs 경매가 갭

실행: DATABASE_URL=postgresql://... uvicorn api.main:app --reload
문서: http://localhost:8000/docs
"""
from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parent))
import queries as q                       # noqa: E402
from db import pool, fetch_all            # noqa: E402
from ledger import router as ledger_router  # noqa: E402

PRIMARY_MARKET = "0000000001"   # 양재
DEFAULT_ITEMS = ["장미", "거베라", "호접란", "국화"]


@asynccontextmanager
async def lifespan(_: FastAPI):
    pool.open()
    yield
    pool.close()


app = FastAPI(title="꽃장부 API", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # 개발용. 운영 시 도메인 화이트리스트로 교체.
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(ledger_router)  # 장부: /quote, /transactions, /reports/summary


def _num(x):
    return None if x is None else float(x)


@app.get("/health")
def health():
    try:
        fetch_all("SELECT 1 AS ok;", {})
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(503, f"db unavailable: {e}")


@app.get("/items")
def items(market: str = Query(PRIMARY_MARKET)):
    rows = fetch_all(q.ITEMS, {"market": market})
    return {"market": market, "count": len(rows), "items": rows}


@app.get("/home")
def home(market: str = Query(PRIMARY_MARKET),
         items: str = Query(",".join(DEFAULT_ITEMS),
                            description="쉼표구분 품목명")):
    names = [s.strip() for s in items.split(",") if s.strip()]
    out = []
    for name in names:
        rows = fetch_all(q.HOME_ITEM, {"market": market, "item": name})
        if not rows or rows[0]["main_price"] is None and rows[0]["online_price"] is None:
            continue
        r = rows[0]
        main, prev = _num(r["main_price"]), _num(r["prev_main"])
        wow = None
        if main and prev:
            wow = round((main - prev) / prev * 100, 1)
        out.append({
            "item_name": name,
            "category": r["category"],
            "unit": r["unit"],
            "main_price": main,
            "online_price": _num(r["online_price"]),
            "wow_pct": wow,
            "as_of": str(r["as_of"]) if r["as_of"] else None,
        })
    return {"market": market, "items": out}


@app.get("/prices/today")
def prices_today(market: str = Query(PRIMARY_MARKET),
                 date: str | None = Query(None, description="YYYY-MM-DD, 생략 시 최신")):
    sql = """
    SELECT auction_date, category, item_name, variety_name, grade, unit,
           trade_volume, min_price, max_price, avg_price, auction_type
    FROM auction_price
    WHERE market_code=%(market)s
      AND auction_date = COALESCE(%(date)s,
            (SELECT MAX(auction_date) FROM auction_price WHERE market_code=%(market)s))
    ORDER BY trade_volume DESC, item_name;
    """
    rows = fetch_all(sql, {"market": market, "date": date})
    asof = str(rows[0]["auction_date"]) if rows else date
    return {"market": market, "date": asof, "count": len(rows), "prices": rows}


@app.get("/items/{item}/trend")
def item_trend(item: str,
               market: str = Query(PRIMARY_MARKET),
               period: str = Query("monthly", pattern="^(daily|weekly|monthly|yearly)$")):
    rows = fetch_all(q.trend_sql(period), {"market": market, "item": item})
    pts = [{"key": r["k"], "price": _num(r["price"]), "volume": int(r["volume"] or 0)}
           for r in rows if r["price"] is not None]
    # yearly/monthly 은 최근 12버킷만
    if period in ("monthly", "yearly"):
        pts = pts[-12:]
    prices = [p["price"] for p in pts]
    stats = {
        "avg": round(sum(prices) / len(prices)) if prices else None,
        "max": max(prices) if prices else None,
        "min": min(prices) if prices else None,
    }
    return {"market": market, "item": item, "period": period, "points": pts, "stats": stats}


class CompareIn(BaseModel):
    item_name: str = Field(..., description="품목명")
    my_price: int = Field(..., ge=0)
    market: str = PRIMARY_MARKET
    variety_name: str | None = None
    grade: str | None = None


@app.post("/compare")
def compare(body: CompareIn):
    rows = fetch_all(q.COMPARE, {"market": body.market, "item": body.item_name,
                                 "variety": body.variety_name, "grade": body.grade})
    if not rows:
        raise HTTPException(404, f"'{body.item_name}' 경매 데이터 없음")
    result = {"item_name": body.item_name, "my_price": body.my_price, "market": body.market,
              "auction_date": str(rows[0]["auction_date"]), "by_auction_type": {}}
    for r in rows:
        wavg = _num(r["wavg_price"])
        gap = None if not wavg else round((body.my_price - wavg) / wavg * 100, 1)
        result["by_auction_type"][r["auction_type"]] = {
            "wavg_price": wavg, "min_price": int(r["min_price"]), "max_price": int(r["max_price"]),
            "volume": int(r["volume"]), "my_price_vs_avg_pct": gap,
        }
    return result

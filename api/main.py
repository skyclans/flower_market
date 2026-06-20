# -*- coding: utf-8 -*-
"""
꽃장부 API — 비교 슬라이스.

엔드포인트:
  GET  /health                         상태확인
  GET  /items?market=                  품목 목록(즐겨찾기 피커, 거래량순)
  GET  /prices/today?market=&date=     오늘(또는 지정일) 시세, 본경매/온라인 분리
  GET  /items/{item}/trend?market=&days=30   품목 추세
  POST /compare                        매입가 vs 경매가 갭

실행:
  DATABASE_URL=postgresql://... uvicorn api.main:app --reload
문서: http://localhost:8000/docs
"""
from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parent))

import queries as q          # noqa: E402
from db import pool, fetch_all  # noqa: E402

PRIMARY_MARKET = "0000000001"   # 양재


@asynccontextmanager
async def lifespan(_: FastAPI):
    pool.open()
    yield
    pool.close()


app = FastAPI(title="꽃장부 API", version="0.1.0", lifespan=lifespan)


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


@app.get("/prices/today")
def prices_today(
    market: str = Query(PRIMARY_MARKET),
    date: str | None = Query(None, description="YYYY-MM-DD, 생략 시 최신 거래일"),
):
    rows = fetch_all(q.TODAY, {"market": market, "date": date})
    if not rows:
        return {"market": market, "date": date, "count": 0, "prices": []}
    return {"market": market, "date": str(rows[0]["auction_date"]),
            "count": len(rows), "prices": rows}


@app.get("/items/{item}/trend")
def item_trend(
    item: str,
    market: str = Query(PRIMARY_MARKET),
    days: int = Query(30, ge=1, le=180),
):
    rows = fetch_all(q.TREND, {"market": market, "item": item, "days": days})
    # 일자별 main/online 분리해 정리
    return {"market": market, "item": item, "days": days,
            "points": [
                {"date": str(r["auction_date"]), "auction_type": r["auction_type"],
                 "avg_price": float(r["wavg_price"]) if r["wavg_price"] is not None else None,
                 "volume": int(r["volume"])}
                for r in rows
            ]}


class CompareIn(BaseModel):
    item_name: str = Field(..., description="품목명 (예: 장미)")
    my_price: int = Field(..., ge=0, description="내 매입 단가")
    market: str = PRIMARY_MARKET
    variety_name: str | None = None
    grade: str | None = None


@app.post("/compare")
def compare(body: CompareIn):
    rows = fetch_all(q.COMPARE, {
        "market": body.market, "item": body.item_name,
        "variety": body.variety_name, "grade": body.grade,
    })
    if not rows:
        raise HTTPException(404, f"'{body.item_name}' 경매 데이터 없음")

    result = {"item_name": body.item_name, "my_price": body.my_price,
              "market": body.market, "auction_date": str(rows[0]["auction_date"]),
              "by_auction_type": {}}
    for r in rows:
        wavg = float(r["wavg_price"]) if r["wavg_price"] is not None else None
        gap = None if wavg in (None, 0) else round((body.my_price - wavg) / wavg * 100, 1)
        result["by_auction_type"][r["auction_type"]] = {
            "wavg_price": wavg,
            "min_price": int(r["min_price"]),
            "max_price": int(r["max_price"]),
            "volume": int(r["volume"]),
            "my_price_vs_avg_pct": gap,   # +면 내가 비싸게 매입, -면 싸게
        }
    return result

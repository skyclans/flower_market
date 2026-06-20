# -*- coding: utf-8 -*-
"""
백필 로더 — data/auction_prices.csv 의 기존 스냅샷을 DB 에 일괄 적재.

run_daily.py 는 '최신 거래일'만 가져온다. 이 스크립트는 Phase 0 에서 수집해 둔
전체 CSV(20,551행)를 한 번에 넣는 용도다. 신규 DB 초기 적재나 재적재에 사용.

전제: schema/auction_price.sql 적용 완료. DATABASE_URL 환경변수 설정.
실행:
  DATABASE_URL=postgresql://... python etl/load_csv.py
  DATABASE_URL=postgresql://... python etl/load_csv.py data/auction_prices.csv
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "sources"))

from base import AuctionRecord                       # noqa: E402
from db import connect, ensure_markets, upsert_records  # noqa: E402
from codes import MARKETS as MARKET_NAMES            # noqa: E402

DEFAULT_CSV = Path(__file__).resolve().parent.parent / "data" / "auction_prices.csv"

FIELDS = ("auction_date", "market_code", "market_name", "category", "item_name",
          "variety_name", "grade", "unit", "trade_volume", "min_price",
          "max_price", "avg_price", "auction_type", "source", "fetched_at")


def load(csv_path: Path) -> None:
    records: list[AuctionRecord] = []
    with open(csv_path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            records.append(AuctionRecord(
                auction_date=row["auction_date"],
                market_code=row["market_code"],
                market_name=row.get("market_name", ""),
                category=row["category"],
                item_name=row["item_name"],
                variety_name=row["variety_name"],
                grade=row["grade"],
                unit=row["unit"],
                trade_volume=int(row["trade_volume"]),
                min_price=int(row["min_price"]),
                max_price=int(row["max_price"]),
                avg_price=int(row["avg_price"]),
                auction_type=row["auction_type"],
                source=row.get("source", "flower.at.or.kr/excelDownLoad"),
                fetched_at=row["fetched_at"],
            ))

    print(f"CSV 로드: {len(records):,}행 ({csv_path.name})")
    conn = connect()
    markets = sorted({r.market_code for r in records})
    ensure_markets(markets, MARKET_NAMES, conn=conn)
    loaded, skipped = upsert_records(records, conn=conn)
    conn.close()
    print(f"적재 완료: upsert {loaded:,}행"
          + (f" · 정합성 스킵 {skipped}행" if skipped else ""))


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    if not path.exists():
        raise SystemExit(f"파일 없음: {path}")
    load(path)

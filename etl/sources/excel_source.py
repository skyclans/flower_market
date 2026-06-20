# -*- coding: utf-8 -*-
"""
엑셀 소스 — Phase 0 에서 검증된 flower.at.or.kr 수집 로직을 AuctionSource 로 감싼다.

collect_auction.py 의 저수준 함수(세션/거래일/다운로드/파싱)를 재사용한다.
'지금 작동하는' 기본 소스이자, Open API 가 화훼를 안 실으면 영구 폴백.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from base import AuctionRecord, AuctionSource  # noqa: E402
from collect_auction import (  # noqa: E402
    new_session, get_sale_dates, download_excel, parse_excel,
)
from codes import MARKETS  # noqa: E402


class ExcelSource(AuctionSource):
    """flower.at.or.kr 일자별 경매동향 엑셀 기반 소스."""

    name = "flower.at.or.kr/excelDownLoad"

    def __init__(self, save_raw: bool = True):
        self._session = None
        self.save_raw = save_raw
        self._raw_dir = Path(__file__).resolve().parent.parent.parent / "data" / "raw"

    def _sess(self):
        if self._session is None:
            self._session = new_session()
        return self._session

    def list_dates(self, market_code: str) -> list[str]:
        return get_sale_dates(self._sess(), market_code)

    def fetch(self, market_code: str, date: str) -> list[AuctionRecord]:
        blob = download_excel(self._sess(), market_code, date)
        if blob is None:
            return []
        if self.save_raw:
            self._raw_dir.mkdir(parents=True, exist_ok=True)
            (self._raw_dir / f"{market_code}_{date}.xls").write_bytes(blob)
        rows = parse_excel(blob, market_code, date)
        # parse_excel 은 dict 를 반환 → AuctionRecord 로 승격
        return [AuctionRecord(**{k: r[k] for k in (
            "auction_date", "market_code", "market_name", "category",
            "item_name", "variety_name", "grade", "unit", "trade_volume",
            "min_price", "max_price", "avg_price", "auction_type",
            "source", "fetched_at",
        )}) for r in rows]


__all__ = ["ExcelSource"]

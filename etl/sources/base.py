# -*- coding: utf-8 -*-
"""
데이터 소스 추상화 — 엑셀 스크래퍼와 Open API를 교체 가능하게 하는 공통 계약.

핵심 아이디어:
  Phase 0 에서 검증된 엑셀 소스(flower.at.or.kr)는 '지금 작동'하는 소스다.
  Open API(data.go.kr 15141808)는 운영용 후보다.
  두 소스 모두 동일한 AuctionRecord 리스트를 내놓으면, 적재/배치/API 계층은
  소스가 무엇인지 몰라도 된다. run_daily.py 에서 환경변수 SOURCE 로만 갈아끼운다.

AuctionRecord 필드는 schema/auction_price.sql 의 auction_price 테이블과 1:1.
"""
from __future__ import annotations

import abc
import dataclasses as dc
import datetime as dt
from typing import Iterable


CATEGORIES = ("절화", "난", "관엽")
AUCTION_KINDS = ("main", "online")


@dc.dataclass(slots=True)
class AuctionRecord:
    """정규화된 경매 시세 1건. auction_price 테이블 컬럼과 동일."""
    auction_date: str          # 'YYYY-MM-DD'
    market_code: str           # 공판장/도매시장 코드
    market_name: str
    category: str              # 절화 | 난 | 관엽
    item_name: str
    variety_name: str
    grade: str
    unit: str                  # 속 | 분
    trade_volume: int
    min_price: int
    max_price: int
    avg_price: int
    auction_type: str          # main | online
    source: str
    fetched_at: str = dc.field(
        default_factory=lambda: dt.datetime.now().isoformat(timespec="seconds")
    )

    def is_valid(self) -> bool:
        """적재 전 정합성 점검. 스키마 CHECK 제약(avg<=max, 음수금지)과 동일 기준."""
        if not self.item_name or not self.variety_name or not self.grade:
            return False
        if min(self.trade_volume, self.min_price, self.max_price, self.avg_price) < 0:
            return False
        if self.avg_price > self.max_price:           # ck_price_order
            return False
        if self.category not in CATEGORIES:
            return False
        if self.auction_type not in AUCTION_KINDS:
            return False
        return True

    def dedup_key(self) -> tuple:
        return (self.auction_date, self.market_code,
                self.item_name, self.variety_name, self.grade)


class AuctionSource(abc.ABC):
    """경매 시세 소스 공통 인터페이스."""

    name: str = "abstract"

    @abc.abstractmethod
    def list_dates(self, market_code: str) -> list[str]:
        """해당 시장의 거래일 목록(YYYY-MM-DD), 최신순."""
        raise NotImplementedError

    @abc.abstractmethod
    def fetch(self, market_code: str, date: str) -> list[AuctionRecord]:
        """해당 시장·일자의 정규화 레코드."""
        raise NotImplementedError

    def fetch_latest(self, market_code: str, last: int = 1) -> list[AuctionRecord]:
        """최근 last개 거래일을 모아서 반환 (공통 헬퍼)."""
        out: list[AuctionRecord] = []
        for d in self.list_dates(market_code)[:last]:
            out.extend(self.fetch(market_code, d))
        return out


def dedup(records: Iterable[AuctionRecord]) -> list[AuctionRecord]:
    """dedup_key 기준 1건만 유지 (마지막 값 우선)."""
    by_key: dict[tuple, AuctionRecord] = {}
    for r in records:
        by_key[r.dedup_key()] = r
    return list(by_key.values())

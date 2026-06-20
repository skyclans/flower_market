# -*- coding: utf-8 -*-
"""데이터 소스 패키지. SOURCE 환경변수로 구현체를 선택한다."""
from __future__ import annotations

import os

from base import AuctionRecord, AuctionSource, dedup  # noqa: F401


def get_source(name: str | None = None, **kwargs) -> AuctionSource:
    """소스 팩토리. name in {'excel','openapi'} (기본: env SOURCE 또는 'excel')."""
    name = (name or os.environ.get("SOURCE", "excel")).lower()
    if name in ("excel", "flower", "at"):
        from excel_source import ExcelSource
        return ExcelSource(**kwargs)
    if name in ("openapi", "datagokr", "api"):
        from openapi_source import OpenApiSource
        return OpenApiSource(**kwargs)
    raise ValueError(f"알 수 없는 SOURCE: {name!r} (excel | openapi)")


__all__ = ["get_source", "AuctionRecord", "AuctionSource", "dedup"]

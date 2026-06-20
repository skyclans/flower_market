# -*- coding: utf-8 -*-
"""API 읽기용 커넥션 풀."""
from __future__ import annotations

import os

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL 환경변수가 필요합니다.")
    return dsn


pool = ConnectionPool(_dsn(), min_size=1, max_size=10, kwargs={"row_factory": dict_row}, open=False)


def fetch_all(sql: str, params: dict) -> list[dict]:
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()

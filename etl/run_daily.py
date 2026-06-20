# -*- coding: utf-8 -*-
"""
일배치 — 최신 경매 시세를 수집해 DB 에 upsert.

소스는 환경변수 SOURCE 로 선택 (excel | openapi). 둘 다 동일 인터페이스라
이 파일은 소스 종류를 신경 쓰지 않는다.

환경변수:
  SOURCE                 excel(기본) | openapi
  DATABASE_URL           postgresql://...
  MARKETS                쉼표구분 시장코드 (기본: 양재만)
  LAST_N                 시장당 최근 N 거래일 (기본: 1)
  DATA_GO_KR_SERVICE_KEY openapi 사용 시 필요
  OPENAPI_ENDPOINT       openapi 엔드포인트(정확값)
  OPENAPI_MARKET_CODES   openapi 시장코드 매핑(JSON)

실행:
  SOURCE=excel DATABASE_URL=postgresql://... python run_daily.py
  SOURCE=excel MARKETS=0000000001,7368200686 LAST_N=2 python run_daily.py
"""
from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "sources"))

from sources import get_source, dedup            # noqa: E402
from db import upsert_records, ensure_markets, connect  # noqa: E402
from codes import MARKETS as MARKET_NAMES, PRIMARY_MARKET  # noqa: E402


def parse_markets() -> list[str]:
    raw = os.environ.get("MARKETS", PRIMARY_MARKET)
    codes = [c.strip() for c in raw.split(",") if c.strip()]
    if codes == ["all"]:
        return list(MARKET_NAMES)
    return codes


def main() -> int:
    source_name = os.environ.get("SOURCE", "excel")
    markets = parse_markets()
    last_n = int(os.environ.get("LAST_N", "1"))

    print(f"[{dt.datetime.now().isoformat(timespec='seconds')}] "
          f"배치 시작 · source={source_name} · markets={markets} · last={last_n}")

    src = get_source(source_name)

    conn = connect()
    ensure_markets(markets, MARKET_NAMES, conn=conn)

    grand_loaded = grand_skipped = 0
    for code in markets:
        name = MARKET_NAMES.get(code, code)
        try:
            recs = dedup(src.fetch_latest(code, last=last_n))
        except Exception as e:
            print(f"  ✗ {name} ({code}) 수집 실패: {e}")
            continue
        loaded, skipped = upsert_records(recs, conn=conn)
        grand_loaded += loaded
        grand_skipped += skipped
        print(f"  ✓ {name} ({code}): upsert {loaded}건"
              + (f" · 스킵 {skipped}건(정합성)" if skipped else ""))

    conn.close()
    print(f"배치 완료 · 총 upsert {grand_loaded}건"
          + (f" · 총 스킵 {grand_skipped}건" if grand_skipped else ""))
    return 0 if grand_loaded > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

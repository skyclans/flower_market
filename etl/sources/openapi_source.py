# -*- coding: utf-8 -*-
"""
Open API 소스 — 공공데이터포털 15141808 (한국농수산식품유통공사 전국 공영도매시장
실시간 경매정보). 운영 전환용 후보 소스.

엑셀과의 본질적 차이:
  엑셀은 (품목·품종·등급)별로 이미 집계된 최저/최고/평균/속수량을 준다.
  이 API는 *거래 건별* 행(prce=단가, unit_qyt=수량)을 준다.
  따라서 (일자·시장·품목·품종·등급)으로 그룹핑해서 min/max/avg/volume 을
  직접 집계해야 한다. (평균은 수량가중 평균으로 계산.)

⚠️ 사용 전 반드시 확인할 것:
  1) serviceKey 발급 (data.go.kr 활용신청). 환경변수 DATA_GO_KR_SERVICE_KEY.
  2) 정확한 엔드포인트 URL — 활용신청 상세의 '엔드포인트/참고문서'에서 확인 후
     환경변수 OPENAPI_ENDPOINT 로 주입. 아래 기본값은 표준 패턴 추정치.
  3) 이 API가 '화훼'(양재 등)를 싣는지 확인. 농수산물 32개 도매시장 중심이라
     화훼 미포함일 수 있음 → 그 경우 ExcelSource 를 계속 사용.
  4) 시장 코드 매핑: 이 API의 whsl_mrkt_code 는 flower.at.or.kr 의 cmpCd 와
     다른 체계. OPENAPI_MARKET_CODES 에 (프로젝트 표준코드 → whsl_mrkt_code) 를
     채워야 함. 표준코드는 동반 API 15141818(농축수산물 표준코드)로 조회.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import statistics as st
import sys
import time
from collections import defaultdict
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from base import AuctionRecord, AuctionSource  # noqa: E402
from codes import MARKETS, MAIN_AUCTION_WEEKDAYS  # noqa: E402
from classify import classify_item  # noqa: E402


# data.go.kr 표준 REST 엔드포인트 (활용신청 상세에서 정확값 확인 후 env 로 덮어쓰기)
DEFAULT_ENDPOINT = "http://apis.data.go.kr/B190001/WholesaleMarketAuctionInfo/getAuctionInfo"
ENDPOINT = os.environ.get("OPENAPI_ENDPOINT", DEFAULT_ENDPOINT)
SERVICE_KEY = os.environ.get("DATA_GO_KR_SERVICE_KEY", "")

# 프로젝트 표준 시장코드(cmpCd) → 이 API 의 whsl_mrkt_code
#   비어 있으면 OpenAPI 소스는 동작하지 않음. env OPENAPI_MARKET_CODES(JSON)로 주입 가능.
#   예: OPENAPI_MARKET_CODES='{"0000000001":"110001"}'
OPENAPI_MARKET_CODES: dict[str, str] = json.loads(
    os.environ.get("OPENAPI_MARKET_CODES", "{}")
)

# API 응답 필드 → 내부 의미 (명세서 컬럼 기준)
F_DATE = "auc_ymd"          # 경매일자
F_MARKET = "whsl_mrkt_code"  # 도매시장코드
F_ITEM = "pdlt_nm"          # 품목명
F_VARIETY = "spcs_nm"       # 품종명
F_GRADE = "mtc_grad_nm"     # 산지등급명
F_QTY = "unit_qyt"          # 단위수량
F_PRICE = "prce"            # 가격(단가)

PAGE_SIZE = 1000
MAX_PAGES = 50
REQUEST_GAP_SEC = 0.4


def _to_int(v, default=0) -> int:
    try:
        return int(round(float(str(v).replace(",", "").strip())))
    except (ValueError, TypeError):
        return default


def _extract_items(payload: dict) -> list[dict]:
    """data.go.kr 응답 봉투에서 item 리스트를 방어적으로 추출.

    지원 형태:
      response.body.items.item = [...]        (표준)
      response.body.items = [...]             (변형)
      data = [...]                            (odcloud 형)
    """
    if not isinstance(payload, dict):
        return []
    if "data" in payload and isinstance(payload["data"], list):
        return payload["data"]
    body = payload.get("response", {}).get("body", {})
    items = body.get("items", [])
    if isinstance(items, dict):
        items = items.get("item", [])
    if isinstance(items, dict):       # 단건이면 dict
        items = [items]
    return items if isinstance(items, list) else []


def _header_ok(payload: dict) -> tuple[bool, str]:
    hdr = payload.get("response", {}).get("header", {})
    code = hdr.get("resultCode")
    if code is None:
        return True, ""               # odcloud 형은 header 없음
    return code in ("00", "0"), hdr.get("resultMsg", str(code))


class OpenApiSource(AuctionSource):
    """data.go.kr 15141808 기반 소스."""

    name = "data.go.kr/15141808"

    def __init__(self, service_key: str | None = None, endpoint: str | None = None):
        self.service_key = service_key or SERVICE_KEY
        self.endpoint = endpoint or ENDPOINT
        if not self.service_key:
            raise RuntimeError(
                "DATA_GO_KR_SERVICE_KEY 가 비어 있습니다. data.go.kr 활용신청 후 "
                "환경변수로 serviceKey 를 설정하세요."
            )

    # ── 거래일 ─────────────────────────────────────────────────────────
    def list_dates(self, market_code: str) -> list[str]:
        """API 는 날짜 enum 을 주지 않음 → 최근 영업일 후보를 생성.

        일요일/미래일 제외. 비경매일은 fetch 가 빈 리스트를 돌려준다.
        """
        today = dt.date.today()
        out = []
        d = today
        while len(out) < 21:                       # 최근 3주 후보
            if d.weekday() != 6:                   # 일요일 제외
                out.append(d.isoformat())
            d -= dt.timedelta(days=1)
        return out

    # ── 수집 ───────────────────────────────────────────────────────────
    def _request_page(self, mrkt_code: str, date: str, page: int) -> dict:
        params = {
            "serviceKey": self.service_key,
            "pageNo": page,
            "numOfRows": PAGE_SIZE,
            "type": "json",
            "saleDate": date,           # 일자 파라미터 (명세: YYYY-MM-DD)
            "whsmkCd": mrkt_code,       # 시장 파라미터 (명세 확인 후 키명 조정)
        }
        r = requests.get(self.endpoint, params=params, timeout=40)
        r.raise_for_status()
        try:
            return r.json()
        except ValueError:
            # XML 로 떨어지면 명세/파라미터 점검 필요
            raise RuntimeError(
                "JSON 파싱 실패 — type=json 미지원이거나 엔드포인트/파라미터 오류. "
                f"응답 머리: {r.text[:200]}"
            )

    def fetch(self, market_code: str, date: str) -> list[AuctionRecord]:
        mrkt = OPENAPI_MARKET_CODES.get(market_code)
        if not mrkt:
            raise RuntimeError(
                f"시장코드 매핑 없음: {market_code}. OPENAPI_MARKET_CODES 에 "
                f"(표준코드 → whsl_mrkt_code) 를 채우세요 (API 15141818 로 조회)."
            )

        # 1) 거래 건별 행 수집 (페이지네이션)
        raw_rows: list[dict] = []
        for page in range(1, MAX_PAGES + 1):
            payload = self._request_page(mrkt, date, page)
            ok, msg = _header_ok(payload)
            if not ok:
                raise RuntimeError(f"API 오류: {msg}")
            items = _extract_items(payload)
            if not items:
                break
            raw_rows.extend(items)
            if len(items) < PAGE_SIZE:
                break
            time.sleep(REQUEST_GAP_SEC)

        if not raw_rows:
            return []

        # 2) (품목·품종·등급)별 집계 → min/max/avg/volume
        wd = dt.date.fromisoformat(date).weekday()
        auction_type = "main" if wd in MAIN_AUCTION_WEEKDAYS else "online"
        market_name = MARKETS.get(market_code, market_code)

        groups: dict[tuple, list[tuple[int, int]]] = defaultdict(list)  # (price, qty)
        for row in raw_rows:
            item = str(row.get(F_ITEM, "")).strip()
            if not item:
                continue
            variety = str(row.get(F_VARIETY, "")).strip() or "기타"
            grade = str(row.get(F_GRADE, "")).strip() or "무등급"
            price = _to_int(row.get(F_PRICE))
            qty = _to_int(row.get(F_QTY))
            if price <= 0:
                continue
            groups[(item, variety, grade)].append((price, max(qty, 0)))

        out: list[AuctionRecord] = []
        for (item, variety, grade), pairs in groups.items():
            prices = [p for p, _ in pairs]
            vols = [q for _, q in pairs]
            total_vol = sum(vols)
            # 수량가중 평균 (수량 0뿐이면 단순평균)
            if total_vol > 0:
                avg = round(sum(p * q for p, q in pairs) / total_vol)
            else:
                avg = round(st.mean(prices))
            category, _ = classify_item(item)
            unit = "속" if category == "절화" else "분"
            rec = AuctionRecord(
                auction_date=date,
                market_code=market_code,
                market_name=market_name,
                category=category,
                item_name=item,
                variety_name=variety,
                grade=grade,
                unit=unit,
                trade_volume=total_vol,
                min_price=min(prices),
                max_price=max(prices),
                avg_price=min(avg, max(prices)),   # 가중평균이 max 넘지 않게 클램프
                auction_type=auction_type,
                source=self.name,
            )
            if rec.is_valid():
                out.append(rec)
        return out


__all__ = ["OpenApiSource"]

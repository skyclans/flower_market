# -*- coding: utf-8 -*-
"""
꽃장부 — 양재(aT) 화훼 경매시세 수집기 (Phase 0 ETL PoC)
==========================================================

PRD §9.4 "양재 시세 데이터 파이프라인"의 Stage 1(헤드리스/HTTP 수집) 구현체.
화훼유통정보시스템(flower.at.or.kr)의 일자별 경매동향 Excel을 내려받아
PRD §9.3 AuctionPrice 스키마에 맞는 정규화 long-format으로 적재한다.

성공률(Phase 0 Exit Criteria: ETL 성공률 ≥ 90%)을 collection_report.json에 기록한다.

운영 원칙(PRD 9.4 / Risk R1):
  - robots.txt 및 합리적 호출 간격 준수 (요청 간 sleep)
  - User-Agent 명시, 세션 쿠키 재사용
  - 사이트 구조 변경/차단 대비 → Stage 2(공공데이터포털 Open API)가 정식 경로.
    본 수집기는 PoC·백업용. 운영 전환 시 data.go.kr 15141808(전국 공영도매시장
    실시간 경매정보) serviceKey 기반 API로 이관 권장.

사용법:
  python collect_auction.py --market 0000000001 --last 25
  python collect_auction.py --market all --last 1
  python collect_auction.py --market 0000000001 --from 2026-06-01 --to 2026-06-20
"""
import argparse
import csv
import datetime as dt
import io
import json
import sys
import time
from pathlib import Path

import requests
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codes import (  # noqa: E402
    MARKETS, PRIMARY_MARKET, BASE_URL, MAIN_PAGE, SALE_DATE_JSON,
    EXCEL_DOWNLOAD, MAIN_AUCTION_WEEKDAYS,
)
from classify import classify_item, build_item_master  # noqa: E402

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"

# Excel 컬럼 → 정규화 필드 매핑
COL_MAP = {
    "품목명": "item_name", "품종명": "variety_name", "등급": "grade",
    "속수량": "trade_volume", "최저단가": "min_price",
    "최고단가": "max_price", "평균단가": "avg_price",
}

REQUEST_GAP_SEC = 1.2   # 호출 간 간격 (사이트 부담 최소화)
MAX_RETRY = 5


def new_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Referer": MAIN_PAGE})
    # 세션 쿠키(KHANUSER, JSESSIONID) 확보
    for _ in range(MAX_RETRY):
        try:
            r = s.get(MAIN_PAGE, timeout=30)
            if r.status_code == 200 and len(r.content) > 1000:
                return s
        except requests.RequestException:
            pass
        time.sleep(REQUEST_GAP_SEC)
    raise RuntimeError("세션 초기화 실패 — flower.at.or.kr 접근 불가")


def get_sale_dates(session: requests.Session, cmp_cd: str) -> list[str]:
    """공판장별 거래일 목록 (YYYY-MM-DD), 최신순."""
    for _ in range(MAX_RETRY):
        try:
            r = session.post(SALE_DATE_JSON, data={"searchCmpCd": cmp_cd},
                             headers={"X-Requested-With": "XMLHttpRequest"}, timeout=30)
            if r.ok and r.text.strip():
                return [x["saleDate"] for x in r.json().get("list", [])]
        except (requests.RequestException, ValueError):
            pass
        time.sleep(REQUEST_GAP_SEC)
    return []


def download_excel(session: requests.Session, cmp_cd: str, date: str) -> bytes | None:
    """일자별 경매동향 .xls 바이트. 실패 시 None."""
    params = {"excelNm": "일자별 경매동향", "saleDate": date, "cmpCd": cmp_cd}
    headers = {"Referer": f"{BASE_URL}/hab09/hab09.do"}
    for _ in range(MAX_RETRY):
        try:
            r = session.get(EXCEL_DOWNLOAD, params=params, headers=headers, timeout=40)
            # 정상 .xls 는 OLE 시그니처(D0 CF 11 E0)로 시작, 최소 2KB+
            if r.ok and len(r.content) > 2000 and r.content[:4] == b"\xd0\xcf\x11\xe0":
                return r.content
        except requests.RequestException:
            pass
        time.sleep(REQUEST_GAP_SEC)
    return None


def parse_excel(blob: bytes, cmp_cd: str, date: str) -> list[dict]:
    """xls 바이트 → 정규화 레코드 목록."""
    df = pd.read_excel(io.BytesIO(blob), engine="xlrd")
    missing = set(COL_MAP) - set(df.columns)
    if missing:
        raise ValueError(f"예상 외 컬럼 구조 (누락: {missing}) — 사이트 구조 변경 가능")
    df = df.rename(columns=COL_MAP)
    fetched = dt.datetime.now().isoformat(timespec="seconds")
    wd = dt.date.fromisoformat(date).weekday()
    auction_type = "main" if wd in MAIN_AUCTION_WEEKDAYS else "online"

    out = []
    for _, row in df.iterrows():
        item = str(row["item_name"]).strip()
        category, _ = classify_item(item)
        # 단위: 절화=속, 난·관엽=분 (품종명에 규격 인코딩)
        unit = "속" if category == "절화" else "분"
        try:
            vol = int(row["trade_volume"]); lo = int(row["min_price"])
            hi = int(row["max_price"]); avg = int(row["avg_price"])
        except (ValueError, TypeError):
            continue
        out.append({
            "auction_date": date,
            "market_code": cmp_cd,
            "market_name": MARKETS.get(cmp_cd, cmp_cd),
            "category": category,
            "item_name": item,
            "variety_name": str(row["variety_name"]).strip(),
            "grade": str(row["grade"]).strip(),
            "unit": unit,
            "trade_volume": vol,
            "min_price": lo,
            "max_price": hi,
            "avg_price": avg,
            "auction_type": auction_type,   # main(본경매 월·수·금) | online(화·목·토)
            "source": "flower.at.or.kr/excelDownLoad",
            "fetched_at": fetched,
        })
    return out


def collect(markets: list[str], dates_filter) -> tuple[list[dict], dict]:
    """수집 실행. (레코드, 리포트) 반환."""
    session = new_session()
    all_rows: list[dict] = []
    report = {"runs": [], "generated_at": dt.datetime.now().isoformat(timespec="seconds")}

    for cmp_cd in markets:
        name = MARKETS.get(cmp_cd, cmp_cd)
        dates = get_sale_dates(session, cmp_cd)
        targets = dates_filter(dates)
        print(f"\n▶ {name} ({cmp_cd}) — 거래일 {len(dates)}개 중 {len(targets)}개 수집 시도")
        ok = 0
        for d in targets:
            blob = download_excel(session, cmp_cd, d)
            if blob is None:
                print(f"   ✗ {d}  다운로드 실패")
                report["runs"].append({"market": cmp_cd, "date": d, "status": "download_fail"})
                continue
            # 원본 보관 (Stage 0 안전망 — 재처리 가능)
            raw_path = RAW_DIR / f"{cmp_cd}_{d}.xls"
            raw_path.write_bytes(blob)
            try:
                rows = parse_excel(blob, cmp_cd, d)
            except Exception as e:
                print(f"   ✗ {d}  파싱 실패: {e}")
                report["runs"].append({"market": cmp_cd, "date": d, "status": f"parse_fail:{e}"})
                continue
            all_rows.extend(rows)
            ok += 1
            print(f"   ✓ {d}  {len(rows):>5}건")
            report["runs"].append({"market": cmp_cd, "date": d, "status": "ok", "records": len(rows)})
            time.sleep(REQUEST_GAP_SEC)
        if targets:
            print(f"   → 성공률 {ok}/{len(targets)} = {ok/len(targets)*100:.1f}%")

    total = len(report["runs"])
    succ = sum(1 for r in report["runs"] if r["status"] == "ok")
    report["summary"] = {
        "attempted": total,
        "succeeded": succ,
        "success_rate_pct": round(succ / total * 100, 1) if total else 0.0,
        "total_records": len(all_rows),
        "exit_criteria_90pct_met": (succ / total >= 0.9) if total else False,
    }
    return all_rows, report


def write_outputs(rows: list[dict], report: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # 1) 정규화 long-format CSV (중복 제거: date+market+item+variety+grade 기준)
    seen, deduped = set(), []
    for r in sorted(rows, key=lambda x: (x["auction_date"], x["market_code"],
                                         x["category"], x["item_name"], x["variety_name"], x["grade"])):
        key = (r["auction_date"], r["market_code"], r["item_name"], r["variety_name"], r["grade"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)

    fields = ["auction_date", "market_code", "market_name", "category", "item_name",
              "variety_name", "grade", "unit", "trade_volume", "min_price",
              "max_price", "avg_price", "auction_type", "source", "fetched_at"]
    with (DATA_DIR / "auction_prices.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(deduped)

    # 2) ItemMaster (도메인 사전)
    master = build_item_master(deduped)
    mfields = ["item_name", "category", "classify_method",
               "observed_weekdays", "variety_count", "grade_set", "obs_dates", "total_volume"]
    with (DATA_DIR / "item_master.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=mfields)
        w.writeheader()
        w.writerows(master)

    # 3) 수집 리포트 (ETL 성공률 = Phase 0 Exit Criteria)
    report["dataset"] = {
        "rows_after_dedup": len(deduped),
        "items": len(master),
        "by_category": {c: sum(1 for r in deduped if r["category"] == c)
                        for c in ("절화", "난", "관엽")},
        "date_range": [min(r["auction_date"] for r in deduped),
                       max(r["auction_date"] for r in deduped)] if deduped else [],
        "markets": sorted({r["market_name"] for r in deduped}),
    }
    (DATA_DIR / "collection_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return deduped, master, report


def main():
    ap = argparse.ArgumentParser(description="양재(aT) 화훼 경매시세 수집기")
    ap.add_argument("--market", default=PRIMARY_MARKET,
                    help="공판장 코드 또는 'all' (기본: 양재 0000000001)")
    ap.add_argument("--last", type=int, default=None, help="최근 N개 거래일 수집")
    ap.add_argument("--from", dest="dfrom", default=None, help="시작일 YYYY-MM-DD")
    ap.add_argument("--to", dest="dto", default=None, help="종료일 YYYY-MM-DD")
    args = ap.parse_args()

    markets = list(MARKETS) if args.market == "all" else [args.market]

    def dfilter(dates: list[str]) -> list[str]:
        ds = dates
        if args.dfrom:
            ds = [d for d in ds if d >= args.dfrom]
        if args.dto:
            ds = [d for d in ds if d <= args.dto]
        if args.last:
            ds = ds[:args.last]
        return ds

    rows, report = collect(markets, dfilter)
    deduped, master, report = write_outputs(rows, report)

    s = report["summary"]
    print("\n" + "=" * 56)
    print(f"  수집 완료: {s['succeeded']}/{s['attempted']}일 성공 "
          f"({s['success_rate_pct']}%) · Exit≥90% {'✅' if s['exit_criteria_90pct_met'] else '❌'}")
    print(f"  정규화 레코드: {len(deduped):,}건 · 고유품목: {len(master)}종")
    print(f"  부류: {report['dataset']['by_category']}")
    print(f"  기간: {report['dataset']['date_range']}")
    print("=" * 56)


if __name__ == "__main__":
    main()

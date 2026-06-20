# -*- coding: utf-8 -*-
"""
data/raw/ 에 보관된 원본 .xls 전체를 다시 파싱해 정규화 데이터셋을 재생성한다.

PRD §9.4 Stage 0(수동 백업/재처리) 안전망. 분류 규칙(classify.py)을 수정한 뒤
재수집 없이 전체 데이터셋을 갱신할 때, 혹은 여러 번에 나눠 수집한 원본을 하나로
합칠 때 사용한다. 네트워크 호출 없음 — 디스크의 원본만 사용.

파일명 규칙: {cmpCd}_{YYYY-MM-DD}.xls
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect_auction import parse_excel, write_outputs, RAW_DIR  # noqa: E402
import datetime as dt  # noqa: E402


def main():
    files = sorted(RAW_DIR.glob("*.xls"))
    print(f"원본 파일 {len(files)}개에서 재처리 시작...")
    rows = []
    runs = []
    for fp in files:
        stem = fp.stem  # {cmpCd}_{date}
        try:
            cmp_cd, date = stem.split("_", 1)
            blob = fp.read_bytes()
            recs = parse_excel(blob, cmp_cd, date)
            rows.extend(recs)
            runs.append({"market": cmp_cd, "date": date, "status": "ok", "records": len(recs)})
        except Exception as e:
            print(f"  ✗ {fp.name}: {e}")
            runs.append({"market": stem, "date": "?", "status": f"parse_fail:{e}"})

    total = len(runs)
    succ = sum(1 for r in runs if r["status"] == "ok")
    report = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "mode": "rebuild_from_raw",
        "runs": runs,
        "summary": {
            "attempted": total, "succeeded": succ,
            "success_rate_pct": round(succ / total * 100, 1) if total else 0.0,
            "total_records": len(rows),
            "exit_criteria_90pct_met": (succ / total >= 0.9) if total else False,
        },
    }
    deduped, master, report = write_outputs(rows, report)
    print(f"✓ 재처리 완료: {len(deduped):,}건 · {len(master)}종 · "
          f"부류 {report['dataset']['by_category']}")


if __name__ == "__main__":
    main()

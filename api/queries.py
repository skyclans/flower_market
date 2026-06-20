# -*- coding: utf-8 -*-
"""읽기 전용 쿼리 모음 — 비교 슬라이스의 핵심 3개 + 보조."""

# 오늘(또는 지정일) 시세. 본경매/온라인 구분 유지.
TODAY = """
SELECT auction_date, market_code, category, item_name, variety_name, grade,
       unit, trade_volume, min_price, max_price, avg_price, auction_type
FROM auction_price
WHERE market_code = %(market)s
  AND auction_date = COALESCE(
        %(date)s,
        (SELECT MAX(auction_date) FROM auction_price WHERE market_code = %(market)s)
      )
ORDER BY trade_volume DESC, item_name, variety_name, grade;
"""

# 품목 추세 (최근 N일). 일자·경매구분별 가중평균가.
TREND = """
SELECT auction_date,
       auction_type,
       SUM(avg_price * trade_volume)::numeric / NULLIF(SUM(trade_volume), 0) AS wavg_price,
       SUM(trade_volume) AS volume
FROM auction_price
WHERE market_code = %(market)s
  AND item_name = %(item)s
  AND auction_date >= (CURRENT_DATE - %(days)s::int)
GROUP BY auction_date, auction_type
ORDER BY auction_date;
"""

# 매입가 비교 — 해당 품목 최신 경매가(본경매/온라인) 대비.
COMPARE = """
WITH latest AS (
  SELECT MAX(auction_date) AS d
  FROM auction_price
  WHERE market_code = %(market)s AND item_name = %(item)s
)
SELECT auction_type,
       SUM(avg_price * trade_volume)::numeric / NULLIF(SUM(trade_volume), 0) AS wavg_price,
       MIN(min_price) AS min_price,
       MAX(max_price) AS max_price,
       SUM(trade_volume) AS volume,
       (SELECT d FROM latest) AS auction_date
FROM auction_price
WHERE market_code = %(market)s
  AND item_name = %(item)s
  AND auction_date = (SELECT d FROM latest)
  AND (%(variety)s IS NULL OR variety_name = %(variety)s)
  AND (%(grade)s   IS NULL OR grade = %(grade)s)
GROUP BY auction_type;
"""

# 즐겨찾기 피커용 품목 목록 (거래량순).
ITEMS = """
SELECT item_name, category, SUM(trade_volume) AS total_volume,
       COUNT(DISTINCT variety_name) AS variety_count
FROM auction_price
WHERE market_code = %(market)s
GROUP BY item_name, category
ORDER BY total_volume DESC;
"""

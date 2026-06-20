# -*- coding: utf-8 -*-
"""읽기 전용 쿼리 — 홈 요약, 기간별 추세, 비교, 품목 목록."""

# 홈 카드 1개(품목)용: 최신 본경매가 / 최신 온라인가 / 지난주 대비(본경매)
HOME_ITEM = """
WITH lm AS (
  SELECT MAX(auction_date) d FROM auction_price
  WHERE market_code=%(market)s AND item_name=%(item)s AND auction_type='main'),
lo AS (
  SELECT MAX(auction_date) d FROM auction_price
  WHERE market_code=%(market)s AND item_name=%(item)s AND auction_type='online'),
mn AS (
  SELECT ROUND(SUM(avg_price*trade_volume)::numeric/NULLIF(SUM(trade_volume),0)) v
  FROM auction_price WHERE market_code=%(market)s AND item_name=%(item)s
    AND auction_type='main' AND auction_date=(SELECT d FROM lm)),
onl AS (
  SELECT ROUND(SUM(avg_price*trade_volume)::numeric/NULLIF(SUM(trade_volume),0)) v
  FROM auction_price WHERE market_code=%(market)s AND item_name=%(item)s
    AND auction_type='online' AND auction_date=(SELECT d FROM lo)),
prev AS (
  SELECT ROUND(SUM(avg_price*trade_volume)::numeric/NULLIF(SUM(trade_volume),0)) v
  FROM auction_price WHERE market_code=%(market)s AND item_name=%(item)s
    AND auction_type='main'
    AND auction_date BETWEEN (SELECT d FROM lm)-13 AND (SELECT d FROM lm)-7)
SELECT
  (SELECT category FROM item_master WHERE item_name=%(item)s)                          AS category,
  (SELECT unit FROM auction_price WHERE market_code=%(market)s AND item_name=%(item)s
     ORDER BY auction_date DESC LIMIT 1)                                               AS unit,
  (SELECT v FROM mn)   AS main_price,
  (SELECT v FROM onl)  AS online_price,
  (SELECT v FROM prev) AS prev_main,
  (SELECT d FROM lm)   AS as_of;
"""

# 기간별 추세 (본경매 기준 가중평균). period: monthly | weekly | daily | yearly
_TREND_BASE = """
SELECT {bucket} AS k,
       ROUND(SUM(avg_price*trade_volume)::numeric/NULLIF(SUM(trade_volume),0)) AS price,
       SUM(trade_volume) AS volume
FROM auction_price
WHERE market_code=%(market)s AND item_name=%(item)s {type_filter}
  AND auction_date >= (SELECT MAX(auction_date) FROM auction_price
                       WHERE market_code=%(market)s) - INTERVAL '{window}'
GROUP BY k ORDER BY k;
"""

def trend_sql(period: str) -> str:
    if period in ("monthly", "yearly"):
        return _TREND_BASE.format(bucket="to_char(auction_date,'YYYY-MM')",
                                  type_filter="AND auction_type='main'", window="13 months")
    if period == "weekly":
        return _TREND_BASE.format(bucket="to_char(date_trunc('week',auction_date),'YYYY-MM-DD')",
                                  type_filter="AND auction_type='main'", window="12 weeks")
    # daily: 모든 경매유형 합산(매 거래일 1점)
    return _TREND_BASE.format(bucket="to_char(auction_date,'YYYY-MM-DD')",
                              type_filter="", window="30 days")

# 매입가 비교 — 최신 경매가(본경매/온라인) 대비
COMPARE = """
WITH latest AS (
  SELECT MAX(auction_date) AS d FROM auction_price
  WHERE market_code=%(market)s AND item_name=%(item)s)
SELECT auction_type,
       ROUND(SUM(avg_price*trade_volume)::numeric/NULLIF(SUM(trade_volume),0)) AS wavg_price,
       MIN(min_price) AS min_price, MAX(max_price) AS max_price,
       SUM(trade_volume) AS volume, (SELECT d FROM latest) AS auction_date
FROM auction_price
WHERE market_code=%(market)s AND item_name=%(item)s
  AND auction_date=(SELECT d FROM latest)
  AND (%(variety)s::text IS NULL OR variety_name=%(variety)s::text)
  AND (%(grade)s::text   IS NULL OR grade=%(grade)s::text)
GROUP BY auction_type;
"""

# 품목 목록 (즐겨찾기 피커, 거래량순)
ITEMS = """
SELECT item_name, category, SUM(trade_volume) AS total_volume,
       COUNT(DISTINCT variety_name) AS variety_count
FROM auction_price
WHERE market_code=%(market)s
GROUP BY item_name, category
ORDER BY total_volume DESC;
"""

# -*- coding: utf-8 -*-
"""
aT 화훼유통정보시스템(flower.at.or.kr) 코드 상수.

출처: flower.at.or.kr 메인 페이지 공판장/부류 셀렉트 옵션 (2026-06 확인).
경매 운영 캘린더는 aT 화훼공판장 공시 기준.
"""

# 공판장(화훼공판장) 코드 → 명칭
#   getSaleData.json / excelDownLoad.do 의 cmpCd 파라미터 값
MARKETS = {
    "0000000001": "aT화훼(양재)",
    "1508500020": "부산화훼(엄궁)",
    "6068207466": "부경화훼(강동)",
    "4108212335": "광주원예(풍암)",
    "3848200087": "한국화훼(음성)",
    "7368200686": "한국화훼(고양)",
    "6158209828": "영남화훼(김해)",
}

# 1차 비치헤드 — 양재
PRIMARY_MARKET = "0000000001"

# 부류 코드 (메인 페이지 셀렉트 기준)
CATEGORY_CODES = {
    "1": "절화",   # 월~토 (주 6일)
    "2": "관엽",   # 화·금 (주 2일)
    "3": "난",     # 월·목 (주 2일)
}

# 경매 운영 요일 (0=월 ... 6=일). aT 양재 기준.
#   절화: 월~토 / 난: 월·목 / 관엽: 화·금 / 일요일·공휴일 휴장
AUCTION_WEEKDAYS = {
    "절화": {0, 1, 2, 3, 4, 5},
    "난": {0, 3},
    "관엽": {1, 4},
}

# 본경매(가격 형성 기준) vs 온라인거래 요일 — 가격 형성 메커니즘이 상이.
#   PRD 9.4.2 / 부록 B 참조.
MAIN_AUCTION_WEEKDAYS = {0, 2, 4}      # 월·수·금 본경매
ONLINE_TRADE_WEEKDAYS = {1, 3, 5}      # 화·목·토 온라인거래

BASE_URL = "https://flower.at.or.kr"
MAIN_PAGE = f"{BASE_URL}/main/flowerMain.do"
SALE_DATE_JSON = f"{BASE_URL}/main/getSaleDate.json"      # POST searchCmpCd → 거래일 목록
SALE_DATA_JSON = f"{BASE_URL}/main/getSaleData.json"      # GET cmpCd, searchSaleDate → 상위 30건
EXCEL_DOWNLOAD = f"{BASE_URL}/excel/excelDownLoad.do"     # GET excelNm, saleDate, cmpCd → 전체 일자별 .xls

# 꽃장부 web

화원용 시세 비교 프론트엔드 (Vite + React). FastAPI 백엔드를 통해 Neon(Postgres)의
양재 화훼 경매 데이터를 실시간으로 그린다. Figma 디자인(꽃장부 MVP)을 코드로 옮긴 것.

## 화면
- **오늘 시세** — 즐겨찾기 품목 카드(본경매/온라인 + 지난주 대비), 매입가 입력 → 갭 즉시 비교
- **품목 상세** — 시세 현황(일/주/월/연 토글 막대그래프) + 거래량 + 산지(연동예정) + 상세정보

## 실행
```bash
# 1) 백엔드 먼저 (저장소 루트에서)
pip install -r requirements.txt
export DATABASE_URL='postgresql://...neon.../neondb?sslmode=require'
uvicorn api.main:app --reload          # http://localhost:8000/docs

# 2) 프론트 (web/ 에서)
cd web
cp .env.example .env                   # 필요 시 VITE_API_URL 수정
npm install
npm run dev                            # http://localhost:5173
```

데이터는 차트·카드 모두 백엔드(`/home`, `/items/{item}/trend`, `/compare`)를 통해
Neon에서 실시간으로 가져온다. 즐겨찾기 품목은 `src/components/TodayScreen.jsx` 의
`FAVS` 에서 조정.

## 연결 구조
```
React (web/) ──HTTP──> FastAPI (api/) ──psycopg──> Neon Postgres
                         /home, /trend, /compare      auction_price (228k행)
```

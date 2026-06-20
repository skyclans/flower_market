#!/usr/bin/env bash
# 꽃장부 로컬 실행 — 백엔드(FastAPI) + 프론트(Vite)를 한 번에 띄운다.
#   사용: ./run-local.sh   (Ctrl+C 로 둘 다 종료)
#   사전: repo 루트의 .env 에 DATABASE_URL 한 줄. (없으면 안내 후 템플릿 생성)
set -euo pipefail
cd "$(dirname "$0")"

PY="$(command -v python3 || command -v python || true)"
[ -z "$PY" ] && { echo "❌ python3 가 필요합니다 → brew install python"; exit 1; }
command -v npm >/dev/null || { echo "❌ npm 이 필요합니다 → brew install node"; exit 1; }

# --- DATABASE_URL (.env 에서) ---
if [ -f .env ]; then set -a; . ./.env; set +a; fi
if [ -z "${DATABASE_URL:-}" ]; then
  echo "❌ DATABASE_URL 이 없습니다."
  if [ ! -f .env ] && [ -f .env.example ]; then
    cp .env.example .env
    echo "   → .env 템플릿을 만들었습니다. 그 안 DATABASE_URL 값을 채우고 다시 실행하세요."
  else
    echo "   → repo 루트 .env 에 다음을 넣으세요:"
    echo "     DATABASE_URL=postgresql://...neon.../neondb?sslmode=require"
  fi
  exit 1
fi

# --- 백엔드 준비 ---
if [ ! -d .venv ]; then echo "🐍 venv 생성..."; "$PY" -m venv .venv; fi
# shellcheck disable=SC1091
. .venv/bin/activate
echo "📦 백엔드 의존성 확인..."
pip install -q -r requirements.txt

# --- 프론트 준비 ---
if [ ! -d web/node_modules ]; then
  echo "📦 프론트 의존성 설치 (처음 한 번)..."
  ( cd web && npm install )
fi

# --- 둘 다 실행 ---
BACK_PID=""
cleanup() {
  echo; echo "🛑 종료 중..."
  [ -n "$BACK_PID" ] && { pkill -P "$BACK_PID" 2>/dev/null || true; kill "$BACK_PID" 2>/dev/null || true; }
  pkill -f "uvicorn api.main:app" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "🚀 백엔드 시작 → http://localhost:8000"
uvicorn api.main:app --reload --port 8000 &
BACK_PID=$!

printf "⏳ 백엔드 준비 대기"
for _ in $(seq 1 40); do
  if curl -sf http://localhost:8000/health >/dev/null 2>&1; then echo " ✅"; break; fi
  printf "."; sleep 1
done

echo "🌸 프론트 시작 → http://localhost:5173  (브라우저에서 열기)"
echo "   (종료하려면 이 창에서 Ctrl+C)"
( cd web && npm run dev )

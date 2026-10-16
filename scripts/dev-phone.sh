#!/usr/bin/env bash
# 아이폰(Expo Go)으로 확인할 때 쓰는 개발 실행 스크립트.
# 같은 와이파이가 아니어도(LTE, 회사 와이파이) 동작하도록 cloudflared 터널 2개를 연다.
#
#   ./scripts/dev-phone.sh                                   내 Mac 서버로
#   ./scripts/dev-phone.sh --remote https://meongnyang.duckdns.org   실서버로 (Metro 터널만)
#
# 하는 일
#   1. Django: migrate 후 8000 포트로 실행
#   2. cloudflared 터널 2개: API(8000), Metro(8081) — 주소는 매번 바뀜
#   3. app/.env 의 EXPO_PUBLIC_API_URL 을 새 API 주소로 갱신 (다른 값은 유지)
#   4. Expo 실행 (Metro 터널 주소로 QR 생성)
# Ctrl+C 한 번이면 전부 같이 종료된다.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REMOTE=""
if [ "${1:-}" = "--remote" ]; then
  REMOTE="${2:?실서버 주소를 같이 적어 주세요. 예: --remote https://meongnyang.duckdns.org}"
  REMOTE="${REMOTE%/}"
fi
LOG_DIR="$ROOT/.dev-logs"
mkdir -p "$LOG_DIR"

PIDS=()
cleanup() {
  echo
  echo "▶ 종료 중..."
  for pid in "${PIDS[@]:-}"; do
    [ -n "$pid" ] && kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

need() {
  command -v "$1" >/dev/null 2>&1 || { echo "✗ '$1' 이(가) 필요해요. $2"; exit 1; }
}
need cloudflared "설치: brew install cloudflared"
need npx "Node.js를 설치해 주세요."
[ -f "$ROOT/server/.venv/bin/activate" ] || {
  echo "✗ server/.venv 가 없어요. README의 '서버 실행'을 먼저 해 주세요."; exit 1;
}
# 패키지가 없거나 package-lock.json이 바뀌었으면(새 패키지 추가) 설치
if [ ! -f "$ROOT/app/node_modules/.package-lock.json" ] || [ "$ROOT/app/package-lock.json" -nt "$ROOT/app/node_modules/.package-lock.json" ]; then
  echo "▶ app 패키지 설치"
  (cd "$ROOT/app" && npm install)
fi
# 서버 패키지도 requirements.txt가 바뀌었으면 설치
if [ "$ROOT/server/requirements.txt" -nt "$ROOT/server/.venv/.installed" ]; then
  echo "▶ server 패키지 설치"
  (cd "$ROOT/server" && .venv/bin/pip install -q -r requirements.txt && touch .venv/.installed)
fi

# 이전 실행에서 남은 프로세스 정리
pkill -f "cloudflared tunnel --url http://localhost:8000" 2>/dev/null || true
pkill -f "cloudflared tunnel --url http://localhost:8081" 2>/dev/null || true
pkill -f "manage.py runserver 0.0.0.0:8000" 2>/dev/null || true

if [ -z "$REMOTE" ]; then
# 1. Django
echo "▶ 서버 준비 (migrate)"
(
  cd "$ROOT/server"
  # shellcheck disable=SC1091
  source .venv/bin/activate
  python manage.py migrate --noinput >/dev/null
)
(
  cd "$ROOT/server"
  # shellcheck disable=SC1091
  source .venv/bin/activate
  # 터널 주소에서 오는 요청 허용 (server/.env 보다 우선)
  export ALLOWED_HOSTS="localhost,127.0.0.1,.trycloudflare.com"
  exec python manage.py runserver 0.0.0.0:8000
) >"$LOG_DIR/django.log" 2>&1 &
PIDS+=($!)
fi

# 2. 터널
start_tunnel() { # $1=포트 $2=로그 이름
  : >"$LOG_DIR/$2.log"
  cloudflared tunnel --url "http://localhost:$1" >"$LOG_DIR/$2.log" 2>&1 &
  PIDS+=($!)
}
wait_url() { # $1=로그 이름 → 주소 출력
  local url=""
  for _ in $(seq 1 60); do
    url=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG_DIR/$1.log" | head -1 || true)
    [ -n "$url" ] && { echo "$url"; return 0; }
    sleep 1
  done
  echo "✗ $1 터널 주소를 받지 못했어요. $LOG_DIR/$1.log 를 확인해 주세요." >&2
  return 1
}

echo "▶ 터널 여는 중 (10~20초)"
start_tunnel 8081 metro
if [ -n "$REMOTE" ]; then
  API_URL="$REMOTE"
else
  start_tunnel 8000 api
  API_URL=$(wait_url api)
fi
METRO_URL=$(wait_url metro)

# 새 터널은 실제로 열리기까지 몇 초 걸린다. API가 응답할 때까지 기다린다.
echo "▶ API 연결 확인: $API_URL"
for _ in $(seq 1 40); do
  code=$(curl -s -o /dev/null -w '%{http_code}' "$API_URL/healthz" || true)
  [ "$code" = "200" ] && break
  sleep 1
done
[ "${code:-}" = "200" ] || echo "⚠ API가 아직 응답하지 않아요 (마지막 응답: ${code:-없음}). $LOG_DIR/django.log 를 확인해 주세요."

# 3. 앱 설정: API 주소 줄만 바꾸고 나머지(카카오 키 등)는 그대로 둔다
ENV_FILE="$ROOT/app/.env"
touch "$ENV_FILE"
grep -v '^EXPO_PUBLIC_API_URL=' "$ENV_FILE" >"$ENV_FILE.tmp" || true
echo "EXPO_PUBLIC_API_URL=$API_URL" >>"$ENV_FILE.tmp"
mv "$ENV_FILE.tmp" "$ENV_FILE"

echo
echo "  API   : $API_URL   (아이폰 사파리에서 $API_URL/api/docs/ 로 확인 가능)"
echo "  Metro : $METRO_URL"
echo "  로그  : $LOG_DIR/"
echo
echo "▶ 아래 QR을 아이폰 카메라로 찍으세요. 안 열리면 Expo Go에서"
echo "  exps://${METRO_URL#https://} 를 직접 입력하세요."
echo

# 4. Expo (포그라운드)
cd "$ROOT/app"
# expo-dev-client가 설치돼 있어도 Expo Go로 열리게 --go
EXPO_PACKAGER_PROXY_URL="$METRO_URL" npx expo start -c --go

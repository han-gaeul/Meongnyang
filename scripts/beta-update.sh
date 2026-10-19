#!/usr/bin/env bash
# 지인 베타에 최신 앱(JS)을 올린다. Mac을 꺼 둬도 지인은 Expo Go에서 바로 연다.
#
#   ./scripts/beta-update.sh "바뀐 내용 한 줄"
#
# - 실서버(meongnyang.duckdns.org)를 보도록 고정해서 올린다. app/.env의 터널 주소는 무시된다.
# - 카카오맵 키 등 나머지 EXPO_PUBLIC_ 값은 app/.env에서 가져온다.
# - 네이티브 패키지를 새로 추가한 경우에도 Expo Go(SDK 57)에 들어 있는 패키지라면 그대로 동작한다.
# 지인 안내 페이지: https://meongnyang.duckdns.org/beta

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MESSAGE="${1:-베타 업데이트}"
API_URL="https://meongnyang.duckdns.org"

if [ -n "$(git -C "$ROOT" status --porcelain -- app)" ]; then
  echo "⚠ app 폴더에 커밋하지 않은 변경이 있어요. 그대로 올라가니 확인해 주세요."
fi

echo "▶ 서버 확인: $API_URL/healthz"
curl -fsS "$API_URL/healthz" >/dev/null || { echo "✗ 서버가 응답하지 않아요. 업로드를 멈춥니다."; exit 1; }

cd "$ROOT/app"
[ -d node_modules ] || npm install

echo "▶ 업로드 (1~2분)"
EXPO_PUBLIC_API_URL="$API_URL" npx eas-cli@latest update \
  --channel beta \
  --environment preview \
  --message "$MESSAGE" \
  --platform all

echo
echo "✓ 올렸어요. 지인은 앱을 완전히 껐다가 다시 열면 새 버전이 보여요."
echo "  안내 페이지: $API_URL/beta"

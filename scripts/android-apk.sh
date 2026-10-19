#!/usr/bin/env bash
# 안드로이드 지인 배포용 APK를 EAS에서 빌드한다 (무료, 15~30분).
#
#   ./scripts/android-apk.sh
#
# - 실서버(meongnyang.duckdns.org)를 보고, beta 채널 업데이트를 받는다.
#   이후 JS만 바뀐 건 ./scripts/beta-update.sh 로 올리면 APK를 다시 깔 필요가 없다.
# - 카카오맵 키는 app/.env의 값을 EAS 환경변수(preview)로 한 번 등록해 둔다.
# - 빌드가 끝나면 설치 링크(QR)가 나온다. 그 링크를 지인에게 보내면 된다.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/app"
[ -d node_modules ] || npm install

KAKAO_KEY=$(grep -E '^EXPO_PUBLIC_KAKAO_JS_KEY=' .env 2>/dev/null | cut -d= -f2- || true)
if [ -n "$KAKAO_KEY" ]; then
  if ! npx eas-cli@latest env:list --environment preview 2>/dev/null | grep -q EXPO_PUBLIC_KAKAO_JS_KEY; then
    echo "▶ 카카오맵 키를 EAS(preview)에 등록"
    npx eas-cli@latest env:create --name EXPO_PUBLIC_KAKAO_JS_KEY --value "$KAKAO_KEY" \
      --environment preview --visibility plaintext --non-interactive
  fi
else
  echo "⚠ app/.env에 EXPO_PUBLIC_KAKAO_JS_KEY가 없어요. 지도 없이 목록만 보여요."
fi

echo "▶ APK 빌드 요청 (EAS 클라우드, 무료 대기열이라 15~30분 걸릴 수 있어요)"
npx eas-cli@latest build --platform android --profile preview

/**
 * API 서버 주소. app/.env 의 EXPO_PUBLIC_API_URL 로 바꾼다.
 * 안드로이드 에뮬레이터에서 내 PC의 localhost는 10.0.2.2 이다.
 * 실기기에서는 PC의 사설 IP(예: http://192.168.0.10:8000)를 넣는다.
 */
export const API_URL = (process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');

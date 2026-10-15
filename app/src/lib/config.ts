/**
 * API 서버 주소. app/.env 의 EXPO_PUBLIC_API_URL 로 바꾼다.
 * 안드로이드 에뮬레이터에서 내 PC의 localhost는 10.0.2.2 이다.
 * 실기기에서는 PC의 사설 IP(예: http://192.168.0.10:8000)를 넣는다.
 */
export const API_URL = (process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');

/**
 * 카카오맵 JavaScript 키 (developers.kakao.com → 내 애플리케이션 → 앱 키).
 * 없으면 지도 대신 목록만 보여준다. JavaScript 키는 앱에 들어가도 되는 공개 키다.
 */
export const KAKAO_JS_KEY = process.env.EXPO_PUBLIC_KAKAO_JS_KEY ?? '';

/**
 * 지도 WebView가 이 주소에서 열린 것처럼 동작한다.
 * 카카오 개발자 콘솔 → 플랫폼 → Web 사이트 도메인에 같은 주소를 등록해야 지도가 뜬다.
 */
export const KAKAO_MAP_ORIGIN = process.env.EXPO_PUBLIC_KAKAO_MAP_ORIGIN ?? 'https://meongnyang.app';

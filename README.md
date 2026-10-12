# 멍냥동네

신원이 확인된 동네 반려인끼리, 금전 없이 서로의 반려동물을 봐주는 앱.

```
server/   Django 5.2 + DRF API 서버
app/      React Native (Expo SDK 57) 앱
```

## 지금 들어 있는 것

| 영역 | 내용 |
| --- | --- |
| 인증 | 이메일 가입·로그인(JWT, refresh 회전·폐기), 소셜 로그인 토큰 검증(카카오·네이버·구글, 애플은 TODO) |
| 본인인증 | 대행사 연동 인터페이스 + 개발용 mock. CI는 HMAC 해시로만 저장, 1인 1계정 |
| 반려동물 | 등록·수정·삭제, 등록번호 인증(등록정보 조회 인터페이스 + mock) |
| 권한 | 모든 API 로그인 필수, 수정·삭제는 작성자만(`IsOwnerOrReadOnly`), 인증 회원 전용(`IsVerifiedMember`) |
| 커뮤니티 | 글·댓글·좋아요·태그·검색·종 필터, 사진 최대 5장(서버에서 JPEG 변환·위치정보 제거) |
| 신고·운영 | 글·댓글 신고, 서로 다른 3명이 신고하면 자동 숨김 → /admin에서 복구·제재. 차단한 사람 글은 서로 안 보임 |
| 둘러보기 | 인증 전에도 피드·글 읽기 가능, 쓰기·좋아요·댓글·신고·업로드는 인증 회원만 |
| 앱 | 로그인·가입, 홈(피드·글 상세·글쓰기), 마이(본인인증·반려동물 등록·인증), 나머지 탭은 자리만 |
| CI | 서버 테스트·마이그레이션·OpenAPI 검증, 앱 타입체크·린트 |

## 서버 실행

```bash
cd server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser   # 운영자 검토용 /admin
python manage.py runserver 0.0.0.0:8000
pytest                             # 테스트
```

- API 문서: http://localhost:8000/api/docs/
- 운영자 화면: http://localhost:8000/admin/ (반려동물 "검토 대기" 필터)

## 앱 실행

```bash
cd app
npm install
cp .env.example .env   # EXPO_PUBLIC_API_URL을 서버 주소로
npx expo start
```

- 안드로이드 에뮬레이터는 `http://10.0.2.2:8000`, 실기기는 PC의 사설 IP를 쓴다.
- 패키지는 `npx expo install <패키지>`로 추가한다(SDK 호환 버전 자동 선택).
- 보안 저장소 등 네이티브 모듈이 있어 실기기 테스트는 개발 빌드(`npx expo run:android` 또는 EAS)가 필요할 수 있다.

## 개발용 mock 규칙

| 대상 | 입력 | 결과 |
| --- | --- | --- |
| 본인인증 | `mock-ok-<사람>` (뒤에 `:아무값` 가능) | 성공. 같은 `<사람>`은 같은 CI로 취급 |
| 본인인증 | 그 외 | 실패 |
| 등록번호 | `0`으로 시작 | 조회 안 됨 → 운영자 검토 대기 |
| 등록번호 | `9`로 시작 | 소유자 불일치 → 인증 실패 |
| 등록번호 | 그 외 15자리 | 인증 완료 |

`DEBUG=False`에서 mock 제공자를 쓰면 서버가 시작되지 않는다.

## 계약 후 채울 곳

- `server/accounts/identity.py` → `PortOneIdentityProvider`
- `server/pets/registry.py` → `CoconPetRegistry`
- `server/accounts/social.py` → `verify_apple`
- 앱 소셜 로그인 버튼(각 SDK), 본인인증 창

## 다음 단계

설계 문서의 개발 단계 순서: 산책·나눔 모임과 만남 인증 → 부탁(돌봄 시트) → 장소 DB·카카오맵 → 일기(GPS 산책).

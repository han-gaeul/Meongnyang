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
| 모임 | 산책·나눔 모임 열기, 참여 신청 → 모임장 수락·거절, 정원 차면 자동 마감·취소 시 다시 모집 |
| 만남 인증 | QR(3분 유효, 서명) + 두 기기 200m 이내 확인, 같은 두 사람 하루 1회. 좌표는 저장 안 함 |
| 이웃 | 만남 1회 = 이웃, 만남 3회 + 짧은 부탁 1회 완료 = 단골 이웃. 동네는 현재 위치로 설정 |
| 부탁 | 만난 이웃에게만 보이는 짧은 부탁(2시간 이내). 돌봄 시트 초안 자동 작성, 상세 시트는 맡은 이웃에게만. 작성·신청 시 책임 범위 동의, 수락 → 완료 확인 → 감사 후기. 집 방문 부탁은 단골 이웃만 |
| 장소 | 자체 장소 DB, 반경 검색·거리순. 동반 조건(크기·체중·공간·바닥·요금·편의) 구조화, 내 반려동물 기준 OK/어려움 표시와 필터(대형견·실내·바닥·추가요금 없음·24시). 30초 후기(함께 간 반려동물 크기·체중 자동, 근처 작성 시 방문 확인), 최신 후기가 정책보다 우선. 장소 제보 → 운영자 승인. 카카오맵 길찾기, 네이버 예약 링크 |
| 둘러보기 | 인증 전에도 피드·글 읽기 가능, 쓰기·좋아요·댓글·신고·업로드는 인증 회원만 |
| 앱 | 로그인·가입, 홈(커뮤니티), 모임·부탁(목록·상세·만들기·신청 관리, 돌봄 시트), 만남 인증(QR 보여주기·찍기), 이웃 목록, 마이(동네·본인인증·반려동물). 지도(카카오맵 WebView, 키가 없으면 목록), 일기 탭은 자리만 |
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

### 아이폰(Expo Go)으로 확인하기

```bash
brew install cloudflared
./scripts/dev-phone.sh
```

서버 migrate·실행, 터널 2개(API·Metro), `app/.env` 갱신, Expo 실행을 한 번에 한다. 같은 와이파이가 아니어도 된다. 터널 주소는 실행할 때마다 바뀌므로 매번 새로 뜬 QR을 찍는다. Ctrl+C 한 번이면 전부 종료되고, 로그는 `.dev-logs/`에 남는다.

### 카카오맵 키

1. developers.kakao.com → 내 애플리케이션 → 앱 만들기 → **JavaScript 키** 복사
2. 앱 설정 → 플랫폼 → Web → 사이트 도메인에 `https://meongnyang.app` 등록 (`EXPO_PUBLIC_KAKAO_MAP_ORIGIN`과 같아야 함)
3. 제품 설정 → 카카오맵 사용 설정 ON
4. `app/.env`에 `EXPO_PUBLIC_KAKAO_JS_KEY=복사한 키` 추가 (`dev-phone.sh`는 이 줄을 건드리지 않음)

키가 없으면 지도 없이 거리순 목록만 보인다.

### 샘플 장소

```bash
cd server
DEBUG=True python manage.py seed_dev_places --lat 37.5556 --lng 126.9019
```

좌표 주변에 `[샘플]` 장소 8곳을 만든다. 아이폰으로 볼 땐 내 위치 좌표를 넣는다. `--clear`로 지우고 다시 만든다.

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

설계 문서의 개발 단계 순서: 일기(GPS 산책, 건강 일기 → 돌봄 시트 자동 채우기) → 쪽지·푸시.

- 장소 공공데이터 수집(인허가·TourAPI)은 API 키 발급 후 `places`에 배치 명령으로 추가
- 반경 검색은 좌표 계산(`places/services.py`), 데이터가 늘면 PostGIS로 교체

- 돌봄 시트의 일기 연동 지점: `server/favors/services.py`의 `_journal_items`
- 부탁 약속(책임 범위) 문구는 초안: `app/src/lib/favor-terms.ts`, 출시 전 법률 검토 필요

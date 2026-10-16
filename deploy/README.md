# 서버 배포 (AWS)

EC2 한 대에 API(gunicorn)와 Caddy(HTTPS 자동 발급)를 Docker로 띄우고, DB는 RDS PostgreSQL, 사진은 S3에 둔다.

```
아이폰 앱 ──HTTPS──▶ EC2 [Caddy :443 → api :8000] ──▶ RDS PostgreSQL
                                         └──────────▶ S3 (사진)
```

리전은 모두 **서울(ap-northeast-2)**.

## 1. S3 버킷 (사진)

1. S3 → 버킷 만들기: 이름 `meongnyang-media`(전역에서 유일해야 하니 겹치면 뒤에 숫자), 리전 서울
2. 객체 소유권: **ACL 비활성화**(기본값)
3. 퍼블릭 액세스 차단: **"새 퍼블릭 버킷 정책" 관련 두 항목만 해제**하고 나머지(ACL 관련)는 그대로 둔다
4. 권한 → 버킷 정책에 아래를 붙인다 (`media/` 아래 사진만 공개 읽기)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadMedia",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::meongnyang-media/media/*"
    }
  ]
}
```

서버가 업로드할 때 위치정보(EXIF)를 지우고 JPEG로 바꿔서 올리므로 원본 메타데이터는 남지 않는다.

## 2. IAM 역할 (EC2 → S3)

키를 서버에 넣지 않도록 EC2에 역할을 붙인다.

1. IAM → 역할 만들기 → 신뢰할 엔터티 **AWS 서비스 / EC2**
2. 권한 → 인라인 정책 (JSON):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::meongnyang-media/media/*"
    }
  ]
}
```

3. 역할 이름 `meongnyang-ec2`

## 3. 보안 그룹

| 이름 | 인바운드 |
| --- | --- |
| `meongnyang-web` (EC2) | 80, 443: 어디서나 / 22: **내 IP만** |
| `meongnyang-db` (RDS) | 5432: 소스 = `meongnyang-web` 보안 그룹 |

## 4. RDS PostgreSQL

1. RDS → 데이터베이스 생성 → **PostgreSQL**, 템플릿 **프리 티어**(가능하면)
2. DB 인스턴스 식별자 `meongnyang`, 마스터 사용자 `meongnyang`, 비밀번호는 따로 보관
3. 퍼블릭 액세스 **아니요**, 보안 그룹 `meongnyang-db`
4. 추가 구성 → 초기 데이터베이스 이름 `meongnyang`
5. 자동 백업 켜 둠 (기본 7일)

만들어지면 **엔드포인트**를 복사해 둔다.

## 5. EC2

1. 인스턴스 시작: Ubuntu 24.04, `t3.small` 이상(메모리 2GB 권장), 보안 그룹 `meongnyang-web`, IAM 역할 `meongnyang-ec2`
2. **탄력적 IP**를 할당해 인스턴스에 연결 (재시작해도 주소 유지)
3. DuckDNS에서 도메인(예: `meongnyang.duckdns.org`)을 탄력적 IP로 연결

접속해서 Docker 설치:

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2 git
sudo usermod -aG docker $USER
```

로그아웃했다가 다시 접속한 뒤:

```bash
git clone https://github.com/han-gaeul/Meongnyang.git
cd Meongnyang/deploy
cp .env.prod.example .env.prod
nano .env.prod
```

`.env.prod`에 채울 것:

- `DOMAIN`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`: DuckDNS 도메인
- `SECRET_KEY`, `CI_HASH_SECRET`: 각각 아래로 새로 만든 값
  ```bash
  python3 -c "import secrets; print(secrets.token_urlsafe(50))"
  ```
  **`CI_HASH_SECRET`은 한 번 정하면 바꾸지 않는다.** 바꾸면 기존 회원의 본인인증 중복 확인이 깨진다.
- `DATABASE_URL`: RDS 엔드포인트와 비밀번호
- `AWS_STORAGE_BUCKET_NAME`: 1번에서 만든 버킷 이름
- `BETA_INVITE_CODE`: 지인에게 알려 줄 초대 코드 (8자 이상)

실행:

```bash
docker compose up -d --build
docker compose logs -f api
```

`https://도메인/healthz`가 `{"ok": true}`면 성공. 처음 접속하면 Caddy가 인증서를 받느라 몇 초 걸린다.

운영자 계정:

```bash
docker compose exec api python manage.py createsuperuser
```

`https://도메인/admin/`에서 장소 제보 승인, 신고 검토, 반려동물 수동 검토를 한다.

## 업데이트

```bash
cd ~/Meongnyang
git pull
cd deploy
docker compose up -d --build
```

마이그레이션은 컨테이너가 시작할 때 자동으로 돈다.

## 지인 베타 주의

- 지금은 본인인증·등록번호 조회가 **mock**이다. `mock-ok-아무거나`로 누구나 인증된다. 그래서 초대 코드(`BETA_INVITE_CODE`)를 아는 사람만 가입할 수 있게 막아 두었다.
- 앱스토어 공개 출시 전에 포트원·쿠콘을 연동하고 `ALLOW_MOCK_PROVIDERS=False`로 바꾼다. 그 상태에서 mock이 남아 있으면 서버가 시작되지 않는다.
- 비용: 계정이 프리 티어 대상이면 1년간 EC2·RDS 작은 인스턴스가 대부분 무료다. 아니면 AWS 요금 계산기로 미리 확인한다. 탄력적 IP는 인스턴스에 연결해 두지 않으면 과금된다.

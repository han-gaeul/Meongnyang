from datetime import timedelta
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    IDENTITY_PROVIDER=(str, "mock"),
    PET_REGISTRY_PROVIDER=(str, "mock"),
    GOOGLE_CLIENT_IDS=(list, []),
)
environ.Env.read_env(BASE_DIR / ".env")

DEBUG = env("DEBUG")
# 키는 코드에 두지 않는다. 로컬은 .env, 배포는 환경변수/Secrets Manager.
SECRET_KEY = env("SECRET_KEY")
CI_HASH_SECRET = env("CI_HASH_SECRET")
# 컨테이너 헬스체크(127.0.0.1:8000/healthz)는 항상 허용
ALLOWED_HOSTS = [*env("ALLOWED_HOSTS"), "127.0.0.1", "localhost"]

IDENTITY_PROVIDER = env("IDENTITY_PROVIDER")
PET_REGISTRY_PROVIDER = env("PET_REGISTRY_PROVIDER")
GOOGLE_CLIENT_IDS = env("GOOGLE_CLIENT_IDS")

# 지인 베타: 본인인증·등록번호 조회 계약 전에 mock으로 운영한다.
# 이때는 초대 코드가 있어야 가입할 수 있다. 공개 출시 전에 반드시 끈다.
ALLOW_MOCK_PROVIDERS = env.bool("ALLOW_MOCK_PROVIDERS", default=False)
BETA_INVITE_CODE = env.str("BETA_INVITE_CODE", default="")
if not DEBUG and "mock" in (IDENTITY_PROVIDER, PET_REGISTRY_PROVIDER):
    if not ALLOW_MOCK_PROVIDERS:
        raise ImproperlyConfigured("배포 환경에서는 mock 인증 제공자를 쓸 수 없습니다.")
    if len(BETA_INVITE_CODE) < 8:
        raise ImproperlyConfigured("mock 베타는 8자 이상 BETA_INVITE_CODE가 있어야 합니다(초대한 사람만 가입).")
# 초대 코드가 있으면 가입할 때 확인한다 (mock 베타가 아니어도 비공개 운영에 쓸 수 있음)
INVITE_REQUIRED = bool(BETA_INVITE_CODE)
# 지인 베타 안내 페이지(/beta)에서 Expo Go로 여는 링크. EAS Update 채널을 가리킨다.
EXPO_PROJECT_ID = env.str("EXPO_PROJECT_ID", default="b8bcdae6-6579-450b-806d-7adeb4d72d33")
EXPO_UPDATE_CHANNEL = env.str("EXPO_UPDATE_CHANNEL", default="beta")
EXPO_RUNTIME_VERSION = env.str("EXPO_RUNTIME_VERSION", default="exposdk:57.0.0")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "accounts",
    "pets",
    "uploads",
    "moderation",
    "community",
    "gatherings",
    "meetups",
    "favors",
    "places",
    "journal",
    "notifications",
    "inbox",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": env.db_url_config(
        env.str("DATABASE_URL", default="") or f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
    )
}

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# 업로드 파일: 로컬은 server/media, 배포는 S3 (AWS_STORAGE_BUCKET_NAME이 있으면)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
AWS_STORAGE_BUCKET_NAME = env.str("AWS_STORAGE_BUCKET_NAME", default="")
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
if AWS_STORAGE_BUCKET_NAME:
    STORAGES["default"] = {"BACKEND": "storages.backends.s3.S3Storage"}
    AWS_S3_REGION_NAME = env.str("AWS_S3_REGION_NAME", default="ap-northeast-2")
    AWS_LOCATION = "media"
    AWS_DEFAULT_ACL = None  # 버킷 정책으로 관리
    AWS_QUERYSTRING_AUTH = False  # 공개 이미지. 민감 파일은 별도 버킷·서명 URL로

# 서로 다른 사람의 신고가 이 수에 도달하면 자동 숨김
REPORT_HIDE_THRESHOLD = env.int("REPORT_HIDE_THRESHOLD", default=3)

# 푸시: 운영에서만 켠다 (Expo 푸시 서버로 전송)
PUSH_ENABLED = env.bool("PUSH_ENABLED", default=False)

# 만남 인증: QR 유효 시간(초), 두 기기 사이 허용 거리(m)
MEETUP_TOKEN_TTL = 180
MEETUP_MAX_DISTANCE_M = 200
# 이웃 단계: 만남 횟수 기준 (설계 문서 초안 값)
NEIGHBOR_MEETS = 1
REGULAR_NEIGHBOR_MEETS = 3
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    # 로그인이 기본. 예외(가입·로그인)만 뷰에서 AllowAny.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "common.pagination.DefaultCursorPagination",
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.ScopedRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"auth": "20/min", "verify": "10/hour", "upload": "60/hour", "meetup": "60/hour", "message": "120/hour"},
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "멍냥동네 API",
    "VERSION": "0.1.0",
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "PetSpeciesEnum": "pets.models.Pet.Species",
        "AudienceSpeciesEnum": "community.models.Post.Species",  # 글·모임 공통: 모두/강아지/고양이
        "FavorStatusEnum": "favors.models.Favor.Status",
        "FavorKindEnum": "favors.models.Favor.Kind",
        "PlaceCategoryEnum": "places.models.Place.Category",
        "PlaceSpaceEnum": "places.models.Place.Space",
        "PlaceStatusEnum": "places.models.Place.Status",
        "JournalKindEnum": "journal.models.JournalEntry.Kind",
        "GatheringKindEnum": "gatherings.models.Gathering.Kind",
        "GatheringStatusEnum": "gatherings.models.Gathering.Status",
        "ApplicationStatusEnum": "gatherings.models.Participation.Status",
    },
}

# 배포: 리버스 프록시(Caddy) 뒤에서 HTTPS로만
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": env.str("LOG_LEVEL", default="INFO")},
    "loggers": {"django.db.backends": {"level": "WARNING"}},
}

if not DEBUG:
    # /admin 화면용 정적 파일은 앱 서버가 직접 낸다 (collectstatic 필요)
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
    STORAGES["staticfiles"] = {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    # 헬스체크는 프록시를 거치지 않고 http로 직접 부른다
    SECURE_REDIRECT_EXEMPT = [r"^healthz$"]
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 30)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False  # DuckDNS 같은 공유 도메인일 수 있어 하위 도메인은 건드리지 않는다
    SECURE_CONTENT_TYPE_NOSNIFF = True
    # 하위 도메인 HSTS·preload 목록 등록은 자체 도메인을 정한 뒤 판단 (공유 도메인에서는 켜면 안 됨)
    SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W021"]
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

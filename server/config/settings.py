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
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

IDENTITY_PROVIDER = env("IDENTITY_PROVIDER")
PET_REGISTRY_PROVIDER = env("PET_REGISTRY_PROVIDER")
GOOGLE_CLIENT_IDS = env("GOOGLE_CLIENT_IDS")

if not DEBUG and "mock" in (IDENTITY_PROVIDER, PET_REGISTRY_PROVIDER):
    raise ImproperlyConfigured("배포 환경에서는 mock 인증 제공자를 쓸 수 없습니다.")

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
        "DIRS": [],
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
    "DEFAULT_THROTTLE_RATES": {"auth": "20/min", "verify": "10/hour", "upload": "60/hour"},
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
}

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

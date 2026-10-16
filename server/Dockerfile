# 멍냥동네 API 서버
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# 정적 파일(/admin 화면)은 이미지에 미리 모아 둔다. 빌드할 때만 쓰는 임시 키.
RUN DEBUG=True SECRET_KEY=build-only-not-secret-0123456789abcdefghijklmn \
    CI_HASH_SECRET=build-only-not-secret-0123456789abcdefghijk \
    python manage.py collectstatic --noinput

RUN useradd --create-home app && chown -R app /app
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz').status==200 else 1)"

# 시작할 때 마이그레이션 후 gunicorn (EC2 한 대 기준 워커 3개)
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-3} --timeout 60 --access-logfile -"]

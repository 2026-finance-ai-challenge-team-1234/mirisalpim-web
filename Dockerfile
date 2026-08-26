FROM node:22-alpine AS frontend-builder

WORKDIR /build/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Keep the monorepo layout in the image. Django resolves ai_core and scenario
# seeds relative to /app, just as it does from a local checkout.
COPY backend/ ./backend/
COPY ai_core/ ./ai_core/
COPY data/ ./data/
COPY --from=frontend-builder /build/frontend/dist ./backend/frontend_dist

WORKDIR /app/backend

# These build-only commands do not read or write the application database.
# Production SECRET_KEY and DATABASE_URL are supplied only at container runtime.
RUN SECRET_KEY=build-only-not-for-runtime \
    DATABASE_URL=postgresql://build:build@invalid/build \
    python manage.py seed_scenarios --check
RUN SECRET_KEY=build-only-not-for-runtime \
    DATABASE_URL=postgresql://build:build@invalid/build \
    python manage.py collectstatic --noinput

# 시나리오 적재는 기동할 때마다 한다 (update_or_create 라 멱등하다). 빌드 단계의
# seed_scenarios --check 는 검증만 하고 DB 를 건드리지 않으므로, 이 줄이 없으면
# 배포 DB 의 Scenario 테이블이 비어 있고 훈련이 시작조차 되지 않는다.
#
# ⚠️ seed 실패가 기동을 막지 않게 한다. 진행됐던 세션의 Turn 이 Stage 를 PROTECT 로
# 참조하고 있으면 seed_scenarios 가 단계를 교체하지 못하고 CommandError 를 낸다.
# 그때 서비스 전체가 못 뜨는 것보다 기존 시나리오로 뜨는 편이 낫다.
CMD ["/bin/sh", "-c", "python manage.py migrate --noinput && { python manage.py seed_scenarios || echo 'WARNING: seed_scenarios 실패 - 기존 적재분으로 기동합니다'; } && exec uvicorn config.asgi:application --host 0.0.0.0 --port ${PORT:-8000}"]

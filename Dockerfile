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

CMD ["/bin/sh", "-c", "python manage.py migrate --noinput && exec uvicorn config.asgi:application --host 0.0.0.0 --port ${PORT:-8000}"]

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

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=frontend-builder /build/frontend/dist ./frontend_dist

# Django must initialize during the image build, but the production secret must
# only be supplied to the running container.
RUN SECRET_KEY=collectstatic-build-only-key python manage.py collectstatic --noinput

CMD ["/bin/sh", "-c", "python manage.py migrate --noinput && exec uvicorn config.asgi:application --host 0.0.0.0 --port ${PORT:-8000}"]

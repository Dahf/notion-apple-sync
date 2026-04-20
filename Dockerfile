ARG TAILWIND_VERSION=v3.4.17

# ---- CSS build stage --------------------------------------------------------
FROM debian:bookworm-slim AS css-builder
ARG TAILWIND_VERSION
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build
RUN curl -sSL -o tailwindcss "https://github.com/tailwindlabs/tailwindcss/releases/download/${TAILWIND_VERSION}/tailwindcss-linux-x64" \
    && chmod +x tailwindcss
COPY tailwind.config.js ./
COPY app/static/css/tailwind.src.css ./src.css
COPY app/templates ./app/templates
RUN ./tailwindcss \
    -c ./tailwind.config.js \
    -i ./src.css \
    -o ./app.css \
    --minify

# ---- Runtime stage ----------------------------------------------------------
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_URL=sqlite:////app/config/app.db

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Built CSS replaces any committed one
COPY --from=css-builder /build/app.css ./app/static/css/app.css

RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/config \
    && chown -R appuser:appuser /app

EXPOSE 8080

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

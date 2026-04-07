## Stage 1: Build the React UI
FROM node:22-slim AS ui-build

WORKDIR /ui
COPY ui/package.json ui/package-lock.json ./
RUN npm ci
COPY ui/ .
RUN npm run build

## Stage 2: Python API + static UI
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libjpeg62-turbo zlib1g libwebp7 libzbar0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY schema.sql .
COPY config/ config/
COPY src/ src/
COPY scripts/ scripts/
RUN chmod +x scripts/entrypoint.sh

# Copy built UI into /app/static
COPY --from=ui-build /ui/dist static/

RUN mkdir -p data/images

EXPOSE 8300

CMD ["scripts/entrypoint.sh"]

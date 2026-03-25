# Deploy Guide

## Overview

Global Market Newsboard can be deployed in three practical ways:

- local development with `uvicorn`
- Docker on a VPS
- reverse-proxied public deployment with Nginx or a cloud edge

The easiest public deployment path is:

1. provision a small Linux VPS
2. install Docker and Docker Compose
3. clone the repo
4. copy `.env.example` to `.env`
5. run `docker compose up --build -d`
6. put Nginx or Caddy in front for HTTPS

## Environment

Copy:

```bash
cp .env.example .env
```

Typical edits:

```bash
PORT=8010
MARKET_STREAM_POLL_INTERVAL_SECONDS=60
MARKET_STREAM_MAX_STORED_ITEMS=100000
MARKET_STREAM_DB_PATH=data/market_stream.db
MARKET_STREAM_CLASSIFIER_MODE=heuristic
```

## Docker Deployment

```bash
docker compose up --build -d
```

Check:

```bash
curl http://127.0.0.1:8010/health
```

Stop:

```bash
docker compose down
```

## Reverse Proxy Example

Use Nginx in front of the app if you want a public domain and HTTPS.

Minimal upstream shape:

```nginx
server {
    listen 80;
    server_name your-domain.example;

    location / {
        proxy_pass http://127.0.0.1:8010;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        proxy_buffering off;
    }
}
```

If you use HTTPS, terminate TLS at Nginx or your cloud edge.

## Persistence

By default, the SQLite database lives under `data/market_stream.db`.

For Docker, that path is mounted from the host:

- `./data:/app/data`

Back this directory up if you care about history retention.

## Operational Notes

- Polling public sources too aggressively is unnecessary and increases breakage risk.
- Keep the default `60` second poll unless you have a specific reason to lower it.
- Some public mover pages may return `403`; the app already falls back to internal mover extraction logic.
- If you expose the app publicly, review all upstream source terms and branding rules.

## GitHub Launch Checklist

- add repo description
- add topics like `fastapi`, `market-data`, `news-aggregator`, `trading`, `finance`
- pin a good dashboard screenshot
- keep `README.md` and screenshots current
- make sure `data/` and `logs/` are not committed

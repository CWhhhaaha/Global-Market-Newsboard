# Global Market Newsboard

[![License: Apache-2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688)
![SQLite](https://img.shields.io/badge/storage-SQLite-0f6ab4)
![Docker Ready](https://img.shields.io/badge/deploy-Docker%20Ready-2496ed)

A retail-first global macro and stock catalyst board that surfaces the headlines most likely to move indices, megacaps, sentiment, and risk in real time, using public sources instead of a terminal subscription.

## Live Website

- Public entry: [https://www.globalnewsboard.cn](https://www.globalnewsboard.cn)
- Source code: [https://github.com/CWhhhaaha/Global-Market-Newsboard](https://github.com/CWhhhaaha/Global-Market-Newsboard)

Global Market Newsboard tracks public market-moving headlines, official releases, filings, and event calendars, then turns them into a live trader-facing board with:

- real-time stream updates
- `Now Moving` market buckets
- `Trader Focus` modules
- search and historical replay
- multilingual UI
- lightweight heuristic classification

The project is built for people who want a Bloomberg-style market monitor using public sources and a simple deployment path.

## Screenshots

<img width="1648" height="987" alt="截屏2026-03-26 下午10 32 45" src="https://github.com/user-attachments/assets/064b7f10-8ca6-4a00-9dc8-9ef9bd709e25" />


## Demo Video

[Watch the demo video](docs/social/global-market-newsboard-demo.mp4)

## Architecture

```mermaid
flowchart LR
    A["Public news feeds<br/>media, official agencies, SEC, CME, NVIDIA"] --> B["Fetcher layer<br/>RSS + HTML parsers"]
    B --> C["Filtering layer<br/>market keywords + source rules"]
    C --> D["Classification layer<br/>heuristic labels and targets"]
    D --> E["Deduplication layer<br/>same-entry + similar-title window"]
    E --> F["Storage<br/>SQLite history"]
    F --> G["Pipeline service<br/>snapshot + SSE"]
    G --> H["FastAPI API"]
    H --> I["Web UI<br/>Main Stream / Now Moving / Trader Focus"]
    H --> J["JSON + SSE consumers"]
    F --> K["Search / replay / pagination"]
    B --> L["Upcoming events collector"]
    L --> H
```

## Why This Project

- Focused on what traders scan first: Fed, macro, megacaps, China, Trump, Jensen Huang, Musk, bonds, FX, metals, oil
- Uses public feeds and official sources instead of closed terminals
- Keeps source links visible to avoid black-box aggregation
- Runs locally with SQLite, but can also be exposed publicly through a reverse proxy or Cloudflare Tunnel

## Current Feature Set

- Real-time SSE stream for new headlines
- Multi-source polling across media, official agencies, central banks, SEC filings, CME, NVIDIA, and more
- Lightweight cross-source deduplication
- Historical storage with local retention control
- Keyword search, pagination, and date filtering
- `Now Moving` buckets:
  - macro
  - stocks
  - geopolitics
- `Trader Focus` modules:
  - market drivers
  - bonds and rates
  - dollar and FX
  - precious metals
  - China watch
  - Trump watch
  - Jensen Huang
  - Elon Musk
  - hot stocks
  - earnings and guidance
  - policy and regulation
  - war and oil
- UI language switching:
  - Simplified Chinese
  - English
  - Traditional Chinese
  - Japanese
  - Korean
  - Spanish
  - French

## Stack

- `FastAPI`
- `Uvicorn`
- `httpx`
- `feedparser`
- `SQLite`
- plain HTML/CSS/JS frontend

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.market_stream.app:app --host 127.0.0.1 --port 8010 --reload
```

Open:

- `http://127.0.0.1:8010/`
- `http://127.0.0.1:8010/health`
- `http://127.0.0.1:8010/api/items`
- `http://127.0.0.1:8010/api/search?q=fed`
- `http://127.0.0.1:8010/api/dashboard`
- `http://127.0.0.1:8010/stream`

## Docker

```bash
cp .env.example .env
docker compose up --build
```

Then open:

- `http://127.0.0.1:8010/`

Persistent data is stored in the mounted `./data` directory.

## Configuration

Set these environment variables if needed:

- `MARKET_STREAM_POLL_INTERVAL_SECONDS`
- `MARKET_STREAM_MAX_ITEMS`
- `MARKET_STREAM_MAX_STORED_ITEMS`
- `MARKET_STREAM_DB_PATH`
- `MARKET_STREAM_HOST`
- `MARKET_STREAM_PORT`
- `PORT`
- `MARKET_STREAM_CLASSIFIER_MODE`
- `OLLAMA_BASE_URL`
- `MARKET_STREAM_OLLAMA_MODEL`
- `MARKET_STREAM_OLLAMA_TIMEOUT_SECONDS`

See [.env.example](.env.example).

## Deployment

### Local always-on on macOS

Files included:

- [scripts/run_local.sh](scripts/run_local.sh)
- [scripts/run_tunnel.sh](scripts/run_tunnel.sh)
- [scripts/run_keepawake.sh](scripts/run_keepawake.sh)
- [scripts/install_launch_agents.sh](scripts/install_launch_agents.sh)
- [scripts/check_local_services.sh](scripts/check_local_services.sh)
- [deploy/com.newsclassified.marketstream.plist](deploy/com.newsclassified.marketstream.plist)
- [deploy/com.newsclassified.tunnel.plist](deploy/com.newsclassified.tunnel.plist)
- [deploy/com.newsclassified.keepawake.plist](deploy/com.newsclassified.keepawake.plist)

Recommended setup:

```bash
./scripts/install_launch_agents.sh
./scripts/check_local_services.sh
```

What this enables:

- `marketstream`: keeps the FastAPI app running after login
- `tunnel`: keeps the Cloudflare Tunnel online for public access
- `keepawake`: uses `caffeinate` to prevent idle sleep while still allowing the display to turn off

Operational note:

- This setup is designed for a logged-in Mac that stays powered on and connected to the network.
- If the machine shuts down, loses network, or is manually put to sleep, the public site will go offline until the session resumes.

### Container deployment

- [Dockerfile](Dockerfile)
- [docker-compose.yml](docker-compose.yml)
- [DEPLOY.md](DEPLOY.md)

This repo is designed so the same app can run:

- on a local machine
- on a VPS
- in Docker
- behind Nginx or a cloud reverse proxy
- behind Cloudflare Tunnel with a custom domain

## Project Structure

```text
src/market_stream/
  app.py                  FastAPI app and frontend
  config.py               sources, keywords, runtime config
  fetcher.py              feed and page ingestion
  pipeline.py             polling, dedupe, stream pipeline
  storage.py              SQLite persistence
  classifier.py           heuristic classifier
  retail_dashboard.py     trader-facing sections
  events.py               upcoming event calendar
```

## Copyright, Attribution, and Usage Boundaries

This repository contains only original code and metadata produced by this project.

Important:

- News headlines, summaries, source names, logos, and linked articles remain the property of their respective publishers.
- This project is intended to aggregate and link to public sources, not to republish full copyrighted articles.
- If you deploy this publicly, you are responsible for complying with each upstream source's terms of use, robots rules, branding rules, and redistribution limits.
- Do not market this project as an official product of any upstream publisher, exchange, regulator, or company.

See [NOTICE](NOTICE) for a short attribution and content-usage notice.

## License

This codebase is released under the [Apache-2.0 License](LICENSE).

## Financial Disclaimer

This project is for information and research purposes only.

- It is not investment advice.
- It is not a broker, exchange, or regulated market data terminal.
- It does not guarantee completeness, timeliness, or accuracy.

## Contributing

Pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Roadmap

- stronger event clustering
- per-source weighting
- watchlists and user presets
- better China and Asia source coverage
- cleaner mover feeds beyond public scraping
- richer deployment presets for cloud platforms

If this project is useful to you, star the repo.

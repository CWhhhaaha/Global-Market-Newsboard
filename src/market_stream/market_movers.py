from __future__ import annotations

import html
import re

import httpx

from .config import RETAIL_WATCHLIST

SPACE_RE = re.compile(r"\s+")


def _clean_text(value: str) -> str:
    cleaned = html.unescape(value)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    return SPACE_RE.sub(" ", cleaned).strip()


def _extract_change(text: str, symbol: str) -> dict[str, str] | None:
    pattern = re.compile(
        rf"\b{re.escape(symbol)}\b(?P<body>.{{0,220}}?)(?P<change>[+-]?\d+(?:\.\d+)?)\s*\((?P<pct>[+-]?\d+(?:\.\d+)?%)\)",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return None
    body = match.group("body")
    last_match = re.search(r"(\d+(?:\.\d+)?)", body)
    return {
        "symbol": symbol,
        "last": last_match.group(1) if last_match else "",
        "change": match.group("change"),
        "change_pct": match.group("pct"),
        "source_name": "Investing.com Pre-Market",
        "source_url": "https://www.investing.com/equities/pre-market",
    }


async def fetch_watchlist_movers() -> list[dict[str, str]]:
    url = "https://www.investing.com/equities/pre-market"
    headers = {
        "User-Agent": "market-moving-news-stream/0.1 (+https://localhost)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    async with httpx.AsyncClient(headers=headers, timeout=20.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()

    text = _clean_text(response.text)
    movers: list[dict[str, str]] = []
    for symbol in RETAIL_WATCHLIST:
        entry = _extract_change(text, symbol)
        if entry:
            movers.append(entry)
    return movers

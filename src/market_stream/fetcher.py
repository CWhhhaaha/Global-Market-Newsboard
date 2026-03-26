from __future__ import annotations

import asyncio
import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import feedparser
import httpx

from .config import (
    MARKET_KEYWORDS,
    MARKET_SYMBOLS,
    SEC_ALWAYS_KEEP_FORMS,
    SEC_EVENT_KEYWORDS,
    Source,
)
from .filing_filter import is_top_100_market_cap_filing
from .models import StreamItem

TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
US_LOCAL_TZ_RE = re.compile(r"\s(?:EST|EDT)$")
WHITEHOUSE_ITEM_RE = re.compile(
    r'wp-block-post-title[^>]*><a href="(?P<url>https://www\.whitehouse\.gov/[^"]+)"[^>]*>(?P<title>.*?)</a>.*?'
    r'<time datetime="(?P<datetime>[^"]+)"',
    re.S,
)
USTR_ITEM_RE = re.compile(
    r'<div class="views-row">.*?<time datetime="(?P<datetime>[^"]+)"[^>]*>.*?</time>.*?'
    r'<a href="(?P<url>/[^"]+)"[^>]*>(?P<title>.*?)</a>',
    re.S,
)


def contains_term(haystack: str, term: str) -> bool:
    pattern = r"(?<![a-z0-9])" + re.escape(term.lower()).replace(r"\ ", r"\s+") + r"(?![a-z0-9])"
    return re.search(pattern, haystack) is not None


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = html.unescape(value)
    text = TAG_RE.sub(" ", text)
    return SPACE_RE.sub(" ", text).strip()


SOURCE_TIMEZONE_OVERRIDES = {
    "www.eia.gov": ZoneInfo("America/New_York"),
    "www.federalreserve.gov": ZoneInfo("America/New_York"),
    "www.bls.gov": ZoneInfo("America/New_York"),
    "www.sec.gov": ZoneInfo("America/New_York"),
    "www.cftc.gov": ZoneInfo("America/New_York"),
    "www.whitehouse.gov": ZoneInfo("America/New_York"),
    "ustr.gov": ZoneInfo("America/New_York"),
}


def source_timezone(source: Source | None) -> ZoneInfo | None:
    if not source:
        return None
    for domain, tz in SOURCE_TIMEZONE_OVERRIDES.items():
        if domain in source.homepage:
            return tz
    return None


def parse_datetime(entry: dict, source: Source | None = None) -> datetime:
    for field in ("published", "updated", "created"):
        raw = entry.get(field)
        if not raw:
            continue
        try:
            tz_override = source_timezone(source)
            if tz_override and US_LOCAL_TZ_RE.search(raw.strip()):
                cleaned = US_LOCAL_TZ_RE.sub("", raw.strip())
                naive = datetime.strptime(cleaned, "%a, %d %b %Y %H:%M:%S")
                localized = naive.replace(tzinfo=tz_override)
                return localized.astimezone(timezone.utc)
            parsed = parsedate_to_datetime(raw)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except (TypeError, ValueError, IndexError):
            continue
    return datetime.now(timezone.utc)


def parse_iso_datetime(raw: str) -> datetime:
    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def match_terms(title: str, summary: str) -> list[str]:
    haystack = f"{title} {summary}".lower()
    matched = [term for term in (*MARKET_KEYWORDS, *MARKET_SYMBOLS) if contains_term(haystack, term)]
    return matched[:10]


def should_keep_sec_filing(source: Source, title: str, summary: str) -> bool:
    if source.category != "filings":
        return True

    haystack = f"{title} {summary}".lower()
    if not is_top_100_market_cap_filing(title, summary):
        return False
    if not any(contains_term(haystack, form) for form in SEC_ALWAYS_KEEP_FORMS):
        return False
    return any(contains_term(haystack, term) for term in SEC_EVENT_KEYWORDS)


async def fetch_source(client: httpx.AsyncClient, source: Source) -> list[StreamItem]:
    response = await client.get(source.feed_url, follow_redirects=True, timeout=20.0)
    response.raise_for_status()
    if source.kind == "html":
        return parse_html_source(source, response.text)
    parsed = feedparser.parse(response.text)

    items: list[StreamItem] = []
    for entry in parsed.entries:
        title = clean_text(entry.get("title"))
        summary = clean_text(entry.get("summary") or entry.get("description"))
        url = entry.get("link") or source.homepage
        if not should_keep_sec_filing(source, title, summary):
            continue
        matched_terms = match_terms(title, summary)
        if not matched_terms:
            continue

        items.append(
            StreamItem(
                source_name=source.name,
                source_category=source.category,
                source_region=source.region,
                title=title,
                summary=summary,
                url=url,
                source_homepage=source.homepage,
                published_at=parse_datetime(entry, source),
                matched_terms=matched_terms,
            )
        )
    return items


def parse_html_source(source: Source, text: str) -> list[StreamItem]:
    if source.parser == "whitehouse_news":
        return parse_whitehouse_news(source, text)
    if source.parser == "ustr_press":
        return parse_ustr_press(source, text)
    return []


def parse_whitehouse_news(source: Source, text: str) -> list[StreamItem]:
    items: list[StreamItem] = []
    for match in WHITEHOUSE_ITEM_RE.finditer(text):
        title = clean_text(match.group("title"))
        url = match.group("url")
        summary = ""
        matched_terms = match_terms(title, summary)
        if not matched_terms:
            continue
        items.append(
            StreamItem(
                source_name=source.name,
                source_category=source.category,
                source_region=source.region,
                title=title,
                summary=summary,
                url=url,
                source_homepage=source.homepage,
                published_at=parse_iso_datetime(match.group("datetime")),
                matched_terms=matched_terms,
            )
        )
        if len(items) >= 20:
            break
    return items


def parse_ustr_press(source: Source, text: str) -> list[StreamItem]:
    items: list[StreamItem] = []
    for match in USTR_ITEM_RE.finditer(text):
        url_path = match.group("url")
        if "/press-releases/" not in url_path:
            continue
        title = clean_text(match.group("title"))
        summary = ""
        matched_terms = match_terms(title, summary)
        if not matched_terms:
            continue
        items.append(
            StreamItem(
                source_name=source.name,
                source_category=source.category,
                source_region=source.region,
                title=title,
                summary=summary,
                url=urljoin(source.homepage, url_path),
                source_homepage=source.homepage,
                published_at=parse_iso_datetime(match.group("datetime")),
                matched_terms=matched_terms,
            )
        )
        if len(items) >= 20:
            break
    return items


async def fetch_all_sources(sources: list[Source]) -> tuple[list[StreamItem], list[str]]:
    headers = {
        "User-Agent": "market-moving-news-stream/0.1 (+https://localhost)",
        "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
    }
    async with httpx.AsyncClient(headers=headers) as client:
        tasks = [fetch_source(client, source) for source in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    items: list[StreamItem] = []
    errors: list[str] = []
    for source, result in zip(sources, results, strict=True):
        if isinstance(result, Exception):
            errors.append(f"{source.name}: {result}")
            continue
        items.extend(result)
    return items, errors

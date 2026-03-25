from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, time, timezone

import httpx


@dataclass(slots=True)
class UpcomingEvent:
    title: str
    category: str
    source_name: str
    source_url: str
    event_time: datetime
    note: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "category": self.category,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "event_time": self.event_time.isoformat(),
            "note": self.note,
        }


EVENT_SOURCES = (
    {
        "title": "FOMC Meeting",
        "category": "policy",
        "source_name": "Federal Reserve Calendar",
        "source_url": "https://www.federalreserve.gov/newsevents/calendar.htm",
        "parser": "parse_fomc_calendar",
    },
    {
        "title": "Employment Situation",
        "category": "macro",
        "source_name": "BLS Employment Situation",
        "source_url": "https://www.bls.gov/cps/home.htm",
        "parser": "parse_bls_next_release",
    },
    {
        "title": "Consumer Price Index",
        "category": "macro",
        "source_name": "BLS CPI",
        "source_url": "https://www.bls.gov/cpi/?viewClass=Print&viewType=Print",
        "parser": "parse_bls_next_release",
    },
    {
        "title": "Producer Price Index",
        "category": "macro",
        "source_name": "BLS PPI",
        "source_url": "https://www.bls.gov/ppi/?viewClass=Print&viewType=Print",
        "parser": "parse_bls_next_release",
    },
    {
        "title": "Weekly Petroleum Status Report",
        "category": "energy",
        "source_name": "EIA Petroleum",
        "source_url": "https://ir.eia.gov/wpsr/wpsrsummary.pdf",
        "parser": "parse_eia_petroleum",
    },
    {
        "title": "Weekly Natural Gas Storage Report",
        "category": "energy",
        "source_name": "EIA Natural Gas",
        "source_url": "https://ir.eia.gov/ngs/ngs.html?src=Natural-f8",
        "parser": "parse_eia_gas",
    },
)


MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def _parse_month_name(name: str) -> int:
    return MONTHS[name.strip().lower()]


def _from_month_day_year(month_name: str, day: str, year: str, hour: int = 13, minute: int = 0) -> datetime:
    return datetime(int(year), _parse_month_name(month_name), int(day), hour, minute, tzinfo=timezone.utc)


async def fetch_upcoming_events() -> list[UpcomingEvent]:
    async with httpx.AsyncClient(
        headers={"User-Agent": "market-moving-news-stream/0.1 (+https://localhost)"}
    ) as client:
        tasks = [_fetch_event_source(client, source) for source in EVENT_SOURCES]
        results = await __import__("asyncio").gather(*tasks, return_exceptions=True)

    events: list[UpcomingEvent] = []
    for result in results:
        if isinstance(result, UpcomingEvent):
            events.append(result)
    return sorted(events, key=lambda event: event.event_time)


async def _fetch_event_source(client: httpx.AsyncClient, source: dict[str, str]) -> UpcomingEvent | None:
    response = await client.get(source["source_url"], follow_redirects=True, timeout=20.0)
    response.raise_for_status()
    parser = globals()[source["parser"]]
    return parser(response.text, source)


def parse_bls_next_release(text: str, source: dict[str, str]) -> UpcomingEvent | None:
    match = re.search(
        r"Next Release(?:\s*Date)?\s*(?:\n|:|\s)*.*?([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None
    event_time = _from_month_day_year(match.group(1), match.group(2), match.group(3), 12, 30)
    return UpcomingEvent(
        title=source["title"],
        category=source["category"],
        source_name=source["source_name"],
        source_url=source["source_url"],
        event_time=event_time,
        note="Official BLS release schedule page",
    )


def parse_eia_gas(text: str, source: dict[str, str]) -> UpcomingEvent | None:
    match = re.search(r"Next Release:\s*([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})", text)
    if not match:
        return None
    event_time = _from_month_day_year(match.group(1), match.group(2), match.group(3), 14, 30)
    return UpcomingEvent(
        title=source["title"],
        category=source["category"],
        source_name=source["source_name"],
        source_url=source["source_url"],
        event_time=event_time,
        note="Official EIA page next-release field",
    )


def parse_eia_petroleum(_: str, source: dict[str, str]) -> UpcomingEvent | None:
    # EIA publishes weekly, typically Wednesday 14:30 UTC equivalent after US DST conversion is not modeled here.
    now = datetime.now(timezone.utc)
    days_ahead = (2 - now.weekday()) % 7
    if days_ahead == 0 and now.time() > time(14, 30):
        days_ahead = 7
    event_date = now.date().fromordinal(now.date().toordinal() + days_ahead)
    event_time = datetime.combine(event_date, time(14, 30), tzinfo=timezone.utc)
    return UpcomingEvent(
        title=source["title"],
        category=source["category"],
        source_name=source["source_name"],
        source_url=source["source_url"],
        event_time=event_time,
        note="Modeled from the standard weekly EIA schedule",
    )


def parse_fomc_calendar(text: str, source: dict[str, str]) -> UpcomingEvent | None:
    candidates = re.findall(r"Two-day meeting,\s*([A-Za-z]+)\s+(\d{1,2})\s*-\s*(\d{1,2})", text)
    if not candidates:
        return None

    now = datetime.now(timezone.utc)
    year_match = re.search(r"Calendar:\s*([A-Za-z]+)\s+(\d{4})", text)
    default_year = int(year_match.group(2)) if year_match else now.year

    upcoming: list[datetime] = []
    for month_name, start_day, _end_day in candidates:
        event_time = datetime(default_year, _parse_month_name(month_name), int(start_day), 18, 0, tzinfo=timezone.utc)
        if event_time >= now:
            upcoming.append(event_time)
    if not upcoming:
        return None

    return UpcomingEvent(
        title=source["title"],
        category=source["category"],
        source_name=source["source_name"],
        source_url=source["source_url"],
        event_time=min(upcoming),
        note="Parsed from the Federal Reserve calendar page",
    )

from __future__ import annotations

from .models import StreamItem


PRIORITY_KEYWORDS: tuple[str, ...] = (
    "fomc",
    "federal reserve",
    "interest rate",
    "inflation",
    "cpi",
    "ppi",
    "nonfarm",
    "payroll",
    "jobs",
    "recession",
    "sanction",
    "tariff",
    "oil",
    "opec",
    "natural gas",
    "missile",
    "attack",
    "war",
    "merger",
    "acquisition",
    "guidance",
    "earnings",
    "bankruptcy",
    "delisting",
)


def priority_score(item: StreamItem) -> int:
    score = 0
    haystack = f"{item.title} {item.summary}".lower()

    if item.source_category in {"macro", "policy", "energy"}:
        score += 4
    elif item.source_category in {"regulation", "filings"}:
        score += 2
    elif item.source_category in {"markets", "world"}:
        score += 1

    if item.source_name.startswith("Federal Reserve"):
        score += 3
    if item.source_name.startswith("BLS"):
        score += 3
    if item.source_name.startswith("EIA"):
        score += 2
    if item.source_name.startswith("CFTC") or item.source_name.startswith("SEC"):
        score += 1

    score += sum(2 for keyword in PRIORITY_KEYWORDS if keyword in haystack)

    # Specific 8-K items that usually matter more intraday.
    if item.source_category == "filings":
        if "item 2.02" in haystack or "results of operations" in haystack:
            score += 3
        if "item 5.02" in haystack or "departure of directors" in haystack:
            score += 2
        if "item 1.01" in haystack or "material definitive agreement" in haystack:
            score += 3

    return score


def is_high_priority(item: StreamItem) -> bool:
    return priority_score(item) >= 6

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .config import RETAIL_WATCHLIST
from .models import StreamItem


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    haystack = text.lower()
    return any(keyword.lower() in haystack for keyword in keywords)


def _item_text(item: StreamItem) -> str:
    classification = item.classification
    parts = [
        item.title,
        item.summary,
        item.source_name,
        item.source_category,
        item.source_region,
        " ".join(item.matched_terms),
    ]
    if classification:
        parts.extend(
            [
                classification.primary_label,
                classification.impact_direction,
                classification.impact_level,
                " ".join(classification.affected_targets),
                " ".join(classification.secondary_labels),
            ]
        )
    return " ".join(part for part in parts if part).lower()


def _match_market_drivers(text: str, label: str) -> bool:
    return label == "market_driver" or _contains_any(
        text,
        (
            "fed",
            "federal reserve",
            "fomc",
            "cpi",
            "ppi",
            "nonfarm",
            "payroll",
            "interest rate",
            "yield",
            "treasury",
            "dollar",
            "dxy",
            "gdpnow",
        ),
    )


def _match_bonds_rates(text: str) -> bool:
    return _contains_any(
        text,
        (
            "treasury",
            "yield",
            "bond",
            "coupon",
            "refunding",
            "auction result",
            "treasury auction",
            "tips",
            "floating rate note",
            "us10y",
            "us02y",
            "us30y",
            "interest rates commentary",
        ),
    )


def _match_dollar_fx(text: str) -> bool:
    return _contains_any(
        text,
        (
            "dollar",
            "u.s. dollar",
            "usd",
            "dxy",
            "foreign exchange",
            "fx",
            "forex",
            "eurusd",
            "usd/jpy",
            "usdjpy",
            "usdcny",
            "usd/cny",
            "sterling",
            "yen",
            "euro",
            "yuan",
            "renminbi",
            "fx commentary",
        ),
    )


def _match_precious_metals(text: str) -> bool:
    return _contains_any(
        text,
        (
            "gold",
            "silver",
            "platinum",
            "palladium",
            "copper",
            "bullion",
            "precious metal",
            "metals commentary",
            "spot gold",
            "spot silver",
            "gold futures",
            "silver futures",
        ),
    )


def _match_china_watch(text: str) -> bool:
    return _contains_any(
        text,
        (
            "china",
            "beijing",
            "pboc",
            "people s bank of china",
            "yuan",
            "renminbi",
            "hong kong",
            "mainland",
            "china adr",
            "alibaba",
            "baidu",
            "pdd",
            "jd.com",
            "jd ",
            "nio",
            "xpeng",
            "li auto",
            "byd",
            "tencent",
            "taiwan",
            "tariff",
            "export control",
        ),
    )


def _match_trump_watch(text: str) -> bool:
    return _contains_any(
        text,
        (
            "trump",
            "donald trump",
            "white house",
            "executive order",
            "tariff",
            "sanction",
            "campaign",
            "truth social",
            "trade war",
            "trump administration",
            "president trump",
        ),
    )


def _match_jensen_watch(text: str) -> bool:
    direct_terms = (
        "jensen huang",
        "huang renxun",
        "黄仁勋",
        "nvidia ceo",
        "nvidia chief executive",
        "gtc",
        "gpu technology conference",
        "nvidia keynote",
    )
    nvidia_terms = (
        "nvidia",
        "nvda",
        "blackwell",
        "grace blackwell",
        "cuda",
        "dgx",
        "rubin",
        "hopper",
        "h100",
        "h200",
        "gb200",
        "ai factory",
        "ai factories",
        "omniverse",
        "rtx",
    )
    nvidia_sources = (
        "nvidia newsroom",
        "nvidia blog",
        "techcrunch nvidia",
    )
    return (
        _contains_any(text, direct_terms)
        or _contains_any(text, nvidia_sources)
        or (
            _contains_any(text, nvidia_terms)
            and _contains_any(text, nvidia_sources + ("ai", "semiconductor", "chip", "chips"))
        )
    )


def _match_musk_watch(text: str) -> bool:
    direct_terms = (
        "elon musk",
        "马斯克",
        "tesla ceo",
        "twitter owner",
        "chief twit",
    )
    musk_ecosystem_terms = (
        "tesla",
        "tsla",
        "spacex",
        "starlink",
        "xai",
        "x corp",
        "twitter",
        "model y",
        "model 3",
        "robotaxi",
        "cybertruck",
        "optimus",
    )
    musk_sources = (
        "tesla blog",
        "teslarati",
        "electrek tesla",
        "techcrunch spacex",
        "techcrunch xai",
        "techcrunch elon musk",
    )
    catalyst_terms = (
        "launch",
        "earnings",
        "guidance",
        "deliveries",
        "autopilot",
        "lawsuit",
        "investigation",
        "robotaxi",
        "ai",
        "funding",
        "valuation",
        "shares",
        "stock",
    )
    return _contains_any(text, direct_terms) or (
        _contains_any(text, musk_ecosystem_terms) and (_contains_any(text, musk_sources) or _contains_any(text, catalyst_terms))
    )


def _match_earnings_guidance(text: str, label: str) -> bool:
    return label == "earnings_guidance" or _contains_any(
        text,
        ("earnings", "guidance", "forecast", "revenue", "profit", "quarter", "results"),
    )


def _match_policy_regulation_shock(text: str, label: str, source_category: str) -> bool:
    return source_category != "filings" and (
        _contains_any(
            text,
            (
                "sec press release",
                "cftc",
                "doj",
                "tariff",
                "export control",
                "regulation",
                "investigation",
                "enforcement",
                "antitrust",
                "white house",
                "treasury department",
            ),
        )
        or (label == "policy_regulation" and source_category in {"policy", "regulation"})
    )


def _match_war_and_oil(text: str, label: str) -> bool:
    return label in {"war_geopolitics", "energy_commodities"} or _contains_any(
        text,
        (
            "war",
            "attack",
            "missile",
            "sanction",
            "middle east",
            "iran",
            "israel",
            "ukraine",
            "russia",
            "china",
            "taiwan",
            "oil",
            "opec",
            "petroleum",
            "brent",
            "wti",
        ),
    )


def _watch_symbol_for_text(text: str) -> str | None:
    for symbol, aliases in RETAIL_WATCHLIST.items():
        if _contains_any(text, aliases):
            return symbol
    return None


def _is_hot_stock_candidate(text: str, label: str) -> bool:
    catalyst_terms = (
        "stock", "stocks", "share", "shares",
        "earnings", "guidance", "forecast", "revenue", "profit",
        "upgrade", "downgrade", "target price",
        "surge", "surges", "jump", "jumps", "soar", "soars", "rally", "rallies",
        "drop", "drops", "slide", "slides", "sell-off", "selloff", "plunge", "plunges",
        "lawsuit", "investigation", "probe", "antitrust", "doj", "sec",
        "launch", "unveil", "announce", "announces", "product", "chip", "chips",
        "ai", "semiconductor", "bitcoin", "ethereum", "crypto", "etf",
        "deliveries", "robotaxi", "autopilot", "cybertruck",
        "merger", "acquisition", "partnership", "deal",
    )
    return label in {"hot_stock_alert", "single_stock_event", "earnings_guidance", "sector_opportunity"} or _contains_any(text, catalyst_terms)


def build_retail_sections(
    items: list[StreamItem],
    limit_per_section: int = 5,
    lang: str = "en",
) -> dict[str, list[dict[str, object]]]:
    sections: dict[str, list[dict[str, object]]] = {
        "market_drivers": [],
        "bonds_rates": [],
        "dollar_fx": [],
        "precious_metals": [],
        "china_watch": [],
        "trump_watch": [],
        "jensen_watch": [],
        "musk_watch": [],
        "hot_stocks": [],
        "earnings_guidance": [],
        "policy_regulation_shock": [],
        "war_and_oil": [],
    }
    hot_stock_symbol_counts: dict[str, int] = {}

    recent_cutoff = datetime.now(timezone.utc) - timedelta(days=5)
    recent_items = [item for item in items if item.published_at.astimezone(timezone.utc) >= recent_cutoff]
    older_items = [item for item in items if item.published_at.astimezone(timezone.utc) < recent_cutoff]

    def fill_sections(bucket: list[StreamItem]) -> None:
        for item in bucket:
            data = item.as_dict(lang)
            text = _item_text(item)
            label = item.classification.primary_label if item.classification else ""

            if len(sections["market_drivers"]) < limit_per_section and _match_market_drivers(text, label):
                sections["market_drivers"].append(data)
                continue

            if len(sections["bonds_rates"]) < limit_per_section and _match_bonds_rates(text):
                sections["bonds_rates"].append(data)
                continue

            if len(sections["dollar_fx"]) < limit_per_section and _match_dollar_fx(text):
                sections["dollar_fx"].append(data)
                continue

            if len(sections["precious_metals"]) < limit_per_section and _match_precious_metals(text):
                sections["precious_metals"].append(data)
                continue

            if len(sections["china_watch"]) < limit_per_section and _match_china_watch(text):
                sections["china_watch"].append(data)
                continue

            if len(sections["trump_watch"]) < limit_per_section and _match_trump_watch(text):
                sections["trump_watch"].append(data)
                continue

            if len(sections["jensen_watch"]) < limit_per_section and _match_jensen_watch(text):
                sections["jensen_watch"].append(data)
                continue

            if len(sections["musk_watch"]) < limit_per_section and _match_musk_watch(text):
                sections["musk_watch"].append(data)
                continue

            if len(sections["hot_stocks"]) < limit_per_section:
                symbol = _watch_symbol_for_text(text)
                if symbol and hot_stock_symbol_counts.get(symbol, 0) == 0 and _is_hot_stock_candidate(text, label):
                    data["watch_symbol"] = symbol
                    sections["hot_stocks"].append(data)
                    hot_stock_symbol_counts[symbol] = 1
                    continue

            if len(sections["earnings_guidance"]) < limit_per_section and _match_earnings_guidance(text, label):
                sections["earnings_guidance"].append(data)
                continue

            if (
                len(sections["policy_regulation_shock"]) < limit_per_section
                and _match_policy_regulation_shock(text, label, item.source_category)
            ):
                sections["policy_regulation_shock"].append(data)
                continue

            if len(sections["war_and_oil"]) < limit_per_section and _match_war_and_oil(text, label):
                sections["war_and_oil"].append(data)

    fill_sections(recent_items)
    fill_sections(older_items)

    if len(sections["hot_stocks"]) < limit_per_section:
        chosen_ids = {item["id"] for item in sections["hot_stocks"]}
        for bucket in (recent_items, older_items):
            for item in bucket:
                if len(sections["hot_stocks"]) >= limit_per_section:
                    break
                if item.item_id in chosen_ids:
                    continue
                text = _item_text(item)
                label = item.classification.primary_label if item.classification else ""
                symbol = _watch_symbol_for_text(text)
                if not symbol:
                    continue
                if not _is_hot_stock_candidate(text, label):
                    continue
                if hot_stock_symbol_counts.get(symbol, 0) >= 2:
                    continue
                data = item.as_dict(lang)
                data["watch_symbol"] = symbol
                sections["hot_stocks"].append(data)
                hot_stock_symbol_counts[symbol] = hot_stock_symbol_counts.get(symbol, 0) + 1
                chosen_ids.add(item.item_id)
            if len(sections["hot_stocks"]) >= limit_per_section:
                break

    return sections


def build_prepost_news(items: list[StreamItem], limit: int = 5) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for item in items:
        if item.item_id in seen_ids:
            continue
        text = _item_text(item)
        if _contains_any(
            text,
            (
                "premarket",
                "pre-market",
                "pre market",
                "after hours",
                "after-hours",
                "after market",
                "after-market",
                "extended trading",
                "shares jump",
                "stock jumps",
                "stock rises",
                "stock falls",
                "stock drops",
                "stock sinks",
                "stock plunges",
                "stock surges",
                "stock soars",
                "shares rise",
                "shares fall",
                "shares drop",
                "shares plunge",
                "shares surge",
                "shares soar",
                "zooms",
                "tumbles",
                "slides",
                "rallies",
            ),
        ):
            selected.append(item.as_dict())
            seen_ids.add(item.item_id)
        if len(selected) >= limit:
            break
    return selected

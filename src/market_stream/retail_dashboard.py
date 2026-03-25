from __future__ import annotations

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


def build_retail_sections(items: list[StreamItem], limit_per_section: int = 5) -> dict[str, list[dict[str, object]]]:
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

    for item in items:
        data = item.as_dict()
        text = _item_text(item)
        label = item.classification.primary_label if item.classification else ""

        if (
            len(sections["market_drivers"]) < limit_per_section
            and (
                label == "market_driver"
                or _contains_any(
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
            )
        ):
            sections["market_drivers"].append(data)
            continue

        if (
            len(sections["bonds_rates"]) < limit_per_section
            and _contains_any(
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
        ):
            sections["bonds_rates"].append(data)
            continue

        if (
            len(sections["dollar_fx"]) < limit_per_section
            and _contains_any(
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
        ):
            sections["dollar_fx"].append(data)
            continue

        if (
            len(sections["precious_metals"]) < limit_per_section
            and _contains_any(
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
        ):
            sections["precious_metals"].append(data)
            continue

        if (
            len(sections["china_watch"]) < limit_per_section
            and _contains_any(
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
        ):
            sections["china_watch"].append(data)
            continue

        if (
            len(sections["trump_watch"]) < limit_per_section
            and _contains_any(
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
        ):
            sections["trump_watch"].append(data)
            continue

        if (
            len(sections["jensen_watch"]) < limit_per_section
            and _contains_any(
                text,
                (
                    "jensen huang",
                    "huang renxun",
                    "黄仁勋",
                    "nvidia ceo",
                    "nvidia chief executive",
                    "gtc",
                    "gpu technology conference",
                    "nvidia keynote",
                    "blackwell",
                    "grace blackwell",
                    "cuda",
                    "dgx",
                ),
            )
        ):
            sections["jensen_watch"].append(data)
            continue

        if (
            len(sections["musk_watch"]) < limit_per_section
            and _contains_any(
                text,
                (
                    "elon musk",
                    "马斯克",
                    "xai",
                    "spacex",
                    "tesla ceo",
                    "x corp",
                    "twitter owner",
                ),
            )
        ):
            sections["musk_watch"].append(data)
            continue

        if len(sections["hot_stocks"]) < limit_per_section:
            for symbol, aliases in RETAIL_WATCHLIST.items():
                if _contains_any(text, aliases):
                    data["watch_symbol"] = symbol
                    sections["hot_stocks"].append(data)
                    break
            if data in sections["hot_stocks"]:
                continue

        if (
            len(sections["earnings_guidance"]) < limit_per_section
            and (
                label == "earnings_guidance"
                or _contains_any(
                    text,
                    ("earnings", "guidance", "forecast", "revenue", "profit", "quarter", "results"),
                )
            )
        ):
            sections["earnings_guidance"].append(data)
            continue

        if (
            len(sections["policy_regulation_shock"]) < limit_per_section
            and item.source_category != "filings"
            and (
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
                or (label == "policy_regulation" and item.source_category in {"policy", "regulation"})
            )
        ):
            sections["policy_regulation_shock"].append(data)
            continue

        if (
            len(sections["war_and_oil"]) < limit_per_section
            and (
                label in {"war_geopolitics", "energy_commodities"}
                or _contains_any(
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
            )
        ):
            sections["war_and_oil"].append(data)

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

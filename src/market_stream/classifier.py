from __future__ import annotations

from dataclasses import dataclass, field
import re


@dataclass(slots=True)
class ClassificationResult:
    primary_label: str
    impact_direction: str
    impact_level: str
    affected_targets: list[str] = field(default_factory=list)
    secondary_labels: list[str] = field(default_factory=list)
    confidence: float = 0.5
    rationale: str = ""

RETAIL_LABEL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "market_driver": (
        "fomc",
        "federal reserve",
        "ecb",
        "bank of england",
        "interest rate",
        "rate cut",
        "rate hike",
        "powell",
        "minutes",
        "beige book",
        "gdpnow",
        "nonfarm",
        "payroll",
        "cpi",
        "ppi",
        "inflation",
        "gdp",
        "treasury auction",
        "auction result",
        "refunding",
        "tips",
        "yield",
        "bond",
        "dollar",
        "dxy",
        "fx",
        "foreign exchange",
        "forex",
        "yen",
        "euro",
    ),
    "hot_stock_alert": (
        "nvidia",
        "jensen huang",
        "gtc",
        "gpu technology conference",
        "blackwell",
        "grace blackwell",
        "cuda",
        "tesla",
        "apple",
        "microsoft",
        "meta",
        "google",
        "alphabet",
        "amazon",
        "micron",
        "paypal",
        "amd",
        "broadcom",
        "alibaba",
        "baidu",
        "pdd",
        "jd.com",
        "nio",
        "xpeng",
        "li auto",
        "byd",
    ),
    "earnings_guidance": (
        "earnings",
        "guidance",
        "results of operations",
        "financial condition",
        "revenue",
        "profit",
        "forecast",
        "quarter",
        "full year",
        "item 2.02",
    ),
    "policy_regulation": (
        "sec",
        "cftc",
        "doj",
        "antitrust",
        "probe",
        "investigation",
        "regulation",
        "enforcement",
        "prudential",
        "delisting",
        "tariff",
        "export control",
    ),
    "war_geopolitics": (
        "war",
        "attack",
        "missile",
        "sanction",
        "taiwan",
        "china",
        "russia",
        "ukraine",
        "iran",
        "israel",
        "middle east",
        "shipping",
        "strait",
    ),
    "energy_commodities": (
        "oil",
        "opec",
        "petroleum",
        "gasoline",
        "diesel",
        "natural gas",
        "storage report",
        "energy",
        "eia",
        "gold",
        "silver",
        "platinum",
        "palladium",
        "copper",
        "bullion",
        "precious metal",
        "metals",
    ),
    "sector_opportunity": (
        "semiconductor",
        "chip",
        "ai",
        "artificial intelligence",
        "bank",
        "crypto",
        "biotech",
        "electric vehicle",
        "cloud",
        "software",
    ),
    "single_stock_event": (
        "merger",
        "acquisition",
        "material definitive agreement",
        "departure of directors",
        "bankruptcy",
        "dividend",
        "share repurchase",
        "8-k",
        "other events",
        "item 5.02",
        "item 1.01",
    ),
}


TARGET_KEYWORDS: dict[str, tuple[str, ...]] = {
    "SPY": ("fomc", "cpi", "ppi", "nonfarm", "payroll", "gdp", "federal reserve"),
    "QQQ": ("nvidia", "tesla", "apple", "microsoft", "meta", "google", "amazon", "chip", "semiconductor"),
    "NVDA": ("nvidia", "jensen huang", "gtc", "gpu technology conference", "blackwell", "grace blackwell", "cuda", "dgx"),
    "Oil": ("oil", "opec", "petroleum", "gasoline", "diesel", "brent", "wti"),
    "Gold": ("gold", "bullion", "spot gold", "gold futures"),
    "Silver": ("silver", "spot silver", "silver futures"),
    "Treasuries": ("treasury", "treasury auction", "auction result", "tips", "bond yield", "10-year yield", "2-year yield", "30-year yield"),
    "Dollar": ("dollar", "dxy", "usd", "u.s. dollar"),
    "FX": ("foreign exchange", "fx", "forex", "eurusd", "usd/jpy", "usdjpy", "usdcny", "usd/cny", "yen", "euro", "sterling", "renminbi", "yuan"),
    "NatGas": ("natural gas", "storage report", "lng"),
    "Banks": ("bank", "liquidity", "capital", "prudential", "stress test"),
    "Crypto": ("bitcoin", "ethereum", "crypto", "stablecoin"),
    "China ADR": ("china", "tariff", "sanction", "taiwan"),
    "China Tech": ("alibaba", "baidu", "pdd", "jd.com", "nio", "xpeng", "li auto", "byd", "hong kong"),
    "Semis": ("nvidia", "micron", "amd", "chip", "semiconductor"),
}


DIRECTION_BULLISH = (
    "rises",
    "rise",
    "cut",
    "declines",
    "cools",
    "eases",
    "beats",
    "buyback",
    "dividend",
    "approval",
)

DIRECTION_BEARISH = (
    "falls",
    "higher than expected",
    "attack",
    "war",
    "tariff",
    "sanction",
    "downgrade",
    "probe",
    "bankruptcy",
    "delisting",
)

IMPACT_CRITICAL = (
    "fomc",
    "interest rate",
    "cpi",
    "ppi",
    "nonfarm",
    "payroll",
    "war",
    "missile",
    "attack",
    "sanction",
    "tariff",
    "opec",
    "treasury auction",
    "auction result",
    "dollar",
    "dxy",
    )

IMPACT_HIGH = (
    "guidance",
    "earnings",
    "results of operations",
    "material definitive agreement",
    "departure of directors",
    "investigation",
    "regulation fd disclosure",
)


def contains_term(haystack: str, term: str) -> bool:
    pattern = r"(?<![a-z0-9])" + re.escape(term.lower()).replace(r"\ ", r"\s+") + r"(?![a-z0-9])"
    return re.search(pattern, haystack) is not None


class HeuristicClassifier:
    def classify(self, title: str, summary: str, source_category: str, source_name: str) -> ClassificationResult:
        haystack = f"{title} {summary} {source_category} {source_name}".lower()

        label_scores = {
            label: sum(1 for keyword in keywords if contains_term(haystack, keyword))
            for label, keywords in RETAIL_LABEL_KEYWORDS.items()
        }
        primary_label = max(label_scores, key=label_scores.get)
        if label_scores[primary_label] == 0:
            primary_label = "market_driver" if source_category in {"macro", "policy", "energy"} else "single_stock_event"

        secondary_labels = [
            label for label, score in label_scores.items()
            if label != primary_label and score > 0
        ][:3]

        affected_targets = [
            target for target, keywords in TARGET_KEYWORDS.items()
            if any(contains_term(haystack, keyword) for keyword in keywords)
        ][:4]
        if not affected_targets:
            affected_targets = ["SPY"]

        bearish = any(contains_term(haystack, keyword) for keyword in DIRECTION_BEARISH)
        bullish = any(contains_term(haystack, keyword) for keyword in DIRECTION_BULLISH)
        if bearish and bullish:
            impact_direction = "mixed"
        elif bearish:
            impact_direction = "bearish"
        elif bullish:
            impact_direction = "bullish"
        else:
            impact_direction = "watch"

        if any(contains_term(haystack, keyword) for keyword in IMPACT_CRITICAL):
            impact_level = "critical"
        elif any(contains_term(haystack, keyword) for keyword in IMPACT_HIGH) or primary_label in {"market_driver", "hot_stock_alert"}:
            impact_level = "high"
        elif primary_label in {"energy_commodities", "policy_regulation", "earnings_guidance", "war_geopolitics"}:
            impact_level = "medium"
        else:
            impact_level = "low"

        confidence = min(0.55 + 0.08 * label_scores.get(primary_label, 0), 0.94)
        rationale = f"{primary_label} via retail-priority match; direction={impact_direction}; impact={impact_level}"

        return ClassificationResult(
            primary_label=primary_label,
            impact_direction=impact_direction,
            impact_level=impact_level,
            affected_targets=affected_targets,
            secondary_labels=secondary_labels,
            confidence=confidence,
            rationale=rationale,
        )

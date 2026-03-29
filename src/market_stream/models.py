from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha1

from .classifier import ClassificationResult


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


ZH_LABELS = {
    "market_driver": "大盘驱动",
    "hot_stock_alert": "热门股突发",
    "earnings_guidance": "财报与指引",
    "policy_regulation": "政策监管",
    "war_geopolitics": "战争与地缘",
    "energy_commodities": "能源与大宗",
    "sector_opportunity": "板块机会",
    "single_stock_event": "个股事件",
    "unclassified": "未分类",
    "bullish": "利多",
    "bearish": "利空",
    "watch": "观察",
    "mixed": "混合",
    "critical": "极高",
    "high": "高",
    "medium": "中",
    "low": "低",
}


@dataclass(slots=True)
class StreamItem:
    source_name: str
    source_category: str
    source_region: str
    title: str
    summary: str
    url: str
    source_homepage: str
    published_at: datetime
    matched_terms: list[str] = field(default_factory=list)
    fetched_at: datetime = field(default_factory=utc_now)
    title_zh: str = ""
    summary_zh: str = ""
    classification: ClassificationResult | None = None

    @property
    def item_id(self) -> str:
        raw = f"{self.source_name}|{self.title.strip().lower()}|{self.url.strip()}"
        return sha1(raw.encode("utf-8")).hexdigest()

    def localized_title(self, lang: str = "en") -> str:
        return self.title_zh if lang.startswith("zh") and self.title_zh else self.title

    def localized_summary(self, lang: str = "en") -> str:
        if lang.startswith("zh"):
            return self.summary_zh if self.summary_zh else "点击原文查看详情。"
        return self.summary

    def as_text_line(self, lang: str = "en") -> str:
        published = self.published_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        terms = ", ".join(self.matched_terms[:6]) if self.matched_terms else "general"
        return (
            f"[{published}] {self.localized_title(lang)} | source={self.source_name} | "
            f"matched={terms} | link={self.url}"
        )

    def as_alert_text(self, lang: str = "en") -> str:
        published = self.published_at.strftime("%Y-%m-%d %H:%M UTC")
        summary = self.localized_summary(lang) or ("暂无摘要。" if lang.startswith("zh") else "No summary available.")
        terms = ", ".join(self.matched_terms[:5]) if self.matched_terms else "general market signal"
        label = self.classification.primary_label if self.classification else "unclassified"
        direction = self.classification.impact_direction if self.classification else "watch"
        impact = self.classification.impact_level if self.classification else "low"
        title = self.localized_title(lang)
        if lang.startswith("zh"):
            return (
                f"【{self.source_category.upper()} | {self.source_region.upper()}】 {title}\n"
                f"时间: {published}\n"
                f"来源: {self.source_name}\n"
                f"信号: {terms}\n"
                f"分类: {ZH_LABELS.get(label, label)} | {ZH_LABELS.get(direction, direction)} | {ZH_LABELS.get(impact, impact)}\n"
                f"链接: {self.url}\n"
                f"摘要: {summary}"
            )
        return (
            f"【{self.source_category.upper()} | {self.source_region.upper()}】 {title}\n"
            f"Time: {published}\n"
            f"Source: {self.source_name}\n"
            f"Signal: {terms}\n"
            f"Class: {label} | {direction} | {impact}\n"
            f"Link: {self.url}\n"
            f"Summary: {summary}"
        )

    def as_dict(self, lang: str = "en") -> dict[str, object]:
        return {
            "id": self.item_id,
            "source_name": self.source_name,
            "source_category": self.source_category,
            "source_region": self.source_region,
            "title": self.localized_title(lang),
            "summary": self.localized_summary(lang),
            "title_original": self.title,
            "summary_original": self.summary,
            "title_zh": self.title_zh,
            "summary_zh": self.summary_zh,
            "url": self.url,
            "source_homepage": self.source_homepage,
            "published_at": self.published_at.isoformat(),
            "fetched_at": self.fetched_at.isoformat(),
            "matched_terms": self.matched_terms,
            "classification": {
                "primary_label": self.classification.primary_label if self.classification else "unclassified",
                "impact_direction": self.classification.impact_direction if self.classification else "watch",
                "impact_level": self.classification.impact_level if self.classification else "low",
                "affected_targets": self.classification.affected_targets if self.classification else [],
                "secondary_labels": self.classification.secondary_labels if self.classification else [],
                "confidence": self.classification.confidence if self.classification else 0.0,
                "rationale": self.classification.rationale if self.classification else "",
            },
            "text_line": self.as_text_line(lang),
            "alert_text": self.as_alert_text(lang),
        }

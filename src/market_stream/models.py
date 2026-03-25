from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha1

from .classifier import ClassificationResult


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


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
    classification: ClassificationResult | None = None

    @property
    def item_id(self) -> str:
        raw = f"{self.source_name}|{self.title.strip().lower()}|{self.url.strip()}"
        return sha1(raw.encode("utf-8")).hexdigest()

    def as_text_line(self) -> str:
        published = self.published_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        terms = ", ".join(self.matched_terms[:6]) if self.matched_terms else "general"
        return (
            f"[{published}] {self.title} | source={self.source_name} | "
            f"matched={terms} | link={self.url}"
        )

    def as_alert_text(self) -> str:
        published = self.published_at.strftime("%Y-%m-%d %H:%M UTC")
        summary = self.summary or "No summary available."
        terms = ", ".join(self.matched_terms[:5]) if self.matched_terms else "general market signal"
        label = self.classification.primary_label if self.classification else "unclassified"
        direction = self.classification.impact_direction if self.classification else "watch"
        impact = self.classification.impact_level if self.classification else "low"
        return (
            f"【{self.source_category.upper()} | {self.source_region.upper()}】 {self.title}\n"
            f"Time: {published}\n"
            f"Source: {self.source_name}\n"
            f"Signal: {terms}\n"
            f"Class: {label} | {direction} | {impact}\n"
            f"Link: {self.url}\n"
            f"Summary: {summary}"
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.item_id,
            "source_name": self.source_name,
            "source_category": self.source_category,
            "source_region": self.source_region,
            "title": self.title,
            "summary": self.summary,
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
            "text_line": self.as_text_line(),
            "alert_text": self.as_alert_text(),
        }

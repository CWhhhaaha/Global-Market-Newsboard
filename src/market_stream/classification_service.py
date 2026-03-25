from __future__ import annotations

import json
import re

import httpx

from .classifier import ClassificationResult, HeuristicClassifier
from .config import CLASSIFIER_MODE, OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT_SECONDS
from .models import StreamItem


class ClassificationService:
    def __init__(self) -> None:
        self._classifier = HeuristicClassifier()

    async def classify_item_async(self, item: StreamItem) -> StreamItem:
        if CLASSIFIER_MODE != "ollama":
            return self.classify_item(item)

        try:
            item.classification = await self._classify_with_ollama(item)
        except Exception:
            item.classification = self._classifier.classify(
                title=item.title,
                summary=item.summary,
                source_category=item.source_category,
                source_name=item.source_name,
            )
        return item

    async def classify_items_async(self, items: list[StreamItem]) -> list[StreamItem]:
        if not items:
            return items
        results: list[StreamItem] = []
        for item in items:
            results.append(await self.classify_item_async(item))
        return results

    def classify_item(self, item: StreamItem) -> StreamItem:
        result = self._classifier.classify(
            title=item.title,
            summary=item.summary,
            source_category=item.source_category,
            source_name=item.source_name,
        )
        item.classification = result
        return item

    def classify_items(self, items: list[StreamItem]) -> list[StreamItem]:
        return [self.classify_item(item) for item in items]

    async def _classify_with_ollama(self, item: StreamItem) -> ClassificationResult:
        prompt = self._build_prompt(item)
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0,
                    },
                },
            )
            response.raise_for_status()

        payload = response.json()
        raw = payload.get("response", "{}")
        data = self._extract_json(raw)
        if not data:
            raise ValueError("Ollama classification returned no JSON")

        return ClassificationResult(
            primary_label=data.get("primary_label", "market_driver"),
            impact_direction=data.get("impact_direction", "watch"),
            impact_level=data.get("impact_level", "low"),
            affected_targets=list(data.get("affected_targets", []))[:4],
            secondary_labels=list(data.get("secondary_labels", []))[:3],
            confidence=float(data.get("confidence", 0.5)),
            rationale=str(data.get("rationale", "ollama classification")),
        )

    @staticmethod
    def _build_prompt(item: StreamItem) -> str:
        return f"""
You are classifying a market-moving news item for a US equities monitoring system.
Return JSON only.

Allowed primary_label values:
- market_driver
- hot_stock_alert
- earnings_guidance
- policy_regulation
- war_geopolitics
- energy_commodities
- sector_opportunity
- single_stock_event

Allowed impact_direction values:
- bullish
- bearish
- mixed
- watch

Allowed impact_level values:
- critical
- high
- medium
- low

Allowed affected_targets values:
- SPY
- QQQ
- Oil
- NatGas
- Banks
- Crypto
- China ADR
- Semis

Classify this item:
source_name: {item.source_name}
source_category: {item.source_category}
source_region: {item.source_region}
title: {item.title}
summary: {item.summary}

Return this JSON shape:
{{
  "primary_label": "...",
  "impact_direction": "...",
  "impact_level": "...",
  "affected_targets": ["..."],
  "secondary_labels": ["..."],
  "confidence": 0.0,
  "rationale": "one short sentence"
}}
""".strip()

    @staticmethod
    def _extract_json(raw: str) -> dict[str, object] | None:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                return None
            return json.loads(match.group(0))

    @staticmethod
    def serialize(result: ClassificationResult | None) -> dict[str, object]:
        if result is None:
            return {
                "primary_label": "unclassified",
                "impact_direction": "watch",
                "impact_level": "low",
                "affected_targets": [],
                "secondary_labels": [],
                "confidence": 0.0,
                "rationale": "",
            }
        return {
            "primary_label": result.primary_label,
            "impact_direction": result.impact_direction,
            "impact_level": result.impact_level,
            "affected_targets": result.affected_targets,
            "secondary_labels": result.secondary_labels,
            "confidence": result.confidence,
            "rationale": result.rationale,
        }

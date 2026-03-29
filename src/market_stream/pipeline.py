from __future__ import annotations

import asyncio
import json
import re
from collections import deque
from datetime import datetime
from typing import AsyncIterator

from .config import CLASSIFIER_MODE, DB_PATH, MAX_ITEMS, OLLAMA_MODEL, POLL_INTERVAL_SECONDS, SOURCES
from .classification_service import ClassificationService
from .events import UpcomingEvent, fetch_upcoming_events
from .fetcher import fetch_all_sources
from .models import StreamItem
from .market_movers import fetch_watchlist_movers
from .retail_dashboard import build_prepost_news, build_retail_sections
from .signals import is_high_priority, priority_score
from .storage import SQLiteStore

TITLE_STOPWORDS = {
    "a", "an", "and", "as", "at", "be", "for", "from", "how", "in", "into", "is", "its",
    "of", "on", "or", "the", "to", "up", "with", "what", "why", "will",
}


class NewsStreamService:
    def __init__(self) -> None:
        self._items: deque[StreamItem] = deque(maxlen=MAX_ITEMS)
        self._classification_service = ClassificationService()
        self._store = SQLiteStore(DB_PATH)
        self._seen_ids: set[str] = self._store.all_ids()
        self._condition = asyncio.Condition()
        self._errors: deque[str] = deque(maxlen=50)
        self._last_poll_started_at: datetime | None = None
        self._last_poll_finished_at: datetime | None = None
        self._last_poll_new_items = 0
        for item in reversed(self._store.recent_items(limit=MAX_ITEMS)):
            self._items.append(item)

    def recent_items(self, limit: int = 50) -> list[StreamItem]:
        db_items = self._deduped_recent_items(limit=limit)
        self._items = deque(reversed(db_items), maxlen=MAX_ITEMS)
        return db_items

    def localized_items(self, items: list[StreamItem], lang: str = "en") -> list[StreamItem]:
        if lang.startswith("zh"):
            return self._store.ensure_chinese_for_items(items)
        return items

    def history_items(
        self,
        limit: int = 50,
        offset: int = 0,
        source_category: str | None = None,
        source_region: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> list[StreamItem]:
        return self._store.query_items(
            limit=limit,
            offset=offset,
            source_category=source_category,
            source_region=source_region,
            start_at=start_at,
            end_at=end_at,
        )

    def recent_errors(self) -> list[str]:
        return list(self._errors)

    def search_items(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0,
        source_category: str | None = None,
        source_region: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> list[StreamItem]:
        return self._store.search_items(
            query=query,
            limit=limit,
            offset=offset,
            source_category=source_category,
            source_region=source_region,
            start_at=start_at,
            end_at=end_at,
        )

    def health_status(self) -> dict[str, object]:
        latest = self._store.recent_items(limit=1)
        latest_item = latest[0] if latest else None
        return {
            "status": "ok",
            "classifier_mode": CLASSIFIER_MODE,
            "classifier_model": OLLAMA_MODEL if CLASSIFIER_MODE == "ollama" else "heuristic",
            "sources_configured": len(SOURCES),
            "stored_items": len(self._seen_ids),
            "recent_error_count": len(self._errors),
            "recent_errors": list(self._errors)[-5:],
            "last_poll_started_at": self._last_poll_started_at.isoformat() if self._last_poll_started_at else None,
            "last_poll_finished_at": self._last_poll_finished_at.isoformat() if self._last_poll_finished_at else None,
            "last_poll_new_items": self._last_poll_new_items,
            "latest_item_published_at": latest_item.published_at.isoformat() if latest_item else None,
            "latest_item_title": latest_item.title if latest_item else None,
        }

    def high_priority_items(self, limit: int = 25, lang: str = "en") -> list[dict[str, object]]:
        items = self.localized_items(self._deduped_recent_items(limit=200), lang=lang)
        ranked = [
            (priority_score(item), item)
            for item in items
            if is_high_priority(item)
        ]
        ranked.sort(key=lambda pair: (pair[0], pair[1].published_at), reverse=True)
        selected: list[dict[str, object]] = []
        seen_signatures: list[tuple[datetime, str, set[str]]] = []
        for score, item in ranked:
            if self._is_duplicate_signature(item.published_at, item.title, seen_signatures):
                continue
            seen_signatures.append((item.published_at, self._normalized_title(item.title), self._title_tokens(item.title)))
            selected.append({**item.as_dict(lang), "priority_score": score})
            if len(selected) >= limit:
                break
        return selected

    def trader_focus_items(self, limit: int = 8, lang: str = "en") -> list[dict[str, object]]:
        items = self.localized_items(self._deduped_recent_items(limit=250), lang=lang)
        ranked: list[tuple[int, StreamItem]] = []
        for item in items:
            classification = item.classification
            if not classification:
                continue
            haystack = f"{item.title} {item.summary}".lower()
            score = 0
            score += priority_score(item)
            if classification.primary_label in {
                "market_driver",
                "hot_stock_alert",
                "earnings_guidance",
                "policy_regulation",
                "war_geopolitics",
                "energy_commodities",
            }:
                score += 4
            if classification.impact_level == "critical":
                score += 4
            elif classification.impact_level == "high":
                score += 2
            if any(term in haystack for term in ("trump", "tariff", "china", "taiwan", "fomc", "cpi", "nonfarm", "opec", "oil")):
                score += 3
            if item.source_category == "filings":
                score -= 4
            ranked.append((score, item))

        ranked.sort(key=lambda pair: (pair[0], pair[1].published_at), reverse=True)
        seen_signatures: list[tuple[datetime, str, set[str]]] = []
        selected: list[dict[str, object]] = []
        for score, item in ranked:
            if self._is_duplicate_signature(item.published_at, item.title, seen_signatures):
                continue
            seen_signatures.append((item.published_at, self._normalized_title(item.title), self._title_tokens(item.title)))
            selected.append(
                {
                    **item.as_dict(lang),
                    "priority_score": score,
                }
            )
            if len(selected) >= limit:
                break
        return selected

    def now_moving_sections(self, limit_per_section: int = 3, lang: str = "en") -> dict[str, list[dict[str, object]]]:
        items = self.trader_focus_items(limit=24, lang=lang)
        sections: dict[str, list[dict[str, object]]] = {
            "macro_now": [],
            "stock_now": [],
            "geopolitics_now": [],
        }

        for item in items:
            classification = item.get("classification") or {}
            label = classification.get("primary_label", "")
            title = str(item.get("title", "")).lower()
            summary = str(item.get("summary", "")).lower()
            haystack = f"{title} {summary}"

            if (
                len(sections["macro_now"]) < limit_per_section
                and (
                    label in {"market_driver", "policy_regulation", "energy_commodities"}
                    or any(term in haystack for term in ("fomc", "fed", "cpi", "ppi", "nonfarm", "payroll", "yield", "treasury", "dollar"))
                )
            ):
                sections["macro_now"].append(item)
                continue

            if (
                len(sections["geopolitics_now"]) < limit_per_section
                and (
                    label in {"war_geopolitics", "policy_regulation"}
                    or any(term in haystack for term in ("trump", "china", "taiwan", "tariff", "sanction", "iran", "israel", "russia", "ukraine", "oil"))
                )
            ):
                sections["geopolitics_now"].append(item)
                continue

            if len(sections["stock_now"]) < limit_per_section:
                sections["stock_now"].append(item)

        return sections

    def retail_sections(self, limit_per_section: int = 6, lang: str = "en") -> dict[str, list[dict[str, object]]]:
        items = self.localized_items(self._deduped_recent_items(limit=250), lang=lang)
        return build_retail_sections(items, limit_per_section=limit_per_section)

    async def retail_snapshot(self, limit_per_section: int = 5, lang: str = "en") -> dict[str, object]:
        items = self.localized_items(self._deduped_recent_items(limit=300), lang=lang)
        try:
            movers = await fetch_watchlist_movers()
        except Exception as exc:
            self._errors.append(f"Pre-market movers: {exc}")
            movers = []
        if not movers:
            movers = build_prepost_news(items, limit=5)
        return {
            "sections": build_retail_sections(items, limit_per_section=limit_per_section),
            "prepost_movers": movers,
        }

    async def upcoming_events(self) -> list[UpcomingEvent]:
        return await fetch_upcoming_events()

    async def poll_once(self) -> int:
        self._last_poll_started_at = datetime.now()
        items, errors = await fetch_all_sources(SOURCES)
        if errors:
            self._errors.extend(errors)
        items = await self._classification_service.classify_items_async(items)

        seen_signatures = [
            (item.published_at, self._normalized_title(item.title), self._title_tokens(item.title))
            for item in self._store.recent_items(limit=300)
        ]
        fresh: list[StreamItem] = []
        for item in sorted(items, key=lambda candidate: candidate.published_at):
            if item.item_id in self._seen_ids:
                continue
            if self._is_duplicate_signature(item.published_at, item.title, seen_signatures):
                continue
            self._seen_ids.add(item.item_id)
            self._items.append(item)
            fresh.append(item)
            seen_signatures.append((item.published_at, self._normalized_title(item.title), self._title_tokens(item.title)))

        self._store.insert_items(fresh)

        if fresh:
            async with self._condition:
                self._condition.notify_all()
        self._last_poll_new_items = len(fresh)
        self._last_poll_finished_at = datetime.now()
        return len(fresh)

    async def run_forever(self) -> None:
        while True:
            try:
                await self.poll_once()
            except Exception as exc:  # pragma: no cover
                self._errors.append(str(exc))
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    async def stream(self, lang: str = "en") -> AsyncIterator[str]:
        sent_ids: set[str] = set()
        backlog = self.localized_items(self.recent_items(limit=30), lang=lang)
        for item in reversed(backlog):
            sent_ids.add(item.item_id)
            yield self._format_sse("item", item.as_dict(lang))

        while True:
            async with self._condition:
                await self._condition.wait()

            for item in reversed(self.localized_items(self.recent_items(limit=30), lang=lang)):
                if item.item_id in sent_ids:
                    continue
                sent_ids.add(item.item_id)
                yield self._format_sse("item", item.as_dict(lang))

    @staticmethod
    def _format_sse(event: str, payload: dict[str, object]) -> str:
        return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def _deduped_recent_items(self, limit: int, sample_multiplier: int = 4) -> list[StreamItem]:
        sample_size = max(limit * sample_multiplier, limit)
        raw_items = self._store.recent_items(limit=sample_size)
        selected: list[StreamItem] = []
        seen_signatures: list[tuple[datetime, str, set[str]]] = []
        for item in raw_items:
            if self._is_duplicate_signature(item.published_at, item.title, seen_signatures):
                continue
            selected.append(item)
            seen_signatures.append((item.published_at, self._normalized_title(item.title), self._title_tokens(item.title)))
            if len(selected) >= limit:
                break
        return selected

    @staticmethod
    def _normalized_title(title: str) -> str:
        text = title.lower()
        text = text.replace("'s", " ")
        text = re.sub(r"&", " and ", text)
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def _title_tokens(title: str) -> set[str]:
        tokens = {
            token
            for token in NewsStreamService._normalized_title(title).split()
            if len(token) > 2 and token not in TITLE_STOPWORDS
        }
        return tokens

    @staticmethod
    def _titles_similar(normalized_a: str, tokens_a: set[str], normalized_b: str, tokens_b: set[str]) -> bool:
        if normalized_a == normalized_b:
            return True
        if not tokens_a or not tokens_b:
            return False
        intersection = tokens_a & tokens_b
        shorter = min(len(tokens_a), len(tokens_b))
        union = len(tokens_a | tokens_b)
        if shorter >= 4 and len(intersection) >= max(4, int(shorter * 0.75)):
            return True
        if union and (len(intersection) / union) >= 0.72 and len(intersection) >= 4:
            return True
        return False

    @staticmethod
    def _is_duplicate_signature(
        published_at: datetime,
        title: str,
        seen_signatures: list[tuple[datetime, str, set[str]]],
        window_hours: int = 6,
    ) -> bool:
        normalized = NewsStreamService._normalized_title(title)
        tokens = NewsStreamService._title_tokens(title)
        for seen_published_at, seen_normalized, seen_tokens in seen_signatures:
            if abs((published_at - seen_published_at).total_seconds()) > window_hours * 3600:
                continue
            if NewsStreamService._titles_similar(normalized, tokens, seen_normalized, seen_tokens):
                return True
        return False

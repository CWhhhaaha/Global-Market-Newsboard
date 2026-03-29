from __future__ import annotations

import sqlite3
from json import dumps, loads
from datetime import datetime, timezone
from pathlib import Path

from .classifier import ClassificationResult
from .classification_service import ClassificationService
from .config import MAX_STORED_ITEMS, SEC_ALWAYS_KEEP_FORMS, SEC_EVENT_KEYWORDS
from .filing_filter import is_top_100_market_cap_filing
from .models import StreamItem
from .translation import contains_cjk, needs_chinese_translation, translate_text_to_chinese


class SQLiteStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._classification_service = ClassificationService()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    source_name TEXT NOT NULL,
                    source_category TEXT NOT NULL,
                    source_region TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    title_zh TEXT NOT NULL DEFAULT '',
                    summary_zh TEXT NOT NULL DEFAULT '',
                    url TEXT NOT NULL,
                    source_homepage TEXT NOT NULL,
                    published_at TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    matched_terms TEXT NOT NULL,
                    classification_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_alerts_published_at
                ON alerts (published_at DESC)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_alerts_source_category
                ON alerts (source_category)
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(alerts)").fetchall()
            }
            if "classification_json" not in columns:
                connection.execute(
                    "ALTER TABLE alerts ADD COLUMN classification_json TEXT NOT NULL DEFAULT '{}'"
                )
            if "title_zh" not in columns:
                connection.execute(
                    "ALTER TABLE alerts ADD COLUMN title_zh TEXT NOT NULL DEFAULT ''"
                )
            if "summary_zh" not in columns:
                connection.execute(
                    "ALTER TABLE alerts ADD COLUMN summary_zh TEXT NOT NULL DEFAULT ''"
                )
            self._prune_noisy_filings(connection)
            self._refresh_classification(connection)

    def insert_items(self, items: list[StreamItem]) -> None:
        if not items:
            return
        rows = [
            (
                item.item_id,
                item.source_name,
                item.source_category,
                item.source_region,
                item.title,
                item.summary,
                item.title_zh or self._translate_if_needed(item.title),
                item.summary_zh,
                item.url,
                item.source_homepage,
                item.published_at.isoformat(),
                item.fetched_at.isoformat(),
                "\t".join(item.matched_terms),
                dumps(ClassificationService.serialize(item.classification), ensure_ascii=False),
            )
            for item in items
        ]
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT OR IGNORE INTO alerts (
                    id, source_name, source_category, source_region,
                    title, summary, title_zh, summary_zh, url, source_homepage,
                    published_at, fetched_at, matched_terms, classification_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            self._prune_old_rows(connection, keep=MAX_STORED_ITEMS)

    def recent_items(self, limit: int = 50) -> list[StreamItem]:
        return self.query_items(limit=limit)

    def query_items(
        self,
        limit: int = 50,
        offset: int = 0,
        source_category: str | None = None,
        source_region: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> list[StreamItem]:
        sql = """
            SELECT *
            FROM alerts
            WHERE 1 = 1
        """
        params: list[object] = []
        if source_category:
            sql += " AND source_category = ?"
            params.append(source_category)
        if source_region:
            sql += " AND source_region = ?"
            params.append(source_region)
        if start_at:
            sql += " AND published_at >= ?"
            params.append(start_at.astimezone(timezone.utc).isoformat())
        if end_at:
            sql += " AND published_at <= ?"
            params.append(end_at.astimezone(timezone.utc).isoformat())
        sql += " ORDER BY published_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._connect() as connection:
            rows = connection.execute(
                sql,
                params,
            ).fetchall()
        return [self._row_to_item(row) for row in rows]

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
        pattern = f"%{query.strip()}%"
        with self._connect() as connection:
            if contains_cjk(query):
                self._backfill_chinese_fields(connection, limit=8)
            sql = """
                SELECT *
                FROM alerts
                WHERE (
                    title LIKE ?
                    OR summary LIKE ?
                    OR title_zh LIKE ?
                    OR summary_zh LIKE ?
                    OR matched_terms LIKE ?
                    OR source_name LIKE ?
                )
            """
            params: list[object] = [pattern, pattern, pattern, pattern, pattern, pattern]
            if source_category:
                sql += " AND source_category = ?"
                params.append(source_category)
            if source_region:
                sql += " AND source_region = ?"
                params.append(source_region)
            if start_at:
                sql += " AND published_at >= ?"
                params.append(start_at.astimezone(timezone.utc).isoformat())
            if end_at:
                sql += " AND published_at <= ?"
                params.append(end_at.astimezone(timezone.utc).isoformat())
            sql += " ORDER BY published_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            rows = connection.execute(sql, params).fetchall()
        return [self._row_to_item(row) for row in rows]

    def ensure_chinese_for_items(self, items: list[StreamItem], limit: int = 12) -> list[StreamItem]:
        remaining = limit
        updates: list[tuple[str, str, str]] = []
        for item in items:
            if remaining <= 0:
                break
            changed = False
            if not item.title_zh:
                item.title_zh = self._translate_if_needed(item.title)
                changed = True
            if changed:
                remaining -= 1
                updates.append((item.title_zh, item.summary_zh, item.item_id))
        if updates:
            with self._connect() as connection:
                connection.executemany(
                    """
                    UPDATE alerts
                    SET title_zh = ?, summary_zh = ?
                    WHERE id = ?
                    """,
                    updates,
                )
        return items

    def all_ids(self) -> set[str]:
        with self._connect() as connection:
            rows = connection.execute("SELECT id FROM alerts").fetchall()
        return {row["id"] for row in rows}

    @staticmethod
    def _row_to_item(row: sqlite3.Row) -> StreamItem:
        return StreamItem(
            source_name=row["source_name"],
            source_category=row["source_category"],
            source_region=row["source_region"],
            title=row["title"],
            summary=row["summary"],
            title_zh=row["title_zh"],
            summary_zh=row["summary_zh"],
            url=row["url"],
            source_homepage=row["source_homepage"],
            published_at=datetime.fromisoformat(row["published_at"]),
            fetched_at=datetime.fromisoformat(row["fetched_at"]),
            matched_terms=[term for term in row["matched_terms"].split("\t") if term],
            classification=SQLiteStore._classification_from_json(row["classification_json"]),
        )

    @staticmethod
    def _prune_old_rows(connection: sqlite3.Connection, keep: int) -> None:
        connection.execute(
            """
            DELETE FROM alerts
            WHERE id IN (
                SELECT id
                FROM alerts
                ORDER BY published_at DESC
                LIMIT -1 OFFSET ?
            )
            """,
            (keep,),
        )

    @staticmethod
    def _prune_noisy_filings(connection: sqlite3.Connection) -> None:
        filing_rows = connection.execute(
            """
            SELECT id, title, summary
            FROM alerts
            WHERE source_category = 'filings'
            """
        ).fetchall()
        delete_ids = [
            row["id"]
            for row in filing_rows
            if "8-k" not in row["title"].lower() or not is_top_100_market_cap_filing(row["title"], row["summary"])
        ]
        if delete_ids:
            connection.executemany(
                "DELETE FROM alerts WHERE id = ?",
                [(item_id,) for item_id in delete_ids],
            )

        keep_clauses: list[str] = []
        params: list[object] = []

        for form in SEC_ALWAYS_KEEP_FORMS:
            keep_clauses.extend([
                "lower(title) LIKE ?",
                "lower(summary) LIKE ?",
            ])
            like = f"%{form}%"
            params.extend([like, like])

        for term in SEC_EVENT_KEYWORDS:
            keep_clauses.extend([
                "lower(title) LIKE ?",
                "lower(summary) LIKE ?",
            ])
            like = f"%{term}%"
            params.extend([like, like])

        sql = f"""
            DELETE FROM alerts
            WHERE source_category = 'filings'
            AND NOT ({' OR '.join(keep_clauses)})
        """
        connection.execute(sql, params)

    def _refresh_classification(self, connection: sqlite3.Connection) -> None:
        rows = connection.execute(
            """
            SELECT *
            FROM alerts
            """
        ).fetchall()
        if not rows:
            return

        items = [self._row_to_item(row) for row in rows]
        items = self._classification_service.classify_items(items)
        connection.executemany(
            """
            UPDATE alerts
            SET classification_json = ?
            WHERE id = ?
            """,
            [
                (
                    dumps(ClassificationService.serialize(item.classification), ensure_ascii=False),
                    item.item_id,
                )
                for item in items
            ],
        )

    def _backfill_chinese_fields(self, connection: sqlite3.Connection, limit: int = 120) -> None:
        rows = connection.execute(
            """
            SELECT id, title, summary, title_zh, summary_zh
            FROM alerts
            WHERE title_zh = '' OR summary_zh = ''
            ORDER BY published_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        if not rows:
            return

        updates: list[tuple[str, str, str]] = []
        for row in rows:
            title_zh = row["title_zh"] or self._translate_if_needed(row["title"])
            summary_zh = row["summary_zh"] or self._translate_if_needed(row["summary"])
            updates.append((title_zh, summary_zh, row["id"]))

        connection.executemany(
            """
            UPDATE alerts
            SET title_zh = ?, summary_zh = ?
            WHERE id = ?
            """,
            updates,
        )

    @staticmethod
    def _translate_if_needed(text: str) -> str:
        if not needs_chinese_translation(text):
            return text
        return translate_text_to_chinese(text)

    @staticmethod
    def _classification_from_json(raw: str) -> ClassificationResult | None:
        if not raw or raw == "{}":
            return None
        payload = loads(raw)
        return ClassificationResult(
            primary_label=payload.get("primary_label", "unclassified"),
            impact_direction=payload.get("impact_direction", "watch"),
            impact_level=payload.get("impact_level", "low"),
            affected_targets=list(payload.get("affected_targets", [])),
            secondary_labels=list(payload.get("secondary_labels", [])),
            confidence=float(payload.get("confidence", 0.0)),
            rationale=payload.get("rationale", ""),
        )

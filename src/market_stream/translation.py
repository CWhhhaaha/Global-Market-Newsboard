from __future__ import annotations

import json
import re
from functools import lru_cache
from urllib.parse import urlencode

import httpx

CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
LATIN_RE = re.compile(r"[A-Za-z]")

TRANSLATION_TIMEOUT_SECONDS = 8.0
GOOGLE_TRANSLATE_ENDPOINT = "https://translate.googleapis.com/translate_a/single"

TERM_OVERRIDES = {
    "fed": "美联储",
    "federal reserve": "美联储",
    "treasury": "美国财政部",
    "yield": "收益率",
    "oil": "原油",
    "crude": "原油",
    "gold": "黄金",
    "silver": "白银",
    "dollar": "美元",
    "tariff": "关税",
    "sanction": "制裁",
    "earnings": "财报",
    "guidance": "业绩指引",
    "pre-market": "盘前",
    "after-hours": "盘后",
    "after hours": "盘后",
}


def contains_cjk(text: str) -> bool:
    return bool(CJK_RE.search(text or ""))


def needs_chinese_translation(text: str) -> bool:
    cleaned = (text or "").strip()
    if not cleaned:
        return False
    if contains_cjk(cleaned):
        return False
    return bool(LATIN_RE.search(cleaned))


def _apply_term_overrides(text: str) -> str:
    translated = text
    lowered = translated.lower()
    for source, target in TERM_OVERRIDES.items():
        if source in lowered:
            translated = re.sub(
                re.escape(source),
                target,
                translated,
                flags=re.IGNORECASE,
            )
            lowered = translated.lower()
    return translated


@lru_cache(maxsize=4096)
def translate_text_to_chinese(text: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return ""
    if not needs_chinese_translation(cleaned):
        return cleaned

    params = {
        "client": "gtx",
        "sl": "auto",
        "tl": "zh-CN",
        "dt": "t",
        "q": cleaned,
    }
    url = f"{GOOGLE_TRANSLATE_ENDPOINT}?{urlencode(params)}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
        )
    }

    try:
        with httpx.Client(timeout=TRANSLATION_TIMEOUT_SECONDS, follow_redirects=True, headers=headers) as client:
            response = client.get(url)
            response.raise_for_status()
        payload = json.loads(response.text)
        segments = payload[0] if payload and isinstance(payload, list) else []
        translated = "".join(
            segment[0]
            for segment in segments
            if isinstance(segment, list) and segment and isinstance(segment[0], str)
        ).strip()
        if translated:
            return _apply_term_overrides(translated)
    except Exception:
        pass

    return _apply_term_overrides(cleaned)

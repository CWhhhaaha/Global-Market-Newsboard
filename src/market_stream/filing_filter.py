from __future__ import annotations

import re

from .config import TOP_100_MARKET_CAP_ISSUERS

NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
LEGAL_SUFFIX_RE = re.compile(
    r"\b(inc|corp|corporation|co|company|group|holdings|holding|plc|ltd|limited|nv|se|sa|ag)\b"
)


def _clean(value: str) -> str:
    value = value.lower().replace("&", " and ")
    value = value.replace("`", "'")
    value = NON_ALNUM_RE.sub(" ", value)
    return value.strip()


def _normalize(value: str) -> str:
    value = _clean(value)
    value = LEGAL_SUFFIX_RE.sub(" ", value)
    value = NON_ALNUM_RE.sub(" ", value)
    return value.strip()


def _issuer_aliases() -> dict[str, dict[str, tuple[str, ...]]]:
    aliases: dict[str, dict[str, tuple[str, ...]]] = {}
    for symbol, name in TOP_100_MARKET_CAP_ISSUERS.items():
        symbol_aliases = (symbol.lower(),)
        normalized_name = _normalize(name)
        cleaned_name = _clean(name)
        name_aliases: set[str] = set()
        if cleaned_name:
            cleaned_words = cleaned_name.split()
            if len(cleaned_name) >= 6:
                name_aliases.add(cleaned_name)
            if len(cleaned_words) >= 2:
                name_aliases.add(" ".join(cleaned_words[:2]))
            if len(cleaned_words) >= 3:
                name_aliases.add(" ".join(cleaned_words[:3]))
        elif normalized_name:
            words = normalized_name.split()
            if len(normalized_name) >= 4:
                name_aliases.add(normalized_name)
            if len(words) >= 2:
                name_aliases.add(" ".join(words[:2]))
            if len(words) >= 3:
                name_aliases.add(" ".join(words[:3]))
        aliases[symbol] = {
            "symbols": tuple(alias for alias in symbol_aliases if alias and (len(alias) >= 3 or "." in alias)),
            "names": tuple(alias for alias in name_aliases if alias and len(alias) >= 4),
        }
    return aliases


TOP_ISSUER_ALIASES = _issuer_aliases()


def is_top_100_market_cap_filing(title: str, summary: str) -> bool:
    normalized_title = _clean(title)
    lowered_title = title.lower()
    for aliases in TOP_ISSUER_ALIASES.values():
        for alias in aliases["symbols"]:
            if re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", lowered_title):
                return True
        for alias in aliases["names"]:
            if alias in normalized_title:
                return True
    return False

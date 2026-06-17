from __future__ import annotations

import hashlib
import re
from typing import Optional

from bs4 import BeautifulSoup


def _strip_html(text: str) -> str:
    if not text:
        return ""
    if "<" in text and ">" in text:
        try:
            return BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
        except Exception:
            # fallback simple strip
            return re.sub(r"<[^>]+>", " ", text)
    return text


def _normalize_field(text: Optional[str]) -> str:
    if not text:
        return ""
    text = text.lower()
    text = _strip_html(text)
    # Replace non-breaking spaces and similar
    text = text.replace("\u00a0", " ").replace("\r\n", " ").replace("\n", " ")
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Remove special characters except basic punctuation and spaces
    text = re.sub(r"[^0-9a-zA-Z \-.,']+", "", text)
    return text


def generate_content_hash(title: Optional[str], company_slug: Optional[str], location: Optional[str], description: Optional[str]) -> str:
    """Generate a SHA-256 hex digest for job content deduplication.

    Normalizes inputs and hashes the concatenation of
    `company_slug + normalized_title + normalized_location + truncated_description`.
    """
    slug = _normalize_field(company_slug or "")
    title_n = _normalize_field(title or "")
    loc_n = _normalize_field(location or "")
    desc = _strip_html(description or "")
    desc = re.sub(r"\s+", " ", desc).strip()
    desc = re.sub(r"[^0-9a-zA-Z \-.,']+", "", desc)
    desc_trunc = desc[:500]

    combined = f"{slug}|{title_n}|{loc_n}|{desc_trunc}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()

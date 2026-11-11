"""
src/aggregator/deduplicator.py - Article URL and content deduplication with
SHA-256 state caching and atomic persistence in data/seen_articles.json.
"""

import os
import json
import hashlib
import logging
import unicodedata
import tempfile
from typing import List, Dict, Set, Optional, Union, Any
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from datetime import datetime, timezone
import threading

logger = logging.getLogger(__name__)

# Tracking parameters to strip from URLs during normalization
TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "fbclid",
    "gclid",
    "ref",
    "source",
    "feed",
    "oc",
    "ceid",
}


def normalize_url(url: str) -> str:
    """
    Normalizes article URL by stripping query tracking parameters,
    normalizing scheme and host to lowercase, sorting query parameters,
    and trimming trailing slashes.
    """
    if not url:
        return ""

    url = url.strip()
    try:
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip("/")

        # Filter query params
        query_pairs = parse_qsl(parsed.query, keep_blank_values=False)
        cleaned_pairs = [
            (k, v) for k, v in query_pairs if k.lower() not in TRACKING_PARAMS
        ]
        cleaned_pairs.sort(key=lambda x: x[0])
        new_query = urlencode(cleaned_pairs)

        # Normalize back
        return urlunparse((scheme, netloc, path, "", new_query, ""))
    except Exception as e:
        logger.warning("Error normalizing URL '%s': %s", url, e)
        return url.strip()


def normalize_title(title: str) -> str:
    """
    Normalizes article title: strips whitespace, normalizes Unicode (NFC),
    and strips common publication title suffixes.
    """
    if not title:
        return ""
    # Unicode NFC normalization
    t = unicodedata.normalize("NFC", title).strip()
    # Strip common news source suffixes
    t = t.split(" - ")[0].split(" | ")[0].strip()
    return t


def compute_article_hash(url: str, title: str = "", source_id: str = "") -> str:
    """
    Computes deterministic SHA-256 hash for an article.
    Prioritizes normalized URL; if URL is empty, hashes normalized title + source_id.
    """
    norm_url = normalize_url(url)
    if norm_url:
        return hashlib.sha256(norm_url.encode("utf-8")).hexdigest()

    norm_title = normalize_title(title)
    key = f"{source_id}:{norm_title}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


class Deduplicator:
    """
    Persistent deduplication cache tracking seen article hashes in data/seen_articles.json.
    Thread-safe with atomic file writes to prevent cache corruption.
    """

    def __init__(
        self,
        filepath: str = "data/seen_articles.json",
        max_entries: int = 5000,
    ):
        self.filepath = os.path.abspath(filepath)
        self.max_entries = max_entries
        self._lock = threading.Lock()
        self._seen_hashes: Dict[str, Dict[str, Any]] = {}
        self.load()

    def is_seen(self, item: Any) -> bool:
        """
        Check if an article, URL, or hash has already been seen.
        Accepts: RawArticle, ProcessedArticle, URL string, or hex hash string.
        """
        hash_val = self._extract_hash(item)
        with self._lock:
            return hash_val in self._seen_hashes

    def mark_seen(self, item: Any, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Marks an article as seen and stores it in cache.
        Returns the computed SHA-256 hash.
        """
        hash_val = self._extract_hash(item)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if not isinstance(item, str):
            if hasattr(item, "source_url"):
                record["url"] = str(item.source_url)
            if hasattr(item, "original_title"):
                record["title"] = str(item.original_title)
            elif hasattr(item, "title"):
                record["title"] = str(item.title)
            if hasattr(item, "source_id"):
                record["source_id"] = str(item.source_id)
        else:
            if item.startswith("http://") or item.startswith("https://"):
                record["url"] = item

        if metadata:
            record.update(metadata)

        with self._lock:
            self._seen_hashes[hash_val] = record
            if len(self._seen_hashes) > self.max_entries:
                self._prune_locked()

        self.save()
        return hash_val

    def filter_unseen(self, articles: List[Any]) -> List[Any]:
        """
        Filters a list of articles, returning only those that have not been seen before.
        Also prevents duplicate items within the current batch.
        """
        unseen: List[Any] = []
        batch_seen: Set[str] = set()

        for article in articles:
            h = self._extract_hash(article)
            with self._lock:
                already_in_cache = h in self._seen_hashes
            if not already_in_cache and h not in batch_seen:
                batch_seen.add(h)
                unseen.append(article)

        return unseen

    def _extract_hash(self, item: Any) -> str:
        """Helper to extract or compute SHA-256 hash from diverse item types."""
        if not isinstance(item, str) and hasattr(item, "source_url"):
            raw_title = getattr(item, "original_title", "")
            if not raw_title and hasattr(item, "title"):
                t = getattr(item, "title")
                raw_title = str(t) if not callable(t) else ""
            return compute_article_hash(
                url=getattr(item, "source_url", ""),
                title=raw_title,
                source_id=getattr(item, "source_id", ""),
            )
        elif isinstance(item, str):
            clean = item.strip()
            # If already 64-char hex string, treat as hash
            if len(clean) == 64 and all(c in "0123456789abcdefABCDEF" for c in clean):
                return clean.lower()
            return compute_article_hash(clean)
        return hashlib.sha256(str(item).encode("utf-8")).hexdigest()

    def load(self) -> None:
        """Loads cached seen hashes from disk."""
        with self._lock:
            if not os.path.exists(self.filepath):
                self._seen_hashes = {}
                return

            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        # Format 1: {"version": 1, "hashes": {...}}
                        if "hashes" in data and isinstance(data["hashes"], dict):
                            self._seen_hashes = data["hashes"]
                        # Format 2: raw dict of hashes
                        else:
                            self._seen_hashes = data
                    elif isinstance(data, list):
                        # Format 3: list of hash strings
                        self._seen_hashes = {h: {"timestamp": ""} for h in data if isinstance(h, str)}
                    else:
                        self._seen_hashes = {}
            except Exception as e:
                logger.warning("Could not read seen articles cache %s: %s", self.filepath, e)
                self._seen_hashes = {}

    def save(self) -> None:
        """Atomically saves seen hashes to disk in a thread-safe manner."""
        with self._lock:
            data_to_write = {
                "version": 1,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "count": len(self._seen_hashes),
                "hashes": self._seen_hashes,
            }

            dirname = os.path.dirname(self.filepath)
            os.makedirs(dirname, exist_ok=True)
            base_name = os.path.basename(self.filepath)

            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    dir=dirname,
                    prefix=f".{base_name}.",
                    suffix=".tmp",
                    delete=False,
                ) as tmp_file:
                    tmp_path = tmp_file.name
                    json.dump(data_to_write, tmp_file, ensure_ascii=False, indent=2)
                    tmp_file.flush()
                    os.fsync(tmp_file.fileno())

                os.replace(tmp_path, self.filepath)
            except Exception as e:
                logger.error("Failed to save seen articles cache: %s", e)
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass

    def clear(self) -> None:
        """Clears all seen articles from memory and disk."""
        with self._lock:
            self._seen_hashes.clear()
        self.save()

    def count(self) -> int:
        """Returns the number of seen articles in cache."""
        with self._lock:
            return len(self._seen_hashes)

    def _prune_locked(self) -> None:
        """Prunes oldest entries when cache exceeds max_entries (called under lock)."""
        if len(self._seen_hashes) <= self.max_entries:
            return
        # Keep most recent entries
        excess = len(self._seen_hashes) - self.max_entries
        keys_to_remove = list(self._seen_hashes.keys())[:excess]
        for k in keys_to_remove:
            self._seen_hashes.pop(k, None)

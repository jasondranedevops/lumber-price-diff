"""
lumber_compare.py
Core logic: fetch lumber prices from Home Depot via SerpApi,
compare two ZIP codes, and return structured results.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default lumber SKUs to compare
# ---------------------------------------------------------------------------
DEFAULT_QUERIES: list[str] = [
    "2x4x8 framing lumber",
    "2x6x8 lumber",
    "4x4x8 post",
    "2x4x96 stud",
    "OSB sheathing 4x8",
    "plywood 4x8 sheet",
]

SERPAPI_BASE = "https://serpapi.com/search"

# ---------------------------------------------------------------------------
# Response cache (file-based, TTL-keyed)
# ---------------------------------------------------------------------------
_CACHE_DIR = Path(".cache") / "lumber_prices"


def _cache_key(query: str, zip_code: str) -> str:
    return hashlib.md5(f"{query}:{zip_code}".encode()).hexdigest()


def _cache_get(query: str, zip_code: str, ttl: int) -> Optional[list[dict]]:
    if ttl <= 0:
        return None
    path = _CACHE_DIR / f"{_cache_key(query, zip_code)}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        if time.time() - data["timestamp"] < ttl:
            return data["products"]
    except Exception:
        pass
    return None


def _cache_set(query: str, zip_code: str, products: list[dict]) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path = _CACHE_DIR / f"{_cache_key(query, zip_code)}.json"
        path.write_text(json.dumps({"timestamp": time.time(), "products": products}))
    except Exception as exc:
        logger.debug("Cache write failed: %s", exc)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class ProductPrice:
    query: str
    zip1: Optional[float]
    zip2: Optional[float]
    delta: Optional[float] = field(init=False)

    def __post_init__(self) -> None:
        if self.zip1 is not None and self.zip2 is not None:
            self.delta = round(self.zip2 - self.zip1, 2)
        else:
            self.delta = None

    @property
    def zip2_is_pricier(self) -> Optional[bool]:
        if self.delta is None:
            return None
        return self.delta > 0


# ---------------------------------------------------------------------------
# SerpApi helpers
# ---------------------------------------------------------------------------

def _serpapi_request(
    query: str,
    zip_code: str,
    api_key: str,
    timeout: int = 15,
    max_retries: int = 3,
) -> list[dict]:
    """Fetch raw product list from SerpApi with exponential-backoff retry."""
    params = {
        "engine": "home_depot",
        "q": query,
        "delivery_zip": zip_code,
        "store_zip": zip_code,
        "api_key": api_key,
    }
    url = f"{SERPAPI_BASE}?{urllib.parse.urlencode(params)}"

    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                data = json.loads(resp.read())
            return data.get("products", [])
        except urllib.error.HTTPError as exc:
            if exc.code < 500:
                # 4xx errors (auth, bad request) — don't retry
                logger.warning("SerpApi HTTP %d for '%s' @ %s: %s", exc.code, query, zip_code, exc)
                return []
            logger.warning(
                "SerpApi HTTP %d for '%s' @ %s (attempt %d/%d)",
                exc.code, query, zip_code, attempt + 1, max_retries,
            )
        except Exception as exc:
            logger.warning(
                "SerpApi error for '%s' @ %s (attempt %d/%d): %s",
                query, zip_code, attempt + 1, max_retries, exc,
            )

        if attempt < max_retries - 1:
            delay = 2 ** attempt
            logger.debug("Retrying in %ds…", delay)
            time.sleep(delay)

    logger.error("SerpApi failed for '%s' @ %s after %d attempts", query, zip_code, max_retries)
    return []


def _extract_price(product: dict) -> Optional[float]:
    """Pull the lowest available price from a SerpApi product dict."""
    for key in ("price", "raw_price", "sale_price"):
        val = product.get(key)
        if val is not None:
            try:
                return float(str(val).replace("$", "").replace(",", ""))
            except ValueError:
                pass
    pricing = product.get("pricing") or {}
    for key in ("price", "sale_price"):
        val = pricing.get(key)
        if val is not None:
            try:
                return float(str(val).replace("$", "").replace(",", ""))
            except ValueError:
                pass
    return None


def fetch_price(
    query: str,
    zip_code: str,
    api_key: str,
    top_n: int = 3,
    cache_ttl: int = 3600,
) -> Optional[float]:
    """Return the minimum valid price from the top N results for a query+ZIP.

    Results are cached locally for *cache_ttl* seconds (0 disables caching).
    """
    cached = _cache_get(query, zip_code, cache_ttl)
    if cached is not None:
        logger.debug("Cache hit for '%s' @ %s", query, zip_code)
        products = cached
    else:
        products = _serpapi_request(query, zip_code, api_key)
        _cache_set(query, zip_code, products)

    prices = [p for product in products[:top_n] if (p := _extract_price(product)) is not None]
    return min(prices) if prices else None


# ---------------------------------------------------------------------------
# Main comparison function
# ---------------------------------------------------------------------------

def compare_lumber_prices(
    zip1: str,
    zip2: str,
    api_key: str,
    queries: Optional[list[str]] = None,
    cache_ttl: int = 3600,
    fetcher: Optional[Callable[[str, str, str], Optional[float]]] = None,
) -> list[ProductPrice]:
    """
    Compare Home Depot lumber prices between two ZIP codes.

    Args:
        zip1: First ZIP code (baseline).
        zip2: Second ZIP code (comparison).
        api_key: SerpApi API key.
        queries: List of product search terms. Defaults to DEFAULT_QUERIES.
        cache_ttl: Seconds to cache API responses (0 disables caching).
        fetcher: Optional callable ``(query, zip_code, api_key) -> price`` to
            replace the default SerpApi backend (e.g. for testing or a
            different data provider).

    Returns:
        List of ProductPrice dataclass instances.
    """
    queries = queries or DEFAULT_QUERIES
    results: list[ProductPrice] = []

    for query in queries:
        logger.info("Fetching '%s' for ZIP %s and ZIP %s", query, zip1, zip2)
        if fetcher is not None:
            p1 = fetcher(query, zip1, api_key)
            p2 = fetcher(query, zip2, api_key)
        else:
            p1 = fetch_price(query, zip1, api_key, cache_ttl=cache_ttl)
            p2 = fetch_price(query, zip2, api_key, cache_ttl=cache_ttl)
        results.append(ProductPrice(query=query, zip1=p1, zip2=p2))
        logger.debug(
            "  %s: $%.2f vs $%.2f (Δ %s)",
            query,
            p1 or 0,
            p2 or 0,
            f"${results[-1].delta:+.2f}" if results[-1].delta is not None else "N/A",
        )

    return results

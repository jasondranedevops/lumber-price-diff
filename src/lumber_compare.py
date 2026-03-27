"""
lumber_compare.py
Core logic: fetch lumber prices from Home Depot via SerpApi,
compare two ZIP codes, and return structured results.
"""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

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

def _serpapi_request(query: str, zip_code: str, api_key: str, timeout: int = 15) -> list[dict]:
    """Fetch raw product list from SerpApi Home Depot engine."""
    params = {
        "engine": "home_depot",
        "q": query,
        "delivery_zip": zip_code,
        "store_zip": zip_code,
        "api_key": api_key,
    }
    url = f"{SERPAPI_BASE}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = json.loads(resp.read())
        return data.get("products", [])
    except Exception as exc:
        logger.warning("SerpApi error for '%s' @ %s: %s", query, zip_code, exc)
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


def fetch_price(query: str, zip_code: str, api_key: str, top_n: int = 3) -> Optional[float]:
    """Return the first valid price from the top N results for a query+ZIP."""
    products = _serpapi_request(query, zip_code, api_key)
    for product in products[:top_n]:
        price = _extract_price(product)
        if price is not None:
            return price
    return None


# ---------------------------------------------------------------------------
# Main comparison function
# ---------------------------------------------------------------------------

def compare_lumber_prices(
    zip1: str,
    zip2: str,
    api_key: str,
    queries: Optional[list[str]] = None,
) -> list[ProductPrice]:
    """
    Compare Home Depot lumber prices between two ZIP codes.

    Args:
        zip1: First ZIP code (baseline).
        zip2: Second ZIP code (comparison).
        api_key: SerpApi API key.
        queries: List of product search terms. Defaults to DEFAULT_QUERIES.

    Returns:
        List of ProductPrice dataclass instances.
    """
    queries = queries or DEFAULT_QUERIES
    results: list[ProductPrice] = []

    for query in queries:
        logger.info("Fetching '%s' for ZIP %s and ZIP %s", query, zip1, zip2)
        p1 = fetch_price(query, zip1, api_key)
        p2 = fetch_price(query, zip2, api_key)
        results.append(ProductPrice(query=query, zip1=p1, zip2=p2))
        logger.debug(
            "  %s: $%.2f vs $%.2f (Δ %s)",
            query,
            p1 or 0,
            p2 or 0,
            f"${results[-1].delta:+.2f}" if results[-1].delta is not None else "N/A",
        )

    return results

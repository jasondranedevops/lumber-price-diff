"""
tests/test_lumber_compare.py
Unit tests for lumber_compare core logic (no live API calls).
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lumber_compare import (
    ProductPrice,
    _extract_price,
    compare_lumber_prices,
    fetch_price,
)


# ---------------------------------------------------------------------------
# ProductPrice dataclass
# ---------------------------------------------------------------------------

class TestProductPrice:
    def test_delta_computed_when_both_present(self):
        r = ProductPrice(query="2x4", zip1=10.00, zip2=12.50)
        assert r.delta == 2.50

    def test_delta_none_when_zip1_missing(self):
        r = ProductPrice(query="2x4", zip1=None, zip2=12.50)
        assert r.delta is None

    def test_delta_none_when_zip2_missing(self):
        r = ProductPrice(query="2x4", zip1=10.00, zip2=None)
        assert r.delta is None

    def test_zip2_is_pricier_true(self):
        r = ProductPrice(query="2x4", zip1=10.00, zip2=12.00)
        assert r.zip2_is_pricier is True

    def test_zip2_is_pricier_false(self):
        r = ProductPrice(query="2x4", zip1=12.00, zip2=10.00)
        assert r.zip2_is_pricier is False

    def test_zip2_is_pricier_none_when_no_delta(self):
        r = ProductPrice(query="2x4", zip1=None, zip2=None)
        assert r.zip2_is_pricier is None


# ---------------------------------------------------------------------------
# _extract_price
# ---------------------------------------------------------------------------

class TestExtractPrice:
    def test_top_level_price_key(self):
        assert _extract_price({"price": "$8.97"}) == 8.97

    def test_top_level_raw_price(self):
        assert _extract_price({"raw_price": 12.34}) == 12.34

    def test_top_level_sale_price(self):
        assert _extract_price({"sale_price": "5.50"}) == 5.50

    def test_nested_pricing_dict(self):
        assert _extract_price({"pricing": {"price": "7.25"}}) == 7.25

    def test_price_with_comma(self):
        assert _extract_price({"price": "$1,200.00"}) == 1200.00

    def test_returns_none_when_no_price(self):
        assert _extract_price({}) is None

    def test_returns_none_for_invalid_value(self):
        assert _extract_price({"price": "call for price"}) is None


# ---------------------------------------------------------------------------
# fetch_price
# ---------------------------------------------------------------------------

class TestFetchPrice:
    @patch("lumber_compare._serpapi_request")
    def test_returns_first_valid_price(self, mock_req):
        mock_req.return_value = [
            {"price": "$10.00"},
            {"price": "$9.00"},
        ]
        result = fetch_price("2x4", "90210", "fake-key")
        assert result == 10.00

    @patch("lumber_compare._serpapi_request")
    def test_skips_products_without_price(self, mock_req):
        mock_req.return_value = [
            {"name": "No price here"},
            {"price": "$15.50"},
        ]
        result = fetch_price("2x4", "90210", "fake-key", top_n=3)
        assert result == 15.50

    @patch("lumber_compare._serpapi_request")
    def test_returns_none_when_no_products(self, mock_req):
        mock_req.return_value = []
        result = fetch_price("2x4", "90210", "fake-key")
        assert result is None


# ---------------------------------------------------------------------------
# compare_lumber_prices (integration-level, mocked)
# ---------------------------------------------------------------------------

class TestCompareLumberPrices:
    @patch("lumber_compare.fetch_price")
    def test_returns_product_price_list(self, mock_fetch):
        mock_fetch.side_effect = lambda q, z, k: {"90210": 10.0, "10001": 12.0}[z]
        results = compare_lumber_prices("90210", "10001", "key", queries=["2x4"])
        assert len(results) == 1
        r = results[0]
        assert r.query == "2x4"
        assert r.zip1 == 10.0
        assert r.zip2 == 12.0
        assert r.delta == 2.0

    @patch("lumber_compare.fetch_price")
    def test_handles_missing_prices_gracefully(self, mock_fetch):
        mock_fetch.return_value = None
        results = compare_lumber_prices("00000", "99999", "key", queries=["2x4"])
        assert results[0].delta is None

    @patch("lumber_compare.fetch_price")
    def test_uses_default_queries_when_none_provided(self, mock_fetch):
        from lumber_compare import DEFAULT_QUERIES
        mock_fetch.return_value = 5.0
        results = compare_lumber_prices("11111", "22222", "key")
        assert len(results) == len(DEFAULT_QUERIES)

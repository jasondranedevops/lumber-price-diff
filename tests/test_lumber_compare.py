"""
tests/test_lumber_compare.py
Unit tests for lumber_compare core logic (no live API calls).
"""

import sys
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lumber_compare import (
    ProductPrice,
    _extract_price,
    _serpapi_request,
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
    def test_returns_minimum_valid_price(self, mock_req):
        mock_req.return_value = [
            {"price": "$10.00"},
            {"price": "$9.00"},
        ]
        result = fetch_price("2x4", "90210", "fake-key", cache_ttl=0)
        assert result == 9.00

    @patch("lumber_compare._serpapi_request")
    def test_skips_products_without_price(self, mock_req):
        mock_req.return_value = [
            {"name": "No price here"},
            {"price": "$15.50"},
        ]
        result = fetch_price("2x4", "90210", "fake-key", top_n=3, cache_ttl=0)
        assert result == 15.50

    @patch("lumber_compare._serpapi_request")
    def test_returns_none_when_no_products(self, mock_req):
        mock_req.return_value = []
        result = fetch_price("2x4", "90210", "fake-key", cache_ttl=0)
        assert result is None


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------

class TestCaching:
    @patch("lumber_compare._serpapi_request")
    def test_cache_miss_calls_api(self, mock_req, tmp_path):
        mock_req.return_value = [{"price": "$10.00"}]
        with patch("lumber_compare._CACHE_DIR", tmp_path):
            result = fetch_price("2x4", "90210", "key", cache_ttl=60)
        mock_req.assert_called_once()
        assert result == 10.00

    @patch("lumber_compare._serpapi_request")
    def test_cache_hit_skips_api(self, mock_req, tmp_path):
        mock_req.return_value = [{"price": "$10.00"}]
        with patch("lumber_compare._CACHE_DIR", tmp_path):
            fetch_price("2x4", "90210", "key", cache_ttl=60)
            result = fetch_price("2x4", "90210", "key", cache_ttl=60)
        assert mock_req.call_count == 1
        assert result == 10.00

    @patch("lumber_compare._serpapi_request")
    def test_cache_ttl_zero_disables_cache(self, mock_req, tmp_path):
        mock_req.return_value = [{"price": "$10.00"}]
        with patch("lumber_compare._CACHE_DIR", tmp_path):
            fetch_price("2x4", "90210", "key", cache_ttl=0)
            fetch_price("2x4", "90210", "key", cache_ttl=0)
        assert mock_req.call_count == 2

    @patch("lumber_compare.time.time")
    @patch("lumber_compare._serpapi_request")
    def test_expired_cache_refetches(self, mock_req, mock_time, tmp_path):
        mock_req.return_value = [{"price": "$10.00"}]
        mock_time.return_value = 1000.0
        with patch("lumber_compare._CACHE_DIR", tmp_path):
            fetch_price("2x4", "90210", "key", cache_ttl=60)
            # Advance time past TTL
            mock_time.return_value = 1000.0 + 61
            fetch_price("2x4", "90210", "key", cache_ttl=60)
        assert mock_req.call_count == 2


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------

class TestRetryLogic:
    @patch("lumber_compare.time.sleep")
    @patch("urllib.request.urlopen")
    def test_retries_on_network_error_then_succeeds(self, mock_urlopen, mock_sleep):
        success_resp = MagicMock()
        success_resp.__enter__ = lambda s: s
        success_resp.__exit__ = MagicMock(return_value=False)
        success_resp.read.return_value = b'{"products": [{"price": "$5.00"}]}'

        mock_urlopen.side_effect = [
            urllib.error.URLError("connection refused"),
            urllib.error.URLError("timeout"),
            success_resp,
        ]
        products = _serpapi_request("2x4", "90210", "fake-key")
        assert len(products) == 1
        assert mock_sleep.call_count == 2  # slept between the two failed attempts

    @patch("lumber_compare.time.sleep")
    @patch("urllib.request.urlopen")
    def test_returns_empty_after_all_retries_exhausted(self, mock_urlopen, mock_sleep):
        mock_urlopen.side_effect = urllib.error.URLError("unreachable")
        products = _serpapi_request("2x4", "90210", "fake-key", max_retries=3)
        assert products == []
        assert mock_sleep.call_count == 2  # sleep between attempt 1→2 and 2→3

    @patch("lumber_compare.time.sleep")
    @patch("urllib.request.urlopen")
    def test_no_retry_on_4xx(self, mock_urlopen, mock_sleep):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=401, msg="Unauthorized", hdrs={}, fp=None
        )
        products = _serpapi_request("2x4", "90210", "bad-key")
        assert products == []
        mock_urlopen.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("lumber_compare.time.sleep")
    @patch("urllib.request.urlopen")
    def test_retries_on_5xx(self, mock_urlopen, mock_sleep):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=503, msg="Service Unavailable", hdrs={}, fp=None
        )
        products = _serpapi_request("2x4", "90210", "fake-key", max_retries=2)
        assert products == []
        assert mock_urlopen.call_count == 2

    @patch("lumber_compare.time.sleep")
    @patch("urllib.request.urlopen")
    def test_exponential_backoff_delays(self, mock_urlopen, mock_sleep):
        mock_urlopen.side_effect = urllib.error.URLError("err")
        _serpapi_request("2x4", "90210", "fake-key", max_retries=3)
        delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert delays == [1, 2]  # 2^0, 2^1


# ---------------------------------------------------------------------------
# compare_lumber_prices (integration-level, mocked)
# ---------------------------------------------------------------------------

class TestCompareLumberPrices:
    @patch("lumber_compare.fetch_price")
    def test_returns_product_price_list(self, mock_fetch):
        mock_fetch.side_effect = lambda q, z, k, **_: {"90210": 10.0, "10001": 12.0}[z]
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

    def test_custom_fetcher_is_used_instead_of_serpapi(self):
        prices = {"zip1": 8.0, "zip2": 9.5}
        custom_fetcher = lambda q, z, k: prices.get(z)
        results = compare_lumber_prices(
            "zip1", "zip2", "key",
            queries=["2x4"],
            fetcher=custom_fetcher,
        )
        assert results[0].zip1 == 8.0
        assert results[0].zip2 == 9.5

    @patch("lumber_compare.fetch_price")
    def test_cache_ttl_passed_to_fetch_price(self, mock_fetch):
        mock_fetch.return_value = 5.0
        compare_lumber_prices("11111", "22222", "key", queries=["2x4"], cache_ttl=0)
        # Both calls (zip1 and zip2) should pass cache_ttl=0
        for call in mock_fetch.call_args_list:
            assert call.kwargs.get("cache_ttl") == 0

"""
tests/test_main.py
Tests for the CLI entry point (main.py).
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from main import parse_args, main


class TestParseArgs:
    def test_positional_zips(self):
        args = parse_args(["90210", "10001"])
        assert args.zip1 == "90210"
        assert args.zip2 == "10001"

    def test_key_flag(self):
        args = parse_args(["90210", "10001", "--key", "mykey"])
        assert args.key == "mykey"

    def test_no_chart_flag(self):
        args = parse_args(["90210", "10001", "--no-chart"])
        assert args.no_chart is True

    def test_out_flag(self):
        args = parse_args(["90210", "10001", "--out", "my_chart.png"])
        assert args.out == "my_chart.png"

    def test_queries_override(self):
        args = parse_args(["90210", "10001", "--queries", "2x4", "plywood"])
        assert args.queries == ["2x4", "plywood"]


class TestMain:
    def test_returns_1_without_api_key(self):
        with patch.dict("os.environ", {"SERPAPI_KEY": ""}, clear=False):
            rc = main(["90210", "10001", "--key", ""])
        assert rc == 1

    @patch("main.build_chart")
    @patch("main.compare_lumber_prices")
    def test_successful_run_returns_0(self, mock_compare, mock_chart):
        from lumber_compare import ProductPrice
        mock_compare.return_value = [ProductPrice("2x4", 10.0, 12.0)]
        mock_chart.return_value = Path("charts/test.png")

        rc = main(["90210", "10001", "--key", "fake-key"])
        assert rc == 0

    @patch("main.compare_lumber_prices")
    def test_no_chart_skips_build_chart(self, mock_compare):
        from lumber_compare import ProductPrice
        mock_compare.return_value = [ProductPrice("2x4", 10.0, 12.0)]

        with patch("main.build_chart") as mock_chart:
            main(["90210", "10001", "--key", "fake-key", "--no-chart"])
            mock_chart.assert_not_called()

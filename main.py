#!/usr/bin/env python3
"""
main.py
CLI entry point for the Lumber Price Differential tool.

Usage:
    python main.py <ZIP1> <ZIP2> [--key API_KEY] [--out chart.png]

Environment:
    SERPAPI_KEY  – SerpApi key (alternative to --key flag)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Allow running from repo root or src/
sys.path.insert(0, str(Path(__file__).parent / "src"))

from lumber_compare import DEFAULT_QUERIES, compare_lumber_prices
from chart import build_chart

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Summary printer
# ---------------------------------------------------------------------------

def print_summary(results, zip1: str, zip2: str) -> None:
    sep = "─" * 62
    fmt = "{:<30} {:>8}  {:>8}  {:>8}"
    print(f"\n{sep}")
    print(f"  LUMBER PRICE DIFFERENTIAL  |  {zip1}  →  {zip2}")
    print(sep)
    print(fmt.format("Product", zip1, zip2, "Delta"))
    print(sep)

    total_delta = 0.0
    counted = 0
    for r in results:
        p1 = f"${r.zip1:.2f}" if r.zip1 is not None else "N/A"
        p2 = f"${r.zip2:.2f}" if r.zip2 is not None else "N/A"
        if r.delta is not None:
            sign = "+" if r.delta >= 0 else ""
            d = f"{sign}${r.delta:.2f}"
            total_delta += r.delta
            counted += 1
        else:
            d = "N/A"
        print(fmt.format(r.query[:30], p1, p2, d))

    print(sep)
    if counted:
        avg = total_delta / counted
        sign = "+" if avg >= 0 else ""
        direction = f"ZIP {zip2} is {'pricier' if avg > 0 else 'cheaper'}"
        print(f"  Average delta: {sign}${avg:.2f}/item  ({direction})")
    print(sep + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare Home Depot lumber prices between two ZIP codes.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py 90210 10001
  python main.py 30301 77001 --key sk-abc123 --out results/chart.png
  SERPAPI_KEY=sk-abc123 python main.py 60601 02101
        """,
    )
    parser.add_argument("zip1", help="First ZIP code (baseline)")
    parser.add_argument("zip2", help="Second ZIP code (comparison)")
    parser.add_argument(
        "--key", "-k",
        default=os.environ.get("SERPAPI_KEY", ""),
        help="SerpApi API key (or set SERPAPI_KEY env var)",
    )
    parser.add_argument(
        "--out", "-o",
        default=None,
        help="Output chart path (default: charts/lumber_<ZIP1>_vs_<ZIP2>.png)",
    )
    parser.add_argument(
        "--no-chart",
        action="store_true",
        help="Skip chart generation (print summary only)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        help="Chart image DPI (default: 150)",
    )
    parser.add_argument(
        "--queries",
        nargs="+",
        default=None,
        metavar="QUERY",
        help="Override default lumber search queries",
    )
    parser.add_argument(
        "--cache-ttl",
        type=int,
        default=3600,
        metavar="SECONDS",
        help="Cache API responses for this many seconds (0 disables cache, default: 3600)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.key:
        logger.error(
            "SerpApi key not found. Pass --key or set the SERPAPI_KEY environment variable."
        )
        return 1

    queries = args.queries or DEFAULT_QUERIES

    logger.info(
        "Comparing lumber prices: ZIP %s vs ZIP %s (%d products)",
        args.zip1, args.zip2, len(queries),
    )

    results = compare_lumber_prices(
        zip1=args.zip1,
        zip2=args.zip2,
        api_key=args.key,
        queries=queries,
        cache_ttl=args.cache_ttl,
    )

    print_summary(results, args.zip1, args.zip2)

    if not args.no_chart:
        out_path = Path(args.out) if args.out else None
        try:
            saved = build_chart(results, args.zip1, args.zip2,
                                output_path=out_path, dpi=args.dpi)
            print(f"✓ Chart saved → {saved}")
        except Exception as exc:
            logger.error("Chart generation failed: %s", exc)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

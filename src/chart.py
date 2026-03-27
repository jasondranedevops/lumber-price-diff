"""
chart.py
Generate a dual-panel price comparison chart (bar + delta) from lumber data.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from lumber_compare import ProductPrice

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Palette (dark industrial)
# ---------------------------------------------------------------------------
BG      = "#1a1a1a"
PANEL   = "#242424"
C1      = "#e8a020"   # amber  – ZIP 1
C2      = "#4fc3f7"   # steel blue – ZIP 2
C_POS   = "#ef5350"   # red    – ZIP 2 more expensive
C_NEG   = "#66bb6a"   # green  – ZIP 2 cheaper
C_ZERO  = "#90a4ae"   # grey   – no data / equal
GRID    = "#333333"
TEXT    = "#e0e0e0"
SUBTEXT = "#9e9e9e"


def build_chart(
    results: list[ProductPrice],
    zip1: str,
    zip2: str,
    output_path: Optional[Path] = None,
    dpi: int = 150,
) -> Path:
    """
    Render a price-comparison chart and save it to *output_path*.

    Args:
        results: List of ProductPrice objects from compare_lumber_prices().
        zip1: First ZIP label.
        zip2: Second ZIP label.
        output_path: Destination file. Defaults to charts/lumber_<zip1>_vs_<zip2>.png.
        dpi: Image resolution.

    Returns:
        Resolved Path of the saved chart.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
        import numpy as np
        from matplotlib.patches import Patch
    except ImportError as exc:
        raise RuntimeError(
            "matplotlib and numpy are required for charting. "
            "Install them with:  pip install matplotlib numpy"
        ) from exc

    # Filter to rows with at least one price
    valid = [r for r in results if r.zip1 is not None or r.zip2 is not None]
    if not valid:
        raise ValueError("No price data available to chart.")

    labels  = [r.query.replace(" ", "\n") for r in valid]
    vals1   = [r.zip1 or 0.0 for r in valid]
    vals2   = [r.zip2 or 0.0 for r in valid]
    deltas  = [r.delta for r in valid]

    x      = np.arange(len(labels))
    bar_w  = 0.35

    # ── Figure layout ────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(14, 9), facecolor=BG)
    gs  = fig.add_gridspec(2, 1, height_ratios=[3, 1.2], hspace=0.08)
    ax_bar  = fig.add_subplot(gs[0])
    ax_diff = fig.add_subplot(gs[1], sharex=ax_bar)

    for ax in (ax_bar, ax_diff):
        ax.set_facecolor(PANEL)
        ax.tick_params(colors=TEXT, labelsize=8)
        ax.spines[:].set_color(GRID)
        ax.yaxis.grid(True, color=GRID, linewidth=0.6, linestyle="--")
        ax.set_axisbelow(True)

    # ── Top panel: grouped bars ───────────────────────────────────────────
    bars1 = ax_bar.bar(x - bar_w / 2, vals1, bar_w, label=f"ZIP {zip1}",
                       color=C1, zorder=3, edgecolor=BG, linewidth=0.8)
    bars2 = ax_bar.bar(x + bar_w / 2, vals2, bar_w, label=f"ZIP {zip2}",
                       color=C2, zorder=3, edgecolor=BG, linewidth=0.8)

    for bars, vals in ((bars1, vals1), (bars2, vals2)):
        for bar, val in zip(bars, vals):
            if val:
                ax_bar.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.05,
                    f"${val:.2f}",
                    ha="center", va="bottom",
                    color=TEXT, fontsize=7.5, fontweight="bold",
                )

    ax_bar.set_ylabel("Price (USD)", color=TEXT, fontsize=10)
    ax_bar.yaxis.set_major_formatter(mticker.FormatStrFormatter("$%.0f"))
    ax_bar.legend(frameon=False, labelcolor=TEXT, fontsize=9)
    ax_bar.tick_params(labelbottom=False)
    ax_bar.set_title(
        f"Lumber Price Comparison  ·  ZIP {zip1}  vs  ZIP {zip2}",
        color=TEXT, fontsize=13, fontweight="bold", pad=14,
    )

    # ── Bottom panel: delta bars ──────────────────────────────────────────
    delta_colors = []
    for d in deltas:
        if d is None:
            delta_colors.append(C_ZERO)
        elif d > 0:
            delta_colors.append(C_POS)
        elif d < 0:
            delta_colors.append(C_NEG)
        else:
            delta_colors.append(C_ZERO)

    delta_vals = [d if d is not None else 0.0 for d in deltas]
    ax_diff.bar(x, delta_vals, width=bar_w * 1.6, color=delta_colors,
                zorder=3, edgecolor=BG, linewidth=0.8)
    ax_diff.axhline(0, color=SUBTEXT, linewidth=0.8)

    for xi, dv in zip(x, delta_vals):
        if dv != 0:
            sign = "+" if dv >= 0 else ""
            ax_diff.text(
                xi,
                dv + (0.02 if dv >= 0 else -0.02),
                f"{sign}${dv:.2f}",
                ha="center",
                va="bottom" if dv >= 0 else "top",
                color=TEXT, fontsize=7.5, fontweight="bold",
            )

    ax_diff.set_ylabel(f"Δ ZIP {zip2}−{zip1}", color=TEXT, fontsize=9)
    ax_diff.yaxis.set_major_formatter(mticker.FormatStrFormatter("$%.2f"))
    ax_diff.set_xticks(x)
    ax_diff.set_xticklabels(labels, color=TEXT, fontsize=7.5)

    legend_els = [
        Patch(facecolor=C_POS, label=f"ZIP {zip2} more expensive"),
        Patch(facecolor=C_NEG, label=f"ZIP {zip2} cheaper"),
        Patch(facecolor=C_ZERO, label="No data / equal"),
    ]
    ax_diff.legend(handles=legend_els, frameon=False, labelcolor=TEXT,
                   fontsize=8, loc="upper right")

    fig.text(0.5, 0.01, "Data via SerpApi · Home Depot · Prices may vary",
             ha="center", color=SUBTEXT, fontsize=7.5)

    # ── Save ─────────────────────────────────────────────────────────────
    if output_path is None:
        charts_dir = Path("charts")
        charts_dir.mkdir(exist_ok=True)
        output_path = charts_dir / f"lumber_{zip1}_vs_{zip2}.png"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    logger.info("Chart saved → %s", output_path)
    return output_path

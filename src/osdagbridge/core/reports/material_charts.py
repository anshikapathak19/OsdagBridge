# =============================================================================
# OsdagBridge — Requirement 5: Material Quantity Bar Charts
# =============================================================================
"""
Module for generating material quantity bar charts for Chapter 7 (Material Take-off & Quantity Summary):
1. Chart 1 — Structural Steel Tonnage (MT) for Steel Plate Girders, Cross Bracing, and End Diaphragms.
2. Chart 2 — Concrete Volume vs. Reinforcement Steel Weight (one figure containing two clearly labeled
   panels with separate units: concrete volume in m³ and rebar weight in MT).
"""

import logging
import os
from typing import Any, Dict, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from osdagbridge.core.reports.report_style import (
    CHART_STEEL_BAR_COLORS,
    CHART_STEEL_EDGE,
    CHART_CONCRETE,
    CHART_CONCRETE_EDGE,
    CHART_CONCRETE_BADGE_BG,
    CHART_REBAR,
    CHART_REBAR_EDGE,
    CHART_REBAR_BADGE_BG,
    CHART_GRID_COLOR,
    CHART_SPINE_COLOR,
    CHART_TEXT_MUTED,
    CHART_SUMMARY_BG,
    CHART_SUMMARY_EDGE,
)

logger = logging.getLogger("osdagbridge.core.reports.material_charts")


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Safely convert any value to float, ignoring N.A., None, strings."""
    if val is None:
        return default
    try:
        s = str(val).strip().replace(",", "")
        if s.lower() in ("n.a.", "na", "none", "", "placeholder"):
            return default
        return float(s)
    except Exception:
        return default


def extract_material_quantities(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract material quantities from the input/payload dictionary for Chapter 7.
    
    Returns a dictionary with numeric values:
      - steel_girders_mt: Girder steel tonnage (MT)
      - cross_bracing_top_mt: Top chord bracing tonnage (MT)
      - cross_bracing_bot_mt: Bottom chord bracing tonnage (MT)
      - cross_bracing_diag_mt: Diagonal chord bracing tonnage (MT)
      - cross_bracing_mt: Sum of all cross bracing tonnage (MT)
      - end_diaphragm_mt: End diaphragm steel tonnage (MT)
      - total_steel_mt: Total structural steel tonnage (MT)
      - concrete_vol_m3: Concrete deck volume (m³)
      - concrete_wt_mt: Concrete deck weight (MT)
      - rebar_wt_mt: Reinforcement steel weight (MT)
      - is_valid: True if at least one quantity is positive
    """
    inputs = data or {}

    girders_mt = _safe_float(inputs.get("steel_girders_wt_total"))
    
    cb_top_mt = _safe_float(inputs.get("bracing_top_wt_total"))
    cb_bot_mt = _safe_float(inputs.get("bracing_bot_wt_total"))
    cb_diag_mt = _safe_float(inputs.get("bracing_diag_wt_total"))
    cb_mt = cb_top_mt + cb_bot_mt + cb_diag_mt
    if cb_mt <= 0.0:
        cb_mt = _safe_float(inputs.get("steel_bracing_wt_total"))

    ed_mt = _safe_float(inputs.get("end_diaphragm_wt_total"))

    total_steel_mt = girders_mt + cb_mt + ed_mt

    concrete_vol = _safe_float(inputs.get("concrete_deck_vol_total"))
    concrete_wt = _safe_float(inputs.get("concrete_deck_wt_total"))
    if concrete_wt <= 0.0 and concrete_vol > 0.0:
        concrete_wt = concrete_vol * 2.5

    rebar_wt = _safe_float(inputs.get("rebar_deck_wt_total"))
    if rebar_wt <= 0.0 and concrete_vol > 0.0:
        rebar_wt = (concrete_vol * 120.0) / 1000.0

    is_valid = (total_steel_mt > 0.0 or concrete_vol > 0.0 or rebar_wt > 0.0)

    return {
        "steel_girders_mt": round(girders_mt, 2),
        "cross_bracing_top_mt": round(cb_top_mt, 4),
        "cross_bracing_bot_mt": round(cb_bot_mt, 4),
        "cross_bracing_diag_mt": round(cb_diag_mt, 4),
        "cross_bracing_mt": round(cb_mt, 2),
        "end_diaphragm_mt": round(ed_mt, 2),
        "total_steel_mt": round(total_steel_mt, 2),
        "concrete_vol_m3": round(concrete_vol, 2),
        "concrete_wt_mt": round(concrete_wt, 2),
        "rebar_wt_mt": round(rebar_wt, 2),
        "is_valid": is_valid,
    }


def plot_steel_tonnage_chart(steel_data: Dict[str, Any], output_path: str) -> str:
    """
    Generate Chart 1: Structural Steel Tonnage (MT) vertical bar chart.
    
    Displays steel tonnage for:
      - Steel Plate Girders
      - Cross Bracing
      - End Diaphragms
    """
    labels = ["Steel Plate\nGirders", "Cross\nBracing", "End\nDiaphragms"]
    values = [
        steel_data.get("steel_girders_mt", 0.0),
        steel_data.get("cross_bracing_mt", 0.0),
        steel_data.get("end_diaphragm_mt", 0.0),
    ]
    total_wt = steel_data.get("total_steel_mt", sum(values))

    fig, ax = plt.subplots(figsize=(7.8, 4.4), dpi=300)

    bar_width = 0.42
    x_pos = np.arange(len(labels))

    bars = ax.bar(x_pos, values, width=bar_width, color=CHART_STEEL_BAR_COLORS, edgecolor=CHART_STEEL_EDGE, linewidth=1.0, zorder=3)

    # Annotate bar values
    max_val = max(values) if values else 1.0
    for bar, val in zip(bars, values):
        height = bar.get_height()
        # Offset above bar
        offset = max(max_val * 0.025, 0.4)
        ax.annotate(
            f"{val:.2f} MT",
            xy=(bar.get_x() + bar.get_width() / 2, height + offset),
            xytext=(0, 0),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            color="#111111",
        )

    ax.set_xticks(x_pos)
    ax.set_xticklabels(labels, fontsize=10.5, fontweight="bold")
    ax.set_ylabel("Steel Tonnage (MT)", fontsize=11, fontweight="bold")
    ax.set_title("Structural Steel Tonnage by Component", fontsize=12, fontweight="bold", pad=12)

    y_upper = max(max_val * 1.18, 5.0)
    ax.set_ylim(0, y_upper)

    # Gridlines and styling
    ax.grid(axis="y", linestyle="--", alpha=0.5, color=CHART_GRID_COLOR, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(CHART_SPINE_COLOR)
    ax.spines["bottom"].set_color(CHART_SPINE_COLOR)

    # Add summary box for total steel tonnage
    pct_g = (values[0] / total_wt * 100.0) if total_wt > 0 else 0.0
    pct_cb = (values[1] / total_wt * 100.0) if total_wt > 0 else 0.0
    pct_ed = (values[2] / total_wt * 100.0) if total_wt > 0 else 0.0
    summary_text = (
        f"Total Steel: {total_wt:.2f} MT\n"
        f"• Girders: {pct_g:.1f}%\n"
        f"• Cross Bracing: {pct_cb:.1f}%\n"
        f"• End Diaphragms: {pct_ed:.1f}%"
    )
    ax.text(
        0.96,
        0.93,
        summary_text,
        transform=ax.transAxes,
        fontsize=9,
        verticalalignment="top",
        horizontalalignment="right",
        bbox=dict(boxstyle="round,pad=0.5", facecolor=CHART_SUMMARY_BG, edgecolor=CHART_SUMMARY_EDGE, linewidth=1.0),
    )

    plt.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    return output_path


def plot_concrete_rebar_chart(concrete_vol: float, rebar_wt: float, output_path: str) -> str:
    """
    Generate Chart 2: Concrete Volume vs. Reinforcement Steel Weight.
    
    A combined dual-axis bar chart visualization:
      - Left y-axis: Concrete Volume in m³ (Forest Green)
      - Right y-axis: Reinforcement Steel Weight in MT (Terracotta Amber)
      - Separate scales and distinct color-coded axes so physical units are not conflated.
    """
    fig, ax1 = plt.subplots(figsize=(7.8, 4.4), dpi=300)
    ax2 = ax1.twinx()

    color_conc = CHART_CONCRETE
    edge_conc = CHART_CONCRETE_EDGE
    color_rebar = CHART_REBAR
    edge_rebar = CHART_REBAR_EDGE

    bar_width = 0.38

    # Concrete bar on ax1 (Left Axis) at x = 0
    b1 = ax1.bar(
        0, concrete_vol, width=bar_width, color=color_conc, edgecolor=edge_conc, linewidth=1.2, zorder=3
    )

    # Rebar bar on ax2 (Right Axis) at x = 1
    b2 = ax2.bar(
        1, rebar_wt, width=bar_width, color=color_rebar, edgecolor=edge_rebar, linewidth=1.2, zorder=3
    )

    ax1.set_xlim(-0.6, 1.6)
    ax1.set_xticks([0, 1])
    ax1.set_xticklabels(
        ["Deck Slab Concrete\n(Volume)", "Reinforcement Steel\n(Weight)"],
        fontsize=10.5,
        fontweight="bold",
    )

    # ── Left Axis: Concrete Volume ──
    y_max1 = max(concrete_vol * 1.20, 10.0)
    ax1.set_ylim(0, y_max1)
    ax1.set_ylabel(r"Concrete Volume ($\mathrm{m}^3$)", fontsize=11, fontweight="bold", color=color_conc)
    ax1.tick_params(axis="y", labelcolor=color_conc, labelsize=10)
    ax1.grid(axis="y", linestyle="--", alpha=0.4, color=CHART_GRID_COLOR, zorder=0)
    ax1.spines["top"].set_visible(False)
    ax1.spines["left"].set_color(color_conc)
    ax1.spines["left"].set_linewidth(1.5)
    ax1.spines["bottom"].set_color(CHART_SPINE_COLOR)

    # ── Right Axis: Reinforcement Steel Weight ──
    y_max2 = max(rebar_wt * 1.20, 1.0)
    ax2.set_ylim(0, y_max2)
    ax2.set_ylabel("Reinforcement Weight (MT)", fontsize=11, fontweight="bold", color=color_rebar)
    ax2.tick_params(axis="y", labelcolor=color_rebar, labelsize=10)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_color(color_rebar)
    ax2.spines["right"].set_linewidth(1.5)

    # Annotations above bars
    ax1.annotate(
        f"{concrete_vol:.2f} m³",
        xy=(0, concrete_vol + (y_max1 * 0.025)),
        ha="center",
        va="bottom",
        fontsize=11,
        fontweight="bold",
        color=color_conc,
    )
    ax2.annotate(
        f"{rebar_wt:.2f} MT",
        xy=(1, rebar_wt + (y_max2 * 0.025)),
        ha="center",
        va="bottom",
        fontsize=11,
        fontweight="bold",
        color=color_rebar,
    )

    # Informational badges on the bars
    ax1.text(
        0,
        y_max1 * 0.20,
        "Grade: M40\nDensity: 25.0 kN/m³",
        ha="center",
        va="center",
        fontsize=8.5,
        bbox=dict(boxstyle="round,pad=0.4", facecolor=CHART_CONCRETE_BADGE_BG, edgecolor=color_conc, alpha=0.9),
    )
    ax2.text(
        1,
        y_max2 * 0.20,
        "Grade: Fe 500\nAllowance: 120 kg/m³",
        ha="center",
        va="center",
        fontsize=8.5,
        bbox=dict(boxstyle="round,pad=0.4", facecolor=CHART_REBAR_BADGE_BG, edgecolor=color_rebar, alpha=0.9),
    )

    ax1.set_title(
        "Deck Slab Materials --- Concrete Volume vs. Reinforcement Steel Weight",
        fontsize=11.5,
        fontweight="bold",
        pad=14,
    )

    # Footnote
    fig.text(
        0.5,
        -0.02,
        r"* Reinforcement steel weight is estimated using standard bridge deck allowance of 120 kg/m$^3$ of concrete volume.",
        ha="center",
        fontsize=8.5,
        fontstyle="italic",
        color=CHART_TEXT_MUTED,
    )

    plt.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    return output_path


def generate_all_material_charts(data: Dict[str, Any], output_dir: str) -> Dict[str, str]:
    """
    Generate all material quantity charts for Chapter 7 and return their file paths.
    
    Keys returned:
      - material_chart_steel_tonnage: path to Chart 1 PNG
      - material_chart_concrete_rebar: path to Chart 2 PNG
    """
    fig_paths: Dict[str, str] = {}
    try:
        os.makedirs(output_dir, exist_ok=True)
        q = extract_material_quantities(data)

        # 1. Chart 1 — Structural Steel Tonnage
        p_steel = os.path.join(output_dir, "material_chart_steel_tonnage.png")
        plot_steel_tonnage_chart(q, p_steel)
        fig_paths["material_chart_steel_tonnage"] = p_steel.replace("\\", "/")

        # 2. Chart 2 — Concrete Volume vs. Reinforcement Steel Weight
        p_conc_rebar = os.path.join(output_dir, "material_chart_concrete_rebar.png")
        plot_concrete_rebar_chart(q["concrete_vol_m3"], q["rebar_wt_mt"], p_conc_rebar)
        fig_paths["material_chart_concrete_rebar"] = p_conc_rebar.replace("\\", "/")

    except Exception as exc:
        logger.warning(f"Error generating material quantity charts: {exc}")

    return fig_paths

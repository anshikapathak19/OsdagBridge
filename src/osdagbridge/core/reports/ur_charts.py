"""
Utilisation Ratio (UR) Chart Generator for OsdagBridge Reports (Requirement 4).

Generates four component-level bar charts embedded in Section 5.5:
  1. Steel Plate Girders (Governing Design Checks, distinguishing Live vs Total Deflection)
  2. Concrete Deck Slab (Transparently communicating Transverse Shear limitation)
  3. Cross Bracing (Member-level Compression, Tension, and Slenderness)
  4. End Diaphragms (All applicable panel members from capacity summary)

Features:
  - Separate pure data extraction from Matplotlib plotting.
  - Safe extraction with no fabricated or zeroed missing values.
  - Red dashed horizontal reference line at UR = 1.0.
  - Green bars for PASS (UR <= 1.0) and Red bars for FAIL (UR > 1.0).
  - Explicit numerical annotations above each bar.
  - Informative placeholder card for pending rolled/welded diaphragms.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines

from osdagbridge.core.utils.common import (
    KEY_DD_HAS_OVERHANG,
    KEY_DD_M_ULS_HOG,
    KEY_DD_M_ULS_OH,
    KEY_DD_M_ULS_SAG,
    KEY_DD_MU_BOT,
    KEY_DD_MU_OH,
    KEY_DD_MU_TOP,
    KEY_DD_PUNCH_VED,
    KEY_DD_SHEAR_VED,
    KEY_DD_SHEAR_VRDC,
    KEY_DD_VRD_C_MPA,
    KEY_DD_WK_BOT,
    KEY_DD_WK_LIMIT,
    KEY_DD_WK_OH,
    KEY_DD_WK_TOP,
    KEY_MP_ED_TYPE,
    KEY_SD_DEFL_ALLOW_LIVE,
    KEY_SD_DEFL_ALLOW_TOTAL,
    KEY_SD_DEFL_LIVE,
    KEY_SD_DEFL_TOTAL,
    KEY_SPAN,
)

if TYPE_CHECKING:
    from osdagbridge.core.reports.report_generator import ReportDataBridge


# ─────────────────────────────────────────────────────────────────────────────
# 1. PURE DATA EXTRACTION FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def extract_girder_ur(bridge: Any) -> List[Tuple[str, float, str]]:
    """
    Extract the governing Utilisation Ratio (UR) for primary plate girder checks:
      1. Moment (Check ID 1)
      2. Shear (Check ID 2)
      3. Lateral Torsional Buckling / LTB (Check ID 5)
      4. Defl. Live (L/800) (Check ID 13 or bridge actual live deflection vs allowable)
      5. Defl. Total (L/600) (Check ID 14 or bridge actual total deflection vs allowable)
      6. Combined Stress (Check ID 11)
      7. Fatigue (Check IDs 8, 9)

    Returns a list of (check_name, ur_value, status) where status is 'PASS' or 'FAIL'.
    """
    output_dict = getattr(bridge, "output_dict", {}) or {}
    input_dict = getattr(bridge, "input_dict", {}) or {}
    per_girder = (output_dict.get("design_results", {}) or {}).get("per_girder", {}) or {}

    def _find_check_dcr(check_ids: set) -> Optional[float]:
        best_dcr = None
        # Preferred: per_girder['checks'] (envelope)
        for g, gd in per_girder.items():
            if str(g).startswith("EB"):
                continue
            for chk in (gd.get("checks") or []):
                if chk.get("check_id") in check_ids:
                    dcr_val = chk.get("dcr")
                    if dcr_val is not None:
                        try:
                            f_dcr = float(dcr_val)
                            if best_dcr is None or f_dcr > best_dcr:
                                best_dcr = f_dcr
                        except (TypeError, ValueError):
                            pass
        # Fallback: per_lc (for SLS-conditional checks)
        if best_dcr is None:
            for g, gd in per_girder.items():
                if str(g).startswith("EB"):
                    continue
                for lc, ld in (gd.get("per_lc") or {}).items():
                    if str(lc).lower().startswith("envelope"):
                        continue
                    for chk in (ld.get("checks") or []):
                        if chk.get("id") in check_ids:
                            dcr_val = chk.get("dcr")
                            if dcr_val is not None:
                                try:
                                    f_dcr = float(dcr_val)
                                    if best_dcr is None or f_dcr > best_dcr:
                                        best_dcr = f_dcr
                                except (TypeError, ValueError):
                                    pass
        return best_dcr

    results: List[Tuple[str, float, str]] = []

    # 1. Moment
    d_mom = _find_check_dcr({1})
    if d_mom is not None:
        results.append(("Moment", round(d_mom, 2), "PASS" if d_mom <= 1.0 else "FAIL"))

    # 2. Shear
    d_shr = _find_check_dcr({2})
    if d_shr is not None:
        results.append(("Shear", round(d_shr, 2), "PASS" if d_shr <= 1.0 else "FAIL"))

    # 3. LTB
    d_ltb = _find_check_dcr({5})
    if d_ltb is not None:
        results.append(("LTB", round(d_ltb, 2), "PASS" if d_ltb <= 1.0 else "FAIL"))

    # 4. Live-Load Deflection (L/800)
    # Check if actual bridge live deflection and allowable exist in output_dict
    act_live = output_dict.get(KEY_SD_DEFL_LIVE)
    if act_live is None:
        vals = [output_dict.get(f"{KEY_SD_DEFL_LIVE}.G{i}") for i in range(1, 10)]
        vals = [float(v) for v in vals if v is not None]
        if vals:
            act_live = max(vals)
    allow_live = output_dict.get(KEY_SD_DEFL_ALLOW_LIVE)
    if allow_live is None and input_dict.get(KEY_SPAN):
        try:
            allow_live = float(input_dict[KEY_SPAN]) * 1000.0 / 800.0
        except (TypeError, ValueError):
            pass

    if act_live is not None and allow_live is not None and float(allow_live) > 0:
        ur_live = float(act_live) / float(allow_live)
        results.append(("Defl. Live (L/800)", round(ur_live, 2), "PASS" if ur_live <= 1.0 else "FAIL"))
    else:
        d_live = _find_check_dcr({13})
        if d_live is not None:
            results.append(("Defl. Live (L/800)", round(d_live, 2), "PASS" if d_live <= 1.0 else "FAIL"))

    # 5. Total-Load Deflection (L/600)
    # Check if actual bridge total deflection and allowable exist in output_dict
    act_total = output_dict.get(KEY_SD_DEFL_TOTAL)
    if act_total is None:
        vals = [output_dict.get(f"{KEY_SD_DEFL_TOTAL}.G{i}") for i in range(1, 10)]
        vals = [float(v) for v in vals if v is not None]
        if vals:
            act_total = max(vals)
    allow_total = output_dict.get(KEY_SD_DEFL_ALLOW_TOTAL)
    if allow_total is None and input_dict.get(KEY_SPAN):
        try:
            allow_total = float(input_dict[KEY_SPAN]) * 1000.0 / 600.0
        except (TypeError, ValueError):
            pass

    if act_total is not None and allow_total is not None and float(allow_total) > 0:
        ur_total = float(act_total) / float(allow_total)
        results.append(("Defl. Total (L/600)", round(ur_total, 2), "PASS" if ur_total <= 1.0 else "FAIL"))
    else:
        d_total = _find_check_dcr({14})
        if d_total is not None:
            results.append(("Defl. Total (L/600)", round(d_total, 2), "PASS" if d_total <= 1.0 else "FAIL"))

    # 6. Combined Stress
    d_str = _find_check_dcr({11})
    if d_str is not None:
        results.append(("Combined Stress", round(d_str, 2), "PASS" if d_str <= 1.0 else "FAIL"))

    # 7. Fatigue
    d_fat = _find_check_dcr({8, 9})
    if d_fat is not None:
        results.append(("Fatigue", round(d_fat, 2), "PASS" if d_fat <= 1.0 else "FAIL"))

    return results


def extract_deck_ur(bridge: Any) -> List[Tuple[str, float, str]]:
    """
    Extract Utilisation Ratios for Concrete Deck Slab design checks from
    `bridge.output_dict['deck_report_values']`.

    Checks evaluated:
      - Sagging Flexure
      - Hogging Flexure
      - Cantilever Overhang (if present)
      - Punching Shear
      - One-Way Shear
      - Crack Width

    Transverse Shear is preserved as unavailable when not evaluated by the deck module.
    """
    output_dict = getattr(bridge, "output_dict", {}) or {}
    deck_rpt = output_dict.get("deck_report_values", {}) or {}

    def _val(key: str) -> Optional[float]:
        v = deck_rpt.get(key)
        if v is None or v == "":
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    results: List[Tuple[str, float, str]] = []

    # 1. Sagging Flexure (Bottom steel)
    m_sag = _val(KEY_DD_M_ULS_SAG)
    mu_bot = _val(KEY_DD_MU_BOT)
    if m_sag is not None and mu_bot is not None and mu_bot > 0:
        ur = m_sag / mu_bot
        results.append(("Sagging Flexure", round(ur, 2), "PASS" if ur <= 1.0 else "FAIL"))

    # 2. Hogging Flexure (Top steel)
    m_hog = _val(KEY_DD_M_ULS_HOG)
    mu_top = _val(KEY_DD_MU_TOP)
    if m_hog is not None and mu_top is not None and mu_top > 0:
        ur = m_hog / mu_top
        results.append(("Hogging Flexure", round(ur, 2), "PASS" if ur <= 1.0 else "FAIL"))

    # 3. Cantilever Overhang
    has_oh = bool(deck_rpt.get(KEY_DD_HAS_OVERHANG))
    if has_oh:
        m_oh = _val(KEY_DD_M_ULS_OH)
        mu_oh = _val(KEY_DD_MU_OH)
        if m_oh is not None and mu_oh is not None and mu_oh > 0:
            ur = m_oh / mu_oh
            results.append(("Cantilever Overhang", round(ur, 2), "PASS" if ur <= 1.0 else "FAIL"))

    # 4. Punching Shear
    v_ed = _val(KEY_DD_PUNCH_VED)
    v_rdc = _val(KEY_DD_VRD_C_MPA)
    if v_ed is not None and v_rdc is not None and v_rdc > 0:
        ur = v_ed / v_rdc
        results.append(("Punching Shear", round(ur, 2), "PASS" if ur <= 1.0 else "FAIL"))

    # 5. One-Way Shear
    v_one = _val(KEY_DD_SHEAR_VED)
    vrd_one = _val(KEY_DD_SHEAR_VRDC)
    if v_one is not None and vrd_one is not None and vrd_one > 0:
        ur = v_one / vrd_one
        results.append(("One-Way Shear", round(ur, 2), "PASS" if ur <= 1.0 else "FAIL"))

    # 6. Crack Width
    wks = []
    for k in (KEY_DD_WK_BOT, KEY_DD_WK_TOP):
        wv = _val(k)
        if wv is not None:
            wks.append(wv)
    if has_oh:
        wv_oh = _val(KEY_DD_WK_OH)
        if wv_oh is not None:
            wks.append(wv_oh)
    wk_lim = _val(KEY_DD_WK_LIMIT)
    if wks and wk_lim is not None and wk_lim > 0:
        gov_wk = max(wks)
        ur = gov_wk / wk_lim
        results.append(("Crack Width", round(ur, 2), "PASS" if ur <= 1.0 else "FAIL"))

    return results


def extract_cross_bracing_ur(bridge: Any) -> List[Tuple[str, float, str]]:
    """
    Extract member-level Utilisation Ratios for Cross Bracing:
      - Compression efficiency
      - Tension efficiency
      - Slenderness ratio (KL/r / limit)

    Iterates through all girder pairs (e.g. G1-G2, G2-G3) and members (Diagonal, Chord).
    """
    results: List[Tuple[str, float, str]] = []

    pairs: List[str] = []
    if hasattr(bridge, "get_cb_pairs"):
        try:
            pairs = bridge.get_cb_pairs() or []
        except Exception:
            pairs = []

    for pair in pairs:
        # Diagonal and Chord capacity efficiencies
        for member, m_abbr in [("diagonal", "Diag"), ("chord", "Chord")]:
            for force_type, f_abbr in [("compression", "Comp"), ("tension", "Tens")]:
                if hasattr(bridge, "get_cb_efficiency"):
                    eff_str = bridge.get_cb_efficiency(pair, member, force_type)
                    if eff_str not in ("", None):
                        try:
                            eff = float(eff_str)
                            label = f"{pair} {m_abbr} ({f_abbr})"
                            status = "PASS" if eff <= 1.0 else "FAIL"
                            results.append((label, round(eff, 2), status))
                        except (TypeError, ValueError):
                            pass

        # Slenderness checks
        if hasattr(bridge, "get_cb_slenderness"):
            slnd_d = bridge.get_cb_slenderness(pair, "diagonal")
            if slnd_d not in ("", None):
                try:
                    ur_d = float(slnd_d) / 250.0
                    results.append((f"{pair} Diag (Slend)", round(ur_d, 2), "PASS" if ur_d <= 1.0 else "FAIL"))
                except (TypeError, ValueError):
                    pass

            slnd_c = bridge.get_cb_slenderness(pair, "chord")
            if slnd_c not in ("", None):
                try:
                    # In IS 800 Cl. 3.8: 250 for compression members, 400 for tension members.
                    # Governing slenderness limit is 250
                    ur_c = float(slnd_c) / 250.0
                    results.append((f"{pair} Chord (Slend)", round(ur_c, 2), "PASS" if ur_c <= 1.0 else "FAIL"))
                except (TypeError, ValueError):
                    pass

    return results


def extract_end_diaphragm_ur(bridge: Any) -> Tuple[bool, List[Tuple[str, float, str]], str]:
    """
    Extract Utilisation Ratios for End Diaphragms.
    Represents the actual member-level design results corresponding to Table 5.28:
      - ED <Pair> Diagonal
      - ED <Pair> Chord

    Returns:
      (is_available: bool, results: List[Tuple[str, float, str]], message: str)

    If end diaphragm is rolled/welded where design is pending, returns:
      (False, [], "Design pending for rolled/welded diaphragm.")
    """
    input_dict = getattr(bridge, "input_dict", {}) or {}
    output_dict = getattr(bridge, "output_dict", {}) or {}

    ed_type = ""
    for k, v in input_dict.items():
        if str(k).startswith(KEY_MP_ED_TYPE) and v:
            ed_type = str(v)
            break

    is_braced = "brac" in ed_type.strip().lower()

    if not is_braced:
        return (False, [], "Design pending for rolled/welded diaphragm.")

    # 1. First, check if specific end_diaphragm_design_results exists in output_dict
    ed_results = output_dict.get("end_diaphragm_design_results") or output_dict.get("end_diaphragm_design")
    if ed_results and isinstance(ed_results, dict):
        results: List[Tuple[str, float, str]] = []
        for pair, p_data in ed_results.items():
            if isinstance(p_data, dict):
                for mem, m_data in p_data.items():
                    if isinstance(m_data, dict):
                        for ftype, fdata in m_data.items():
                            if isinstance(fdata, dict):
                                eff = fdata.get("Member.efficiency") or fdata.get("efficiency")
                                if eff is not None:
                                    try:
                                        eff_f = float(eff)
                                        m_lbl = "Diag" if "diag" in mem.lower() else "Chord"
                                        lbl = f"ED {pair} {m_lbl}"
                                        results.append((lbl, round(eff_f, 2), "PASS" if eff_f <= 1.0 else "FAIL"))
                                    except (TypeError, ValueError):
                                        pass
        if results:
            return (True, results, "")

    # 2. Extract panel member-level results corresponding to Table 5.28
    results: List[Tuple[str, float, str]] = []
    pairs = bridge.get_cb_pairs() if hasattr(bridge, "get_cb_pairs") else []

    for pair in pairs:
        for member in ("diagonal", "chord"):
            m_lbl = "Diag" if member == "diagonal" else "Chord"
            lbl = f"ED {pair} {m_lbl}"
            ur_found = None

            # Prefer governing force efficiency used by Table 5.28
            if hasattr(bridge, "get_cb_governing_force") and hasattr(bridge, "get_cb_efficiency"):
                force_str, ftype = bridge.get_cb_governing_force(pair, member)
                ur_str = bridge.get_cb_efficiency(pair, member, ftype)
                if ur_str not in ("", None):
                    try:
                        ur_found = float(ur_str)
                    except (TypeError, ValueError):
                        pass

            # Fallback to compression / tension scan
            if ur_found is None and hasattr(bridge, "get_cb_efficiency"):
                for ft in ("compression", "tension"):
                    ur_str = bridge.get_cb_efficiency(pair, member, ft)
                    if ur_str not in ("", None):
                        try:
                            f_v = float(ur_str)
                            if ur_found is None or f_v > ur_found:
                                ur_found = f_v
                        except (TypeError, ValueError):
                            pass

            if ur_found is not None:
                results.append((lbl, round(ur_found, 2), "PASS" if ur_found <= 1.0 else "FAIL"))

    if results:
        return (True, results, "")

    return (False, [], "No design results available for end diaphragm.")


# ─────────────────────────────────────────────────────────────────────────────
# 2. PLOTTING LAYER (MATPLOTLIB)
# ─────────────────────────────────────────────────────────────────────────────

def plot_ur_bar_chart(
    title: str,
    data: List[Tuple[str, float, str]],
    output_path: str,
    is_pending: bool = False,
    pending_message: str = "",
    subtitle: str = "",
    figsize: Tuple[float, float] = (8.8, 3.9),
) -> str:
    """
    Render a clean, publication-ready Utilisation Ratio (UR) bar chart.

    Parameters:
      title: Chart title.
      data: List of (label, ur_value, status).
      output_path: Destination file path for PNG.
      is_pending: If True, renders an informative placeholder card.
      pending_message: Text for placeholder card.
      subtitle: Optional subtitle or clarifying note.
      figsize: Width and height tuple in inches.

    Returns:
      Canonical absolute path to the generated PNG file.
    """
    fig, ax = plt.subplots(figsize=figsize, dpi=300)

    # ── Informative Placeholder Mode ──
    if is_pending or not data:
        msg = pending_message or "No design results available."
        ax.text(
            0.5,
            0.5,
            msg,
            ha="center",
            va="center",
            fontsize=12,
            fontweight="medium",
            color="#495057",
            transform=ax.transAxes,
            bbox=dict(
                boxstyle="round,pad=1.2",
                facecolor="#f8f9fa",
                edgecolor="#ced4da",
                linewidth=1.2,
            ),
        )
        ax.set_title(title, fontsize=12, fontweight="bold", pad=12, color="#212529")
        ax.axis("off")
        fig.tight_layout()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        fig.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        return output_path

    # ── Active UR Bar Chart Mode ──
    labels = [d[0] for d in data]
    values = [d[1] for d in data]
    colors = ["#2e7d32" if d[2] == "PASS" else "#d32f2f" for d in data]

    x_indices = range(len(labels))
    bar_width = 0.52 if len(labels) <= 8 else 0.58

    bars = ax.bar(
        x_indices,
        values,
        color=colors,
        width=bar_width,
        edgecolor="#333333",
        linewidth=0.8,
        zorder=3,
    )

    # Red dashed threshold line at UR = 1.0
    ax.axhline(
        1.0,
        color="#d32f2f",
        linestyle="--",
        linewidth=1.6,
        zorder=4,
        label="Limit (UR = 1.0)",
    )

    ax.set_ylabel("Utilisation Ratio (UR)", fontsize=10, fontweight="bold", color="#212529")

    chart_title = title
    if subtitle:
        chart_title += f"\n({subtitle})"
    ax.set_title(chart_title, fontsize=11, fontweight="bold", pad=10, color="#212529")

    ax.set_xticks(list(x_indices))

    # Adapt rotation and font size based on number of bars
    if len(labels) > 8:
        rotation = 35
        fontsize = 8.2
    else:
        rotation = 22
        fontsize = 8.8

    ax.set_xticklabels(labels, rotation=rotation, ha="right", fontsize=fontsize, fontweight="medium")

    # Set suitable Y-axis limits with headroom for annotations
    max_val = max(values) if values else 1.0
    y_upper = max(1.25, max_val * 1.25)
    ax.set_ylim(0, y_upper)

    # Light subtle gridlines
    ax.grid(axis="y", linestyle=":", alpha=0.6, zorder=0)
    ax.set_axisbelow(True)

    # Format spines
    for sp in ["top", "right"]:
        ax.spines[sp].set_visible(False)
    for sp in ["left", "bottom"]:
        ax.spines[sp].set_color("#666666")

    # Value annotations above each bar
    for bar in bars:
        h = bar.get_height()
        annot_color = "#1b5e20" if h <= 1.0 else "#b71c1c"
        ax.annotate(
            f"{h:.2f}",
            xy=(bar.get_x() + bar.get_width() / 2, h),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8.5,
            fontweight="bold",
            color=annot_color,
        )

    # Explanatory legend with mathematical notation
    legend_elements = [
        mpatches.Patch(facecolor="#2e7d32", edgecolor="#333333", label="PASS (UR ≤ 1.0)"),
        mpatches.Patch(facecolor="#d32f2f", edgecolor="#333333", label="FAIL (UR > 1.0)"),
        mlines.Line2D([], [], color="#d32f2f", linestyle="--", linewidth=1.6, label="Limit (UR = 1.0)"),
    ]
    ax.legend(
        handles=legend_elements,
        loc="upper right",
        framealpha=0.92,
        facecolor="#ffffff",
        edgecolor="#cccccc",
        fontsize=8.2,
    )

    fig.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return output_path


# ─────────────────────────────────────────────────────────────────────────────
# 3. HIGH-LEVEL ORCHESTRATION FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def generate_all_ur_charts(bridge: Any, output_dir: str) -> Dict[str, str]:
    """
    Generate all 4 Utilisation Ratio charts for the report:
      1. Steel Plate Girders (Live & Total Deflection distinguished)
      2. Concrete Deck Slab (Transverse Shear limitation communicated)
      3. Cross Bracing (Panel member-level forces & slenderness)
      4. End Diaphragms (All 6 member-level results from capacity summary)

    Returns:
      Dictionary mapping chart keys to absolute file paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    fig_paths: Dict[str, str] = {}

    # 1. Steel Plate Girders
    girder_data = extract_girder_ur(bridge)
    p_girders = os.path.join(output_dir, "ur_chart_girders.png")
    plot_ur_bar_chart(
        title="Steel Plate Girders — Utilisation Ratio (Governing Checks)",
        data=girder_data,
        output_path=p_girders,
        figsize=(8.8, 3.9),
    )
    fig_paths["ur_chart_girders"] = p_girders.replace("\\", "/")

    # 2. Concrete Deck Slab
    deck_data = extract_deck_ur(bridge)
    p_deck = os.path.join(output_dir, "ur_chart_deck.png")
    plot_ur_bar_chart(
        title="Concrete Deck Slab — Utilisation Ratio",
        subtitle="Transverse shear check unavailable in deck module",
        data=deck_data,
        output_path=p_deck,
        figsize=(8.8, 3.9),
    )
    fig_paths["ur_chart_deck"] = p_deck.replace("\\", "/")

    # 3. Cross Bracing
    cb_data = extract_cross_bracing_ur(bridge)
    p_cb = os.path.join(output_dir, "ur_chart_cross_bracing.png")
    plot_ur_bar_chart(
        title="Cross Bracing — Utilisation Ratio (Governing Member Checks)",
        subtitle="Governing axial capacity (Table 5.25) and slenderness checks (Table 5.24)",
        data=cb_data,
        output_path=p_cb,
        figsize=(10.0, 4.2),
    )
    fig_paths["ur_chart_cross_bracing"] = p_cb.replace("\\", "/")

    # 4. End Diaphragms
    ed_avail, ed_data, ed_msg = extract_end_diaphragm_ur(bridge)
    p_ed = os.path.join(output_dir, "ur_chart_end_diaphragm.png")
    plot_ur_bar_chart(
        title="End Diaphragms — Utilisation Ratio",
        data=ed_data,
        output_path=p_ed,
        is_pending=not ed_avail,
        pending_message=ed_msg,
        figsize=(8.8, 3.9),
    )
    fig_paths["ur_chart_end_diaphragm"] = p_ed.replace("\\", "/")

    return fig_paths

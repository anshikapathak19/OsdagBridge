"""
Unit tests for Requirement 5: Material Quantity Bar Charts & BOQ End Diaphragm calculation.

Tests cover:
  1. Quantity extraction from normal BOQ payload.
  2. Safe handling of missing, None, and "N.A." values.
  3. BOQ End Diaphragm calculation for Cross Bracing configuration.
  4. BOQ End Diaphragm calculation for Rolled Beam configuration.
  5. BOQ End Diaphragm calculation for Welded Beam configuration.
  6. Scaling with girder counts and no double-counting with intermediate cross bracings.
  7. Generation of Chart 1 (Structural Steel Tonnage) image.
  8. Generation of Chart 2 (Concrete Volume vs. Rebar Weight) two-panel image.
  9. LaTeX formatting, Table 7.1 Item 2(d), and figure embedding in Chapter 7.
  10. Exact consistency between Table 7.1 quantities and chart values.
"""

import os
import tempfile
import pytest

from osdagbridge.core.boq.boq_generator import calculate_material_quantities
from osdagbridge.core.reports.material_charts import (
    extract_material_quantities,
    plot_steel_tonnage_chart,
    plot_concrete_rebar_chart,
    generate_all_material_charts,
)
from osdagbridge.core.reports.chap7 import ch7_quantities
from osdagbridge.core.utils.common import (
    KEY_SPAN,
    KEY_TS_NO_OF_GIRDERS,
    KEY_TS_GIRDER_SPACING,
    KEY_MP_GIRDER_DEPTH,
    KEY_MP_ED_TYPE,
    KEY_MP_ED_TOTAL_DEPTH,
    KEY_MP_ED_WEB_THICKNESS,
    KEY_MP_ED_TOP_FLANGE_WIDTH,
    KEY_MP_ED_BOTTOM_FLANGE_WIDTH,
    KEY_MP_ED_TOP_FLANGE_THICKNESS,
    KEY_MP_ED_BOTTOM_FLANGE_THICKNESS,
)


# ── 1. Extraction tests ────────────────────────────────────────────────────────

def test_extract_material_quantities_normal():
    data = {
        "steel_girders_wt_total": "32.89",
        "bracing_top_wt_total": "0.01",
        "bracing_bot_wt_total": "0.01",
        "bracing_diag_wt_total": "0.03",
        "end_diaphragm_wt_total": "0.10",
        "concrete_deck_vol_total": "63.00",
        "rebar_deck_wt_total": "7.56",
    }
    q = extract_material_quantities(data)
    assert q["steel_girders_mt"] == 32.89
    assert q["cross_bracing_top_mt"] == 0.01
    assert q["cross_bracing_bot_mt"] == 0.01
    assert q["cross_bracing_diag_mt"] == 0.03
    assert q["cross_bracing_mt"] == 0.05
    assert q["end_diaphragm_mt"] == 0.10
    assert q["total_steel_mt"] == 33.04
    assert q["concrete_vol_m3"] == 63.00
    assert q["rebar_wt_mt"] == 7.56
    assert q["is_valid"] is True


def test_extract_material_quantities_missing_and_na():
    data = {
        "steel_girders_wt_total": "N.A.",
        "bracing_top_wt_total": None,
        "concrete_deck_vol_total": "invalid",
    }
    q = extract_material_quantities(data)
    assert q["steel_girders_mt"] == 0.0
    assert q["cross_bracing_mt"] == 0.0
    assert q["end_diaphragm_mt"] == 0.0
    assert q["total_steel_mt"] == 0.0
    assert q["concrete_vol_m3"] == 0.0
    assert q["rebar_wt_mt"] == 0.0
    assert q["is_valid"] is False


# ── 2. BOQ End Diaphragm calculation tests ─────────────────────────────────────

def test_boq_end_diaphragm_cross_bracing():
    inputs = {
        KEY_SPAN: 30.0,
        KEY_TS_NO_OF_GIRDERS: 4,
        KEY_TS_GIRDER_SPACING: 2.1,
        KEY_MP_GIRDER_DEPTH: 1.65,
        KEY_MP_ED_TYPE: "Cross Bracing",
        "typical_section.overall_bridge_width": 8.4,
        "typical_section.deck_thickness": 250,
    }
    outputs = {
        "transverse_member_design.ed.section_properties.end_diaphragm.G1G2.A": 2.37,  # cm² (ISA 40x40x3)
    }
    q = calculate_material_quantities(inputs, outputs)
    
    # 4 girders -> 3 bays. 2 ends (Support 1 & Support 2).
    # Diagonals: 3 bays * 4 diags = 12
    # Top chords: 3 bays * 2 = 6
    # Bottom chords: 3 bays * 2 = 6
    # Total members = 24
    assert q["end_diaphragm_qty"] == "24"
    assert q["end_diaphragm_wt_total"] == "0.10"
    assert q["end_diaphragm_vol_total"] == "0.01"
    assert "0.00024" in q["end_diaphragm_vol_formula"] or "0.000" in q["end_diaphragm_vol_formula"]
    assert "(avg)" in q["end_diaphragm_vol_formula"]
    assert float(q["end_diaphragm_wt_single"]) > 0.0


def test_boq_end_diaphragm_rolled_beam():
    inputs = {
        KEY_SPAN: 30.0,
        KEY_TS_NO_OF_GIRDERS: 4,
        KEY_TS_GIRDER_SPACING: 2.1,
        KEY_MP_ED_TYPE: "Rolled Beam",
    }
    outputs = {
        "transverse_member_design.ed.section_properties.end_diaphragm.G1G2.A": 45.0,  # 45 cm²
        "transverse_member_design.ed.section_properties.end_diaphragm.G1G2.M": 35.3,  # kg/m
    }
    q = calculate_material_quantities(inputs, outputs)
    
    # 4 girders -> 3 bays * 2 ends = 6 beams
    assert q["end_diaphragm_qty"] == "6"
    assert float(q["end_diaphragm_vol_total"]) > 0.0
    assert float(q["end_diaphragm_wt_total"]) > 0.0
    assert float(q["end_diaphragm_wt_single"]) > 0.0


def test_boq_end_diaphragm_rolled_beam_database_lookup():
    """Verify that a rolled beam end diaphragm successfully queries section database."""
    inputs = {
        KEY_SPAN: 30.0,
        KEY_TS_NO_OF_GIRDERS: 4,
        KEY_TS_GIRDER_SPACING: 2.1,
        KEY_MP_ED_TYPE: "Rolled Beam",
        "member_properties.end_diaphragm_details.is_section": "ISMB 300",
    }
    outputs = {}
    q = calculate_material_quantities(inputs, outputs)

    assert q["end_diaphragm_qty"] == "6"
    assert q["end_diaphragm_vol_total"] == "0.07"
    assert q["end_diaphragm_wt_total"] == "0.58"
    assert "0.00586" in q["end_diaphragm_vol_formula"]


def test_boq_end_diaphragm_welded_beam():
    inputs = {
        KEY_SPAN: 30.0,
        KEY_TS_NO_OF_GIRDERS: 4,
        KEY_TS_GIRDER_SPACING: 2.1,
        KEY_MP_ED_TYPE: "Welded Beam",
        KEY_MP_ED_TOTAL_DEPTH: 800.0,
        KEY_MP_ED_WEB_THICKNESS: 10.0,
        KEY_MP_ED_TOP_FLANGE_WIDTH: 250.0,
        KEY_MP_ED_TOP_FLANGE_THICKNESS: 16.0,
        KEY_MP_ED_BOTTOM_FLANGE_WIDTH: 250.0,
        KEY_MP_ED_BOTTOM_FLANGE_THICKNESS: 16.0,
    }
    outputs = {}
    q = calculate_material_quantities(inputs, outputs)
    
    # 3 bays * 2 ends = 6 welded beams
    assert q["end_diaphragm_qty"] == "6"
    assert float(q["end_diaphragm_vol_total"]) > 0.0
    assert float(q["end_diaphragm_wt_total"]) > 0.0


def test_boq_end_diaphragm_dynamic_scaling():
    # Test that 5 girders gives 4 bays * 8 = 32 members
    inputs_5g = {
        KEY_SPAN: 30.0,
        KEY_TS_NO_OF_GIRDERS: 5,
        KEY_TS_GIRDER_SPACING: 2.1,
        KEY_MP_GIRDER_DEPTH: 1.65,
        KEY_MP_ED_TYPE: "Cross Bracing",
    }
    outputs = {
        "transverse_member_design.ed.section_properties.end_diaphragm.G1G2.A": 2.37,
    }
    q = calculate_material_quantities(inputs_5g, outputs)
    # 4 bays * (4 diags + 2 top + 2 bot) = 32 members
    assert q["end_diaphragm_qty"] == "32"


# ── 3. Chart Generation tests ──────────────────────────────────────────────────

def test_plot_steel_tonnage_chart():
    steel_data = {
        "steel_girders_mt": 32.89,
        "cross_bracing_mt": 0.05,
        "end_diaphragm_mt": 0.10,
        "total_steel_mt": 33.04,
    }
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = os.path.join(tmp_dir, "test_steel.png")
        p = plot_steel_tonnage_chart(steel_data, out_path)
        assert os.path.exists(p)
        assert os.path.getsize(p) > 10000


def test_plot_concrete_rebar_chart():
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = os.path.join(tmp_dir, "test_conc_rebar.png")
        p = plot_concrete_rebar_chart(63.00, 7.56, out_path)
        assert os.path.exists(p)
        assert os.path.getsize(p) > 10000


def test_generate_all_material_charts():
    sample_data = {
        "steel_girders_wt_total": "32.89",
        "bracing_top_wt_total": "0.01",
        "bracing_bot_wt_total": "0.01",
        "bracing_diag_wt_total": "0.03",
        "end_diaphragm_wt_total": "0.10",
        "concrete_deck_vol_total": "63.00",
        "rebar_deck_wt_total": "7.56",
    }
    with tempfile.TemporaryDirectory() as tmp_dir:
        fig_dict = generate_all_material_charts(sample_data, tmp_dir)
        assert "material_chart_steel_tonnage" in fig_dict
        assert "material_chart_concrete_rebar" in fig_dict
        assert os.path.exists(fig_dict["material_chart_steel_tonnage"])
        assert os.path.exists(fig_dict["material_chart_concrete_rebar"])


# ── 4. LaTeX Chapter 7 integration tests ───────────────────────────────────────

def test_ch7_quantities_latex_output():
    inputs = {
        "steel_girders_vol_formula": r"$0.03492\text{ m}^2 \times 30.00\text{ m}$",
        "steel_girders_qty": "4",
        "steel_girders_vol_total": "4.19",
        "steel_girders_wt_single": "8.22",
        "steel_girders_wt_total": "32.89",
        "bracing_top_vol_formula": r"$0.00024\text{ m}^2 \times 2.10\text{ m}$",
        "bracing_top_qty": "3",
        "bracing_top_vol_total": "0.00",
        "bracing_top_wt_single": "0.0039",
        "bracing_top_wt_total": "0.01",
        "bracing_bot_vol_formula": r"$0.00024\text{ m}^2 \times 2.10\text{ m}$",
        "bracing_bot_qty": "3",
        "bracing_bot_vol_total": "0.00",
        "bracing_bot_wt_single": "0.0039",
        "bracing_bot_wt_total": "0.01",
        "bracing_diag_vol_formula": r"$0.00024\text{ m}^2 \times 2.53\text{ m}$",
        "bracing_diag_qty": "6",
        "bracing_diag_vol_total": "0.00",
        "bracing_diag_wt_single": "0.0047",
        "bracing_diag_wt_total": "0.03",
        "end_diaphragm_vol_formula": r"$0.00024\text{ m}^2 \times 2.31\text{ m}$",
        "end_diaphragm_qty": "24",
        "end_diaphragm_vol_total": "0.01",
        "end_diaphragm_wt_single": "0.0043",
        "end_diaphragm_wt_total": "0.10",
        "concrete_deck_vol_formula": r"$8.40\text{ m} \times 0.25\text{ m} \times 30.00\text{ m}$",
        "concrete_deck_qty": "1",
        "concrete_deck_vol_total": "63.00",
        "concrete_deck_wt_single": "157.50",
        "concrete_deck_wt_total": "157.50",
        "rebar_deck_vol_formula": r"$0.032102\text{ m}^2 \times 30.00\text{ m}$",
        "rebar_deck_qty": "1",
        "rebar_deck_vol_total": "0.96",
        "rebar_deck_wt_single": "7.56",
        "rebar_deck_wt_total": "7.56",
    }
    fig_paths = {
        "material_chart_steel_tonnage": "images/material_chart_steel_tonnage.png",
        "material_chart_concrete_rebar": "images/material_chart_concrete_rebar.png",
    }
    tex = ch7_quantities(inputs, fig_paths)

    # Verify Table 7.1 row for End Diaphragms 2(d)
    assert "2(d) & End Diaphragms (at Supports)" in tex
    assert "0.10" in tex
    assert "24" in tex

    # Verify explanatory note
    assert "standard structural design allowance of $120\\text{ kg/m}^3$" in tex
    assert "weighted average equivalent values per member across all 24 members" in tex
    assert "12 diagonals at $2.53\\text{ m}$" in tex
    assert "0.0047\\text{ MT}" in tex
    assert "0.0039\\text{ MT}" in tex
    assert "6 top chords at $2.10\\text{ m}$" in tex
    assert "6 bottom chords at $2.10\\text{ m}$" in tex

    # Verify visual section and both figures
    assert r"\section{Material Quantity Visualizations}" in tex
    assert r"\label{sec:material-charts}" in tex
    assert r"\caption{\textbf{Structural Steel Tonnage by Component}}" in tex
    assert r"\label{fig:mat_steel_tonnage}" in tex
    assert r"\caption{\textbf{Deck Slab Materials --- Concrete Volume vs.\ Reinforcement Steel Weight}}" in tex
    assert r"\label{fig:mat_concrete_rebar}" in tex
    assert "images/material_chart_steel_tonnage.png" in tex
    assert "images/material_chart_concrete_rebar.png" in tex


def test_boq_end_diaphragm_precision_and_reconciliation():
    """Verify internal numerical precision and reconciliation of individual member lengths."""
    import math

    inputs = {
        KEY_SPAN: 30.0,
        KEY_TS_NO_OF_GIRDERS: 4,
        KEY_TS_GIRDER_SPACING: 2.1,
        KEY_MP_GIRDER_DEPTH: 1.65,
        KEY_MP_ED_TYPE: "Cross Bracing",
    }
    outputs = {
        "transverse_member_design.ed.section_properties.end_diaphragm.G1G2.A": 2.37,
    }
    q = calculate_material_quantities(inputs, outputs)

    s = 2.10
    h_frame = 1.65 * 0.85
    L_diag = math.sqrt(s**2 + h_frame**2)  # 2.525274 m
    A = 2.37 / 10000.0  # 0.000237 m2
    density = 7.85

    # Individual calculations
    vol_diags = 12 * A * L_diag
    vol_tc = 6 * A * s
    vol_bc = 6 * A * s
    expected_vol = vol_diags + vol_tc + vol_bc  # 0.013154 m3
    expected_wt = expected_vol * density        # 0.103261 MT

    assert q["end_diaphragm_qty"] == "24"
    assert q["end_diaphragm_vol_total"] == f"{expected_vol:.2f}"
    assert q["end_diaphragm_wt_total"] == f"{expected_wt:.2f}"
    assert q["end_diaphragm_wt_single"] == f"{(expected_wt / 24):.4f}"

    # Verify that total length divided by 24 matches displayed average length
    total_len = (12 * L_diag) + (6 * s) + (6 * s)  # 55.5033 m
    avg_len = total_len / 24                         # 2.3126 m
    assert f"{avg_len:.2f}" in q["end_diaphragm_vol_formula"]


# ── 5. Advanced BOQ Section & Heterogeneity Tests ──────────────────────────────

def test_boq_cross_bracing_heterogeneous_panels():
    """Verify that cross bracing calculates independently per panel with different sections."""
    inputs = {
        KEY_SPAN: 30.0,
        KEY_TS_NO_OF_GIRDERS: 4,
        KEY_TS_GIRDER_SPACING: 2.1,
        KEY_MP_GIRDER_DEPTH: 1.65,
    }
    # G1G2 has 2.37 cm2, G2G3 has 4.79 cm2, G3G4 has 2.37 cm2
    outputs = {
        "crossbracing_forces_dict": {"geometry": {"diagonal_length_m": 2.53, "cb_spacing_m": 5.0}},
        "transverse_member_design.cb.section_properties.bracing.G1G2.A": 2.37,
        "transverse_member_design.cb.section_properties.bracing.G2G3.A": 4.79,
        "transverse_member_design.cb.section_properties.bracing.G3G4.A": 2.37,
    }
    q = calculate_material_quantities(inputs, outputs)

    assert q["bracing_diag_qty"] == "30"
    # Diagonals: 10 diags per bay * 2.53 m
    # G1G2: 10 * 0.000237 * 2.53 = 0.0059961 m3
    # G2G3: 10 * 0.000479 * 2.53 = 0.0121187 m3
    # G3G4: 10 * 0.000237 * 2.53 = 0.0059961 m3
    # Total vol = 0.02411 m3 -> 0.02 m3
    # Total wt = 0.02411 * 7.85 = 0.189 MT -> 0.19 MT
    assert q["bracing_diag_vol_total"] == "0.02"
    assert q["bracing_diag_wt_total"] == "0.19"
    assert "(avg)" in q["bracing_diag_vol_formula"]


def test_boq_cross_bracing_different_chord_and_diagonal_sections():
    """Verify distinct sections for chords and diagonals within the same panel."""
    inputs = {
        KEY_SPAN: 30.0,
        KEY_TS_NO_OF_GIRDERS: 4,
        KEY_TS_GIRDER_SPACING: 2.1,
        KEY_MP_GIRDER_DEPTH: 1.65,
    }
    outputs = {
        "crossbracing_forces_dict": {"geometry": {"diagonal_length_m": 2.53, "cb_spacing_m": 5.0}},
        "transverse_member_design.cb.section_properties.bracing.G1G2.A": 2.37,      # 237 mm2
        "transverse_member_design.cb.section_properties.top_chord.G1G2.A": 4.79,    # 479 mm2
        "transverse_member_design.cb.section_properties.bottom_chord.G1G2.A": 3.38, # 338 mm2
    }
    q = calculate_material_quantities(inputs, outputs)

    assert q["bracing_top_qty"] == "15"
    assert q["bracing_bot_qty"] == "15"
    assert q["bracing_diag_qty"] == "30"

    # Top chord wt: 15 * 0.000479 * 2.1 * 7.85 = 0.1184 MT -> 0.12 MT
    # Bot chord wt: 15 * 0.000338 * 2.1 * 7.85 = 0.0836 MT -> 0.08 MT
    # Diag wt: 30 * 0.000237 * 2.53 * 7.85 = 0.141 MT -> 0.14 MT
    assert q["bracing_top_wt_total"] == "0.12"
    assert q["bracing_bot_wt_total"] == "0.08"
    assert q["bracing_diag_wt_total"] == "0.14"


def test_boq_missing_final_design_properties_reports_na():
    """Verify that if final design outputs are missing, BOQ reports N.A. without fallback to initial inputs."""
    inputs = {
        KEY_SPAN: 30.0,
        KEY_TS_NO_OF_GIRDERS: 4,
        KEY_TS_GIRDER_SPACING: 2.1,
        KEY_MP_GIRDER_DEPTH: 1.65,
        KEY_MP_ED_TYPE: "Cross Bracing",
        # Initial user inputs (trial sections) that must NOT be used as final design values
        "member_properties.cross_bracing_details.bracing_section_designation.G1G2.B1M1": "ISA 100x100x10",
        "member_properties.end_diaphragm_details.bracing_section_designation.G1G2.E1M1": "L 100 x 100 x 10",
    }
    outputs = {}  # No final design results available
    q = calculate_material_quantities(inputs, outputs)

    assert q["bracing_diag_qty"] == "N.A."
    assert q["bracing_diag_vol_total"] == "N.A."
    assert q["bracing_diag_wt_total"] == "N.A."
    assert q["bracing_top_qty"] == "N.A."
    assert q["bracing_bot_qty"] == "N.A."
    assert q["end_diaphragm_qty"] == "N.A."
    assert q["end_diaphragm_vol_total"] == "N.A."
    assert q["end_diaphragm_wt_total"] == "N.A."


def test_boq_separation_of_cb_and_ed():
    """Verify strict separation: presence of intermediate cross bracings does NOT populate end diaphragms."""
    inputs = {
        KEY_SPAN: 30.0,
        KEY_TS_NO_OF_GIRDERS: 4,
        KEY_TS_GIRDER_SPACING: 2.1,
        KEY_MP_GIRDER_DEPTH: 1.65,
        KEY_MP_ED_TYPE: "Cross Bracing",
    }
    # Outputs ONLY contains intermediate cross bracing
    outputs = {
        "crossbracing_forces_dict": {"geometry": {"diagonal_length_m": 2.53, "cb_spacing_m": 5.0}},
        "transverse_member_design.cb.section_properties.bracing.G1G2.A": 2.37,
    }
    q = calculate_material_quantities(inputs, outputs)

    # Intermediate cross bracing is valid
    assert q["bracing_diag_qty"] == "30"
    assert q["bracing_diag_wt_total"] == "0.14"

    # End diaphragms have NO outputs and must remain strictly N.A.
    assert q["end_diaphragm_qty"] == "N.A."
    assert q["end_diaphragm_wt_total"] == "N.A."
    assert q["end_diaphragm_vol_formula"] == "N.A."


def test_boq_end_diaphragm_heterogeneous_panels():
    """Verify end diaphragm calculation when different bays have different final sections."""
    inputs = {
        KEY_SPAN: 30.0,
        KEY_TS_NO_OF_GIRDERS: 4,
        KEY_TS_GIRDER_SPACING: 2.1,
        KEY_MP_GIRDER_DEPTH: 1.65,
        KEY_MP_ED_TYPE: "Cross Bracing",
    }
    # G1G2 has 2.37 cm2, G2G3 has 4.79 cm2, G3G4 has 2.37 cm2
    outputs = {
        "transverse_member_design.ed.section_properties.end_diaphragm.G1G2.A": 2.37,
        "transverse_member_design.ed.section_properties.end_diaphragm.G2G3.A": 4.79,
        "transverse_member_design.ed.section_properties.end_diaphragm.G3G4.A": 2.37,
    }
    q = calculate_material_quantities(inputs, outputs)

    assert q["end_diaphragm_qty"] == "24"
    # G1G2: (4*2.5253 + 2*2.1 + 2*2.1) * 0.000237 = 18.5012 * 0.000237 = 0.0043848 m3
    # G2G3: 18.5012 * 0.000479 = 0.0088621 m3
    # G3G4: 18.5012 * 0.000237 = 0.0043848 m3
    # Total vol = 0.01763 m3 -> 0.02 m3
    # Total wt = 0.01763 * 7.85 = 0.1384 MT -> 0.14 MT
    assert q["end_diaphragm_vol_total"] == "0.02"
    assert q["end_diaphragm_wt_total"] == "0.14"
    assert "(avg)" in q["end_diaphragm_vol_formula"]


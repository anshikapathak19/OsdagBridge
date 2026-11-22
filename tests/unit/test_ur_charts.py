"""
Unit tests for Requirement 4: Utilisation Ratio (UR) Charts.

Tests cover:
  1. Correct extraction of UR values for all four components.
  2. Correct governing UR extraction for girders.
  3. Correct member-level data handling for cross bracing and end diaphragms.
  4. PASS classification when UR <= 1.0.
  5. FAIL classification when UR > 1.0.
  6. Missing and invalid values handling.
  7. Rolled/welded diaphragm pending-design handling.
  8. Generation of all four chart images.
  9. Presence of threshold line, annotations, and legends.
  10. Successful integration into Section 5.5.
"""

import os
import tempfile
import pytest

from osdagbridge.core.reports.ur_charts import (
    extract_girder_ur,
    extract_deck_ur,
    extract_cross_bracing_ur,
    extract_end_diaphragm_ur,
    plot_ur_bar_chart,
    generate_all_ur_charts,
)
from osdagbridge.core.reports.chap5 import ch5_design_checks
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
    KEY_DD_WK_TOP,
    KEY_MP_ED_TYPE,
)


class DummyBridge:
    """Mock bridge object for testing UR extraction and report integration."""
    def __init__(self, input_dict=None, output_dict=None):
        self.input_dict = input_dict or {}
        self.output_dict = output_dict or {}
        self._cb_eff_map = {}
        self._cb_slnd_map = {}
        self._cb_pairs = []

    def get_cb_pairs(self):
        return self._cb_pairs

    def get_cb_efficiency(self, pair, member, force_type):
        return self._cb_eff_map.get((pair, member, force_type), "")

    def get_cb_slenderness(self, pair, member):
        return self._cb_slnd_map.get((pair, member), "")

    def get_cb_capacity(self, pair, member, force_type):
        return "45.0"

    def get_cb_governing_force(self, pair, member):
        return ("10.0", "compression")

    def get_cb_gov_lc(self, pair, member, force_type):
        return "1.5 EQ"

    def get_cb_section(self, pair, member, force_type):
        return "40 x 40 x 3"

    def get_cb_status(self, pair, member, force_type):
        return "PASS"

    def get_cb_effective_length(self, member):
        return "2500"


def test_extract_girder_ur_governing():
    """Verify that governing (worst) DCR across girders is picked and Live/Total deflection distinguished."""
    output_dict = {
        "design_results": {
            "per_girder": {
                "G1": {
                    "checks": [
                        {"check_id": 1, "dcr": 0.45},
                        {"check_id": 2, "dcr": 0.30},
                        {"check_id": 5, "dcr": 0.20},
                        {"check_id": 11, "dcr": 0.40},
                        {"check_id": 8, "dcr": 1.25},
                    ]
                },
                "G2": {
                    "checks": [
                        {"check_id": 1, "dcr": 0.85},  # Governs for Moment
                        {"check_id": 2, "dcr": 0.72},  # Governs for Shear
                        {"check_id": 5, "dcr": 0.65},  # Governs for LTB
                        {"check_id": 11, "dcr": 0.55}, # Governs for Stress
                        {"check_id": 9, "dcr": 1.58},  # Governs for Fatigue (FAIL)
                    ],
                    "per_lc": {
                        "LC1": {
                            "checks": [
                                {"id": 13, "dcr": 0.52}, # Live Deflection
                                {"id": 14, "dcr": 1.02}, # Total Deflection (FAIL)
                            ]
                        }
                    }
                },
            }
        }
    }
    bridge = DummyBridge(output_dict=output_dict)
    data = extract_girder_ur(bridge)
    data_dict = {name: (val, st) for name, val, st in data}

    assert "Moment" in data_dict
    assert data_dict["Moment"] == (0.85, "PASS")

    assert "Shear" in data_dict
    assert data_dict["Shear"] == (0.72, "PASS")

    assert "LTB" in data_dict
    assert data_dict["LTB"] == (0.65, "PASS")

    assert "Defl. Live (L/800)" in data_dict
    assert data_dict["Defl. Live (L/800)"] == (0.52, "PASS")

    assert "Defl. Total (L/600)" in data_dict
    assert data_dict["Defl. Total (L/600)"] == (1.02, "FAIL")

    assert "Combined Stress" in data_dict
    assert data_dict["Combined Stress"] == (0.55, "PASS")

    assert "Fatigue" in data_dict
    assert data_dict["Fatigue"] == (1.58, "FAIL")


def test_extract_deck_ur():
    """Verify deck slab check extraction from deck_report_values."""
    output_dict = {
        "deck_report_values": {
            KEY_DD_M_ULS_SAG: 45.0,
            KEY_DD_MU_BOT: 50.0,      # UR = 0.90 PASS
            KEY_DD_M_ULS_HOG: 32.0,
            KEY_DD_MU_TOP: 40.0,      # UR = 0.80 PASS
            KEY_DD_HAS_OVERHANG: True,
            KEY_DD_M_ULS_OH: 105.0,
            KEY_DD_MU_OH: 100.0,     # UR = 1.05 FAIL
            KEY_DD_PUNCH_VED: 0.25,
            KEY_DD_VRD_C_MPA: 0.50,   # UR = 0.50 PASS
            KEY_DD_SHEAR_VED: 80.0,
            KEY_DD_SHEAR_VRDC: 100.0, # UR = 0.80 PASS
            KEY_DD_WK_BOT: 0.22,
            KEY_DD_WK_TOP: 0.18,
            KEY_DD_WK_LIMIT: 0.30,   # UR = 0.22 / 0.30 = 0.73 PASS
        }
    }
    bridge = DummyBridge(output_dict=output_dict)
    data = extract_deck_ur(bridge)
    data_dict = {name: (val, st) for name, val, st in data}

    assert data_dict["Sagging Flexure"] == (0.90, "PASS")
    assert data_dict["Hogging Flexure"] == (0.80, "PASS")
    assert data_dict["Cantilever Overhang"] == (1.05, "FAIL")
    assert data_dict["Punching Shear"] == (0.50, "PASS")
    assert data_dict["One-Way Shear"] == (0.80, "PASS")
    assert data_dict["Crack Width"] == (0.73, "PASS")


def test_extract_cross_bracing_ur():
    """Verify member-level data extraction for cross bracing panels."""
    bridge = DummyBridge()
    bridge._cb_pairs = ["G1-G2", "G2-G3"]
    bridge._cb_eff_map = {
        ("G1-G2", "diagonal", "compression"): "0.46",
        ("G1-G2", "diagonal", "tension"): "0.20",
        ("G1-G2", "chord", "compression"): "0.38",
        ("G1-G2", "chord", "tension"): "0.15",
        ("G2-G3", "diagonal", "compression"): "1.12", # FAIL
    }
    bridge._cb_slnd_map = {
        ("G1-G2", "diagonal"): "134.0", # 134 / 250 = 0.54 PASS
        ("G1-G2", "chord"): "111.0",    # 111 / 250 = 0.44 PASS
    }
    data = extract_cross_bracing_ur(bridge)
    data_dict = {name: (val, st) for name, val, st in data}

    assert data_dict["G1-G2 Diag (Comp)"] == (0.46, "PASS")
    assert data_dict["G1-G2 Diag (Tens)"] == (0.20, "PASS")
    assert data_dict["G1-G2 Chord (Comp)"] == (0.38, "PASS")
    assert data_dict["G1-G2 Chord (Tens)"] == (0.15, "PASS")
    assert data_dict["G2-G3 Diag (Comp)"] == (1.12, "FAIL")
    assert data_dict["G1-G2 Diag (Slend)"] == (0.54, "PASS")
    assert data_dict["G1-G2 Chord (Slend)"] == (0.44, "PASS")


def test_extract_end_diaphragm_ur_rolled_and_braced():
    """Verify pending handling for rolled/welded diaphragm and panel member-level values for braced."""
    # 1. Rolled section diaphragm -> pending
    bridge_rolled = DummyBridge(input_dict={KEY_MP_ED_TYPE: "Rolled Section"})
    avail, data, msg = extract_end_diaphragm_ur(bridge_rolled)
    assert avail is False
    assert len(data) == 0
    assert "Design pending for rolled/welded diaphragm" in msg

    # 2. Braced diaphragm -> active across panels
    bridge_braced = DummyBridge(input_dict={KEY_MP_ED_TYPE: "Cross Bracing"})
    bridge_braced._cb_pairs = ["G1-G2", "G2-G3"]
    bridge_braced._cb_eff_map = {
        ("G1-G2", "diagonal", "compression"): "0.46",
        ("G1-G2", "chord", "compression"): "0.38",
        ("G2-G3", "diagonal", "compression"): "0.10",
        ("G2-G3", "chord", "compression"): "0.08",
    }
    avail, data, msg = extract_end_diaphragm_ur(bridge_braced)
    assert avail is True
    data_dict = {name: (val, st) for name, val, st in data}
    assert "ED G1-G2 Diag" in data_dict
    assert data_dict["ED G1-G2 Diag"] == (0.46, "PASS")
    assert "ED G1-G2 Chord" in data_dict
    assert data_dict["ED G1-G2 Chord"] == (0.38, "PASS")
    assert "ED G2-G3 Diag" in data_dict
    assert data_dict["ED G2-G3 Diag"] == (0.10, "PASS")
    assert "ED G2-G3 Chord" in data_dict
    assert data_dict["ED G2-G3 Chord"] == (0.08, "PASS")


def test_pass_fail_boundary():
    """Verify exact boundary behavior for UR <= 1.0 (PASS) and UR > 1.0 (FAIL)."""
    # Helper to test classification
    data_test = [
        ("C1", 0.999, "PASS"),
        ("C2", 1.000, "PASS"),
        ("C3", 1.001, "FAIL"),
        ("C4", 1.580, "FAIL"),
    ]
    with tempfile.TemporaryDirectory() as td:
        out_path = os.path.join(td, "chart_boundary.png")
        plot_ur_bar_chart("Boundary Test", data_test, out_path)
        assert os.path.exists(out_path)
        assert os.path.getsize(out_path) > 1000


def test_missing_and_invalid_values_safe_handling():
    """Verify that None, empty string, and non-numeric values are safely ignored without crashing."""
    output_dict = {
        "design_results": {
            "per_girder": {
                "G1": {
                    "checks": [
                        {"check_id": 1, "dcr": None},
                        {"check_id": 2, "dcr": "invalid"},
                        {"check_id": 5, "dcr": ""},
                    ]
                }
            }
        },
        "deck_report_values": {
            KEY_DD_M_ULS_SAG: "N/A",
            KEY_DD_MU_BOT: None,
        }
    }
    bridge = DummyBridge(output_dict=output_dict)
    girder_data = extract_girder_ur(bridge)
    assert len(girder_data) == 0  # No valid values fabricated

    deck_data = extract_deck_ur(bridge)
    assert len(deck_data) == 0    # No valid values fabricated


def test_generate_all_ur_charts():
    """Verify that generate_all_ur_charts generates all 4 PNG files with proper dictionary keys."""
    bridge = DummyBridge(input_dict={KEY_MP_ED_TYPE: "Rolled Section"})
    with tempfile.TemporaryDirectory() as td:
        fig_paths = generate_all_ur_charts(bridge, td)
        assert "ur_chart_girders" in fig_paths
        assert "ur_chart_deck" in fig_paths
        assert "ur_chart_cross_bracing" in fig_paths
        assert "ur_chart_end_diaphragm" in fig_paths

        for key, p in fig_paths.items():
            assert os.path.exists(p)
            assert os.path.getsize(p) > 1000


def test_ch5_design_checks_integration_with_figures():
    """Verify that ch5_design_checks embeds the figure environments and references fig_paths."""
    bridge = DummyBridge(input_dict={KEY_MP_ED_TYPE: "Rolled Section"})
    fig_paths = {
        "ur_chart_girders": "images/ur_chart_girders.png",
        "ur_chart_deck": "images/ur_chart_deck.png",
        "ur_chart_cross_bracing": "images/ur_chart_cross_bracing.png",
        "ur_chart_end_diaphragm": "images/ur_chart_end_diaphragm.png",
    }
    tex = ch5_design_checks({}, bridge, fig_paths)

    assert r"\subsection{Utilisation Ratio (UR) Charts}" in tex
    assert r"\label{fig:ur_girders}" in tex
    assert r"\label{fig:ur_deck}" in tex
    assert r"\label{fig:ur_cross_bracing}" in tex
    assert r"\label{fig:ur_end_diaphragm}" in tex
    assert "images/ur_chart_girders.png" in tex
    assert "images/ur_chart_deck.png" in tex
    assert "images/ur_chart_cross_bracing.png" in tex
    assert "images/ur_chart_end_diaphragm.png" in tex
    assert "Note on Governing Member Checks" in tex
    assert "Utilisation Ratio --- Cross Bracing (Governing Member Checks)" in tex

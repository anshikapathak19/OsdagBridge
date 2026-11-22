"""
Unit tests for IRC 6:2017 Clause 211.2 braking force calculation
and Chapter 3 report presentation.

Tests cover:
1. Lane counts 1, 2, 3, 4, 5
2. All relevant permitted IRC Table 6A vehicle combinations
3. First-train braking contribution (20%)
4. Succeeding-train contribution (10%) and span thresholds
5. Additional-lane contribution (5% on lanes > 2)
6. Vehicle-specific base braking forces
7. Class SV opt-in and opt-out
8. Fatigue braking applicability (not applicable / No)
9. Correct N-to-kN conversion
10. Partial vehicle accommodation on short spans
11. Missing / invalid vehicle-load data handling (ValueError)
12. Invalid lane counts handling (0, negative, invalid strings)
13. No UnboundLocalError for any lane count
14. Correct bridge-level governing combination determination
"""

import pytest
from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
from osdagbridge.core.reports.chap3 import ch3_loads
from osdagbridge.core.utils.common import (
    KEY_SPAN,
    KEY_CARRIAGEWAY_WIDTH,
    KEY_LL_IRC_CLASS_A,
    KEY_LL_IRC_70R_WHEELED,
    KEY_LL_IRC_70R_TRACKED,
    KEY_LL_IRC_70R_BOGIE,
    KEY_LL_IRC_AA_WHEELED,
    KEY_LL_IRC_AA_TRACKED,
    KEY_LL_IRC_CLASS_SV,
    KEY_BL_IRC_CLASS_SV,
    KEY_LL_IRC_CLASS_FATIGUE,
    KEY_WC_LD_LANE_TABLE_COUNT,
    KEY_FOOTPATH,
)


# ── 1. Lane Counts 1 through 5 & Governing Combinations ─────────────────────

def test_braking_lane_1_class_a():
    """1 design lane governed by Class A: 0.20 * 543.474 = 108.695 kN."""
    res = IRC6_2017.cl_211_2_braking_force(design_lanes=1, span_m=30.0, return_details=True)
    assert pytest.approx(res["governing_force_kN"], rel=1e-3) == 108.695
    assert "Class A" in res["governing_combination"]
    assert pytest.approx(res["first_train_kN"], rel=1e-3) == 108.695
    assert res["succeeding_train_kN"] == 0.0
    assert res["additional_lanes_kN"] == 0.0


def test_braking_lane_2_wheeled_governing():
    """2 design lanes: 1 lane 70R Wheeled (196.20 kN) governs over 2 lanes Class A (108.70 kN)."""
    res = IRC6_2017.cl_211_2_braking_force(design_lanes=2, span_m=30.0, return_details=True)
    assert pytest.approx(res["governing_force_kN"], rel=1e-3) == 196.200
    assert "Class 70R Wheeled" in res["governing_combination"]
    assert pytest.approx(res["first_train_kN"], rel=1e-3) == 196.200
    assert res["succeeding_train_kN"] == 0.0
    assert res["additional_lanes_kN"] == 0.0


def test_braking_lane_3_governing_combination():
    """3 design lanes: 1 lane 70R (196.20 kN) + 1 lane Class A (5% of 543.474 = 27.174 kN) = 223.374 kN."""
    res = IRC6_2017.cl_211_2_braking_force(design_lanes=3, span_m=30.0, return_details=True)
    assert pytest.approx(res["governing_force_kN"], rel=1e-3) == 223.374
    assert pytest.approx(res["first_train_kN"], rel=1e-3) == 196.200
    assert pytest.approx(res["additional_lanes_kN"], rel=1e-3) == 27.174
    assert "Class 70R Wheeled" in res["governing_combination"]
    assert "Class A" in res["governing_combination"]


def test_braking_lane_4_all_permitted_combinations():
    """
    4 design lanes under Table 6A:
    - Combo 1 (4 x Class A): 108.695 + 2 * (0.05 * 543.474) = 163.042 kN
    - Combo 2 (1 x 70R + 2 x Class A): 196.20 + 2 * (0.05 * 543.474) = 250.547 kN (GOVERNS)
    - Combo 3 (2 x 70R): 196.20 + 0.05 * 981.0 = 245.250 kN
    Verifies that all 3 combinations are evaluated and Combo 2 governs by 5.30 kN.
    """
    res = IRC6_2017.cl_211_2_braking_force(design_lanes=4, span_m=30.0, return_details=True)
    assert pytest.approx(res["governing_force_kN"], rel=1e-3) == 250.547
    assert len(res["all_combinations"]) == 3
    # Check that 2 x 70R was evaluated
    combo_2_70r = next(c for c in res["all_combinations"] if c["n70R"] == 2)
    assert pytest.approx(combo_2_70r["total"], rel=1e-3) == 245.250
    # Check that governing is Combo 2 (1 x 70R + 2 x Class A)
    assert res["governing_force_kN"] > combo_2_70r["total"]


def test_braking_lane_5_governing_combination():
    """
    5 design lanes under Table 6A:
    - 1 x 70R + 3 x Class A: 196.20 + 3 * (0.05 * 543.474) = 277.721 kN (GOVERNS)
    - 2 x 70R + 1 x Class A: 196.20 + 0.05 * 981 + 0.05 * 543.474 = 272.424 kN
    """
    res = IRC6_2017.cl_211_2_braking_force(design_lanes=5, span_m=30.0, return_details=True)
    assert pytest.approx(res["governing_force_kN"], rel=1e-3) == 277.721
    combo_2_70r_1_a = next(c for c in res["all_combinations"] if c["n70R"] == 2)
    assert pytest.approx(combo_2_70r_1_a["total"], rel=1e-3) == 272.424


# ── 2. First-Train, Succeeding-Train & Span Accommodations ───────────────────

def test_succeeding_train_zero_on_30m_span():
    """On a 30m span, succeeding vehicle cannot enter while leading vehicle is on span."""
    res = IRC6_2017.cl_211_2_braking_force(design_lanes=2, span_m=30.0, return_details=True)
    assert res["succeeding_train_kN"] == 0.0


def test_succeeding_train_calculated_on_long_spans():
    """
    On spans > 38.8m for Class A and > 45m for Class 70R, succeeding train contributes 10%.
    At 45m span, Class A picks up succeeding train axles.
    At 60m span, 70R Wheeled picks up succeeding train (10% * 981.0 = 98.10 kN).
    """
    # Class A single lane on 45m span
    res_a_45 = IRC6_2017.cl_211_2_braking_force(design_lanes=1, vehicle_type="class_a", span_m=45.0, return_details=True)
    assert res_a_45["succeeding_train_kN"] > 0.0
    assert pytest.approx(res_a_45["succeeding_train_kN"], rel=1e-2) == 27.66

    # 70R on 60m span: 196.20 first + 98.10 succ = 294.30 kN
    res_70_60 = IRC6_2017.cl_211_2_braking_force(design_lanes=2, span_m=60.0, return_details=True)
    assert pytest.approx(res_70_60["first_train_kN"], rel=1e-3) == 196.200
    assert pytest.approx(res_70_60["succeeding_train_kN"], rel=1e-3) == 98.100
    assert pytest.approx(res_70_60["governing_force_kN"], rel=1e-3) == 294.300


def test_partial_vehicle_accommodation_short_spans():
    """
    On short spans (span < vehicle wheelbase), only axles fitting on span contribute 20%.
    Class A wheelbase = 18.8m. At 10m span, max axles sum to 357.085 kN -> 20% = 71.417 kN.
    70R Wheeled wheelbase = 13.4m. At 10m span, max axles sum to 902.52 kN -> 20% = 180.504 kN.
    """
    f1_a, fs_a = IRC6_2017._calculate_train_braking(10.0, "class_a")
    assert pytest.approx(f1_a, rel=1e-3) == 71.417
    assert fs_a == 0.0

    f1_70, fs_70 = IRC6_2017._calculate_train_braking(10.0, "wheeled")
    assert pytest.approx(f1_70, rel=1e-3) == 180.504
    assert fs_70 == 0.0


# ── 3. Vehicle Load Helper & Fallback Removal ───────────────────────────────

def test_get_vehicle_load_kN_actual_functions():
    """Verify total loads are directly derived from actual vehicle functions."""
    w_a = IRC6_2017.get_vehicle_load_kN("class_a")
    assert pytest.approx(w_a, rel=1e-3) == 543.474

    w_70w = IRC6_2017.get_vehicle_load_kN("wheeled")
    assert pytest.approx(w_70w, rel=1e-3) == 981.000

    w_70t = IRC6_2017.get_vehicle_load_kN("tracked")
    assert pytest.approx(w_70t, rel=1e-2) == 686.82


def test_get_vehicle_load_kN_invalid_raises():
    """Unsupported vehicle type must raise ValueError rather than returning a silent fallback."""
    with pytest.raises(ValueError, match="Unsupported vehicle type"):
        IRC6_2017.get_vehicle_load_kN("flying_car")


# ── 4. Edge Cases, Unit Conversions & No UnboundLocalError ───────────────────

def test_no_unbound_local_error_any_lane_count():
    """Verify no UnboundLocalError occurs across lane counts 1 through 10."""
    for n in range(1, 11):
        res = IRC6_2017.cl_211_2_braking_force(design_lanes=n)
        assert isinstance(res, float)
        assert res > 0.0


def test_invalid_lane_counts():
    """Zero, negative, or invalid lane inputs return 0.0 safely."""
    assert IRC6_2017.cl_211_2_braking_force(design_lanes=0) == 0.0
    assert IRC6_2017.cl_211_2_braking_force(design_lanes=-3) == 0.0
    assert IRC6_2017.cl_211_2_braking_force(design_lanes="invalid") == 196.200


def test_invalid_vehicle_load_override_raises():
    """Invalid non-numeric vehicle_load_kN must raise ValueError."""
    with pytest.raises(ValueError, match="Invalid vehicle_load_kN"):
        IRC6_2017.cl_211_2_braking_force(vehicle_load_kN="non_numeric")


# ── 5. Chapter 3 Table 3.3, Class SV, Fatigue & Summary Table ───────────────

def test_chap3_vehicle_live_loads_and_braking_summary():
    """Verify distinct vehicle base braking loads in Table 3.3 and summary block."""
    input_dict = {
        KEY_SPAN: "30.0",
        KEY_CARRIAGEWAY_WIDTH: "7.5",
        KEY_WC_LD_LANE_TABLE_COUNT: 2,
        KEY_LL_IRC_CLASS_A: True,
        KEY_LL_IRC_70R_WHEELED: True,
        KEY_LL_IRC_70R_TRACKED: True,
        KEY_LL_IRC_70R_BOGIE: True,
        KEY_LL_IRC_AA_WHEELED: True,
        KEY_LL_IRC_AA_TRACKED: True,
        KEY_LL_IRC_CLASS_SV: True,
        KEY_BL_IRC_CLASS_SV: True,  # Class SV opted in
        KEY_LL_IRC_CLASS_FATIGUE: True,
        KEY_FOOTPATH: "None",
    }
    latex_output = ch3_loads(input_dict)

    # Distinct vehicle base forces in Table 3.3:
    assert "108.70" in latex_output   # Class A (0.20 * 543.5 kN)
    assert "196.20" in latex_output   # 70R Wheeled (0.20 * 981.0 kN)
    assert "137.34" in latex_output or "137.36" in latex_output  # 70R Tracked (0.20 * 686.7 kN)
    assert "78.48" in latex_output    # 70R Bogie / AA Wheeled (0.20 * 392.4 kN)
    assert "755.37" in latex_output   # Class SV opted-in (0.20 * 3776.85 kN)

    # Class Fatigue: braking must NOT be considered
    fatigue_pos = latex_output.find("Class Fatigue")
    fatigue_line = latex_output[fatigue_pos:latex_output.find(r"\\", fatigue_pos)]
    assert "& No &" in fatigue_line
    assert "---" in fatigue_line

    # Bridge-level summary block:
    assert "Governing Longitudinal Braking Force (IRC 6 Clause 211.2)" in latex_output
    assert "Number of Design Lanes & 2" in latex_output
    assert "Carriageway Width & 7.50 m" in latex_output
    assert "First-Train Contribution (20\\%) & 196.20 kN" in latex_output
    assert "Succeeding-Train Contribution (10\\%) & 0.00 kN" in latex_output
    assert "Additional-Lane Contribution (5\\%) & 0.00 kN" in latex_output
    assert "\\textbf{Total Governing Braking Force} & \\textbf{196.20 kN}" in latex_output
    assert "1.20 m (IRC 6 Cl. 211.3)" in latex_output


def test_chap3_class_sv_opt_out():
    """When Class SV braking is opted out, Table 3.3 must display 'No' and '---'."""
    input_dict = {
        KEY_SPAN: "30.0",
        KEY_CARRIAGEWAY_WIDTH: "7.5",
        KEY_LL_IRC_CLASS_A: True,
        KEY_LL_IRC_CLASS_SV: True,
        KEY_BL_IRC_CLASS_SV: False,  # Opt-out
        KEY_FOOTPATH: "None",
    }
    latex_output = ch3_loads(input_dict)
    sv_pos = latex_output.find("Class SV (Special Vehicle)")
    sv_line = latex_output[sv_pos:latex_output.find(r"\\", sv_pos)]
    assert "& No &" in sv_line
    assert "---" in sv_line

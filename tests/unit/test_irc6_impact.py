import sys
import os

# Ensure src is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

try:
    import pytest
except ImportError:
    pytest = None

from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017

TEST_CASES = [
    # ── 1. Benchmark Spans: 30 m ───────────────────────────────────────
    (30.0, "wheeled",            0.207, "30m Wheeled: 9.0 / (13.5 + 30.0)"),
    (30.0, "tracked",            0.100, "30m Tracked: constant 10% for span >= 9m"),
    (30.0, "Class70R(W)",        0.207, "30m Class70R(W): wheeled heavy"),
    (30.0, "Class 70R (Wheeled)",0.207, "30m Class 70R (Wheeled): wheeled heavy"),
    (30.0, "Class70R(T)",        0.100, "30m Class70R(T): tracked heavy"),
    (30.0, "Class 70R (Tracked)",0.100, "30m Class 70R (Tracked): tracked heavy"),
    (30.0, "Class70R(Bogie)",    0.207, "30m Class70R(Bogie): wheeled bogie"),
    (30.0, "bogie",              0.207, "30m bogie: wheeled bogie"),
    (30.0, "ClassAA(W)",         0.207, "30m ClassAA(W): wheeled heavy"),
    (30.0, "Class AA (Wheeled)", 0.207, "30m Class AA (Wheeled): wheeled heavy"),
    (30.0, "ClassAA(T)",         0.100, "30m ClassAA(T): tracked heavy"),
    (30.0, "Class AA (Tracked)", 0.100, "30m Class AA (Tracked): tracked heavy"),

    # ── 2. Short Spans: Below 5 m (e.g. 4 m) ───────────────────────────
    (4.0,  "wheeled",            0.250, "4m Wheeled: 25% for span < 23m"),
    (4.0,  "tracked",            0.250, "4m Tracked: 25% for span < 5m"),

    # ── 3. Exact Boundary: Exactly 5 m ─────────────────────────────────
    (5.0,  "wheeled",            0.250, "5m Wheeled: 25% for span < 23m"),
    (5.0,  "tracked",            0.250, "5m Tracked: 25% at 5m threshold"),

    # ── 4. Intermediate Spans: 5 m to 9 m (e.g. 7 m) ───────────────────
    (7.0,  "wheeled",            0.250, "7m Wheeled: 25% for span < 23m"),
    (7.0,  "tracked",            0.175, "7m Tracked: linear ramp (0.25 - 2 * 0.0375 = 0.175)"),

    # ── 5. Exact Boundary: Exactly 9 m ─────────────────────────────────
    (9.0,  "wheeled",            0.250, "9m Wheeled: 25% for span < 23m"),
    (9.0,  "tracked",            0.100, "9m Tracked: exactly 10% at 9m boundary"),

    # ── 6. Intermediate Spans: 9 m to 23 m (e.g. 15 m) ─────────────────
    (15.0, "wheeled",            0.250, "15m Wheeled: 25% for span < 23m"),
    (15.0, "tracked",            0.100, "15m Tracked: constant 10% for span >= 9m"),

    # ── 7. Exact Boundary: Exactly 23 m ────────────────────────────────
    (23.0, "wheeled",            0.247, "23m Wheeled: 9.0 / (13.5 + 23.0) = 0.2466 -> 0.247"),
    (23.0, "tracked",            0.100, "23m Tracked: constant 10% for span >= 9m"),

    # ── 8. Exact Boundary: Exactly 45 m ────────────────────────────────
    (45.0, "wheeled",            0.154, "45m Wheeled: 9.0 / (13.5 + 45.0) = 0.1538 -> 0.154"),
    (45.0, "tracked",            0.100, "45m Tracked: constant 10% for span >= 9m"),

    # ── 9. Long Spans: Above 45 m (e.g. 50 m, capped at 45 m) ──────────
    (50.0, "wheeled",            0.154, "50m Wheeled: capped at 45m value (0.154)"),
    (50.0, "tracked",            0.100, "50m Tracked: constant 10% for span >= 9m"),
]

if pytest is not None:
    @pytest.mark.parametrize("span,vehicle,expected_im,clause_desc", TEST_CASES)
    def test_cl_208_3_parameterized(span, vehicle, expected_im, clause_desc):
        val = IRC6_2017.cl_208_3_impact_factor(span, vehicle_type=vehicle)
        assert abs(val - expected_im) < 0.001, f"Failed for {clause_desc}"


def test_cl_208_3_backward_compatibility():
    """Verify that calling cl_208_3_impact_factor with only span defaults to wheeled."""
    val_30 = IRC6_2017.cl_208_3_impact_factor(30.0)
    assert val_30 == 0.207, f"Expected 0.207 for 30m default, got {val_30}"

    val_15 = IRC6_2017.cl_208_3_impact_factor(15.0)
    assert val_15 == 0.250, f"Expected 0.250 for 15m default, got {val_15}"

    val_50 = IRC6_2017.cl_208_3_impact_factor(50.0)
    assert val_50 == 0.154, f"Expected 0.154 for 50m default, got {val_50}"


def test_cl_208_3_is_tracked_flag():
    """Verify explicit is_tracked boolean flag overrides vehicle_type."""
    assert IRC6_2017.cl_208_3_impact_factor(30.0, is_tracked=True) == 0.100
    assert IRC6_2017.cl_208_3_impact_factor(30.0, is_tracked=False) == 0.207

    # is_tracked=True overrides vehicle_type='wheeled'
    assert IRC6_2017.cl_208_3_impact_factor(30.0, vehicle_type="wheeled", is_tracked=True) == 0.100
    # is_tracked=False overrides vehicle_type='tracked'
    assert IRC6_2017.cl_208_3_impact_factor(30.0, vehicle_type="tracked", is_tracked=False) == 0.207


def test_cl_208_3_invalid_vehicle_type():
    """Verify that unrecognized vehicle types raise a descriptive ValueError."""
    try:
        IRC6_2017.cl_208_3_impact_factor(30.0, vehicle_type="airplane")
        assert False, "Should have raised ValueError for unrecognized vehicle_type"
    except ValueError as e:
        assert "Unrecognized vehicle_type" in str(e)

    try:
        IRC6_2017.cl_208_3_impact_factor(30.0, vehicle_type="unknown_vehicle")
        assert False, "Should have raised ValueError for unknown_vehicle"
    except ValueError as e:
        assert "Unrecognized vehicle_type" in str(e)


def test_cl_208_3_invalid_span_inputs():
    """Verify that zero, negative, and non-numeric spans raise ValueError."""
    try:
        IRC6_2017.cl_208_3_impact_factor(0)
        assert False, "Should have raised ValueError for zero span"
    except ValueError as e:
        assert "Span must be a positive number" in str(e)

    try:
        IRC6_2017.cl_208_3_impact_factor(-10.0)
        assert False, "Should have raised ValueError for negative span"
    except ValueError as e:
        assert "Span must be a positive number" in str(e)

    try:
        IRC6_2017.cl_208_3_impact_factor("invalid_span")
        assert False, "Should have raised ValueError for non-numeric span"
    except ValueError as e:
        assert "Span must be a valid numeric value" in str(e)


def run_all_tests():
    print("Running parameterized span and vehicle tests (28 cases)...")
    for span, vehicle, expected_im, clause_desc in TEST_CASES:
        val = IRC6_2017.cl_208_3_impact_factor(span, vehicle_type=vehicle)
        assert abs(val - expected_im) < 0.001, f"Failed for {clause_desc}: got {val}, expected {expected_im}"
    print(f"PASS: {len(TEST_CASES)} parameterized test cases passed.")

    print("Running test_cl_208_3_backward_compatibility...")
    test_cl_208_3_backward_compatibility()
    print("PASS: test_cl_208_3_backward_compatibility passed.")

    print("Running test_cl_208_3_is_tracked_flag...")
    test_cl_208_3_is_tracked_flag()
    print("PASS: test_cl_208_3_is_tracked_flag passed.")

    print("Running test_cl_208_3_invalid_vehicle_type...")
    test_cl_208_3_invalid_vehicle_type()
    print("PASS: test_cl_208_3_invalid_vehicle_type passed.")

    print("Running test_cl_208_3_invalid_span_inputs...")
    test_cl_208_3_invalid_span_inputs()
    print("PASS: test_cl_208_3_invalid_span_inputs passed.")

    total_count = len(TEST_CASES) + 4
    print(f"\n==========================================")
    print(f"ALL {total_count} IRC 6 IMPACT TESTS PASSED SUCCESSFULLY!")
    print(f"==========================================")
    return total_count


if __name__ == "__main__":
    run_all_tests()

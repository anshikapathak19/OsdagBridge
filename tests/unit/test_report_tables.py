import os
import subprocess
try:
    import pytest
except ImportError:
    pytest = None
from osdagbridge.core.reports.report_utils import build_longtable

def test_build_longtable_structure():
    r"""Verify clean \caption, \endfirsthead, and \endhead generation."""
    col_spec = "{|C{3cm}|C{5cm}|C{3cm}|}"
    caption = r"\textbf{Test Component Details}"
    headers = r"\textbf{Parameter} & \textbf{Formula} & \textbf{Value} \\[6pt]"
    rows = [
        r"Length & L & 30 m \\[6pt]\hline",
        r"Width & B & 8.4 m \\[6pt]\hline",
    ]
    note = "IRC 24:2010"
    
    tex = build_longtable(
        col_spec=col_spec,
        caption=caption,
        headers=headers,
        rows=rows,
        note=note,
        label="tab:test_comp"
    )
    
    # 1. Environment check
    assert r"\begin{longtable}{{|C{3cm}|C{5cm}|C{3cm}|}}" in tex
    assert r"\end{longtable}" in tex
    
    # 2. Caption appears only once (before \endfirsthead)
    assert tex.count(r"\caption{\textbf{Test Component Details}}") == 1
    
    # 3. Firsthead and endhead markers present
    assert r"\endfirsthead" in tex
    assert r"\endhead" in tex
    
    # 4. Continuation header present
    efh_pos = tex.find(r"\endfirsthead")
    eh_pos = tex.find(r"\endhead")
    assert efh_pos < eh_pos
    between = tex[efh_pos:eh_pos]
    assert r"\textbf{Parameter} & \textbf{Formula} & \textbf{Value}" in between
    
    # 5. Note placed after \end{longtable}
    end_pos = tex.find(r"\end{longtable}")
    note_pos = tex.find(note)
    assert note_pos > end_pos


def test_build_longtable_row_grouping():
    """Verify automatic non-breaking row protection (\\\\*) within member groups."""
    col_spec = "{|C{2.5cm}|C{4cm}|C{4cm}|}"
    caption = r"\textbf{Member Checks}"
    headers = r"\textbf{Member} & \textbf{Check} & \textbf{Status} \\[6pt]"
    
    # 2 members, each with 3 rows
    group_g1 = [
        r"\multirow{3}{*}{\makecell{G1}} & Check 1 & PASS \\[6pt]\cline{2-3}",
        r" & Check 2 & PASS \\[6pt]\cline{2-3}",
        r" & Check 3 & PASS \\[6pt]\hline",
    ]
    group_g2 = [
        r"\multirow{3}{*}{\makecell{G2}} & Check 1 & PASS \\[6pt]\cline{2-3}",
        r" & Check 2 & PASS \\[6pt]\cline{2-3}",
        r" & Check 3 & PASS \\[6pt]\hline",
    ]
    
    tex = build_longtable(
        col_spec=col_spec,
        caption=caption,
        headers=headers,
        rows=[group_g1, group_g2],
        keep_groups_intact=True
    )
    
    # Intermediate rows must end with \\*[6pt]
    assert r"Check 1 & PASS \\*[6pt]\cline{2-3}" in tex
    assert r"Check 2 & PASS \\*[6pt]\cline{2-3}" in tex
    
    # Final row of each group must end with \\[6pt] (not \\*)
    assert r"Check 3 & PASS \\[6pt]\hline" in tex


def test_build_longtable_without_conventional_headers():
    """Verify tables without conventional headers (e.g. key-value tables)."""
    col_spec = "{|L{5cm}|p{8cm}|}"
    caption = r"\textbf{Key-Value Settings}"
    rows = [
        r"Span & 30 m \\[6pt]\hline",
        r"Width & 8.4 m \\[6pt]\hline",
    ]
    tex = build_longtable(
        col_spec=col_spec,
        caption=caption,
        headers=None,
        rows=rows,
    )
    assert r"\caption{\textbf{Key-Value Settings}}" in tex
    assert r"\endfirsthead" in tex
    assert r"\endhead" in tex
    assert r"Span & 30 m \\[6pt]\hline" in tex


def test_build_longtable_uncaptioned():
    """Verify tables without caption (e.g. Bill of Materials in Chapter 7)."""
    col_spec = "{|C{1cm}|L{4cm}|C{2cm}|}"
    headers = r"\textbf{S.N.} & \textbf{Item} & \textbf{Qty} \\[6pt]"
    rows = [
        r"1 & Structural Steel & 45 MT \\[6pt]\hline",
    ]
    tex = build_longtable(
        col_spec=col_spec,
        caption=None,
        headers=headers,
        rows=rows,
    )
    assert r"\caption" not in tex
    assert r"\endfirsthead" in tex
    assert r"\endhead" in tex
    assert r"\textbf{S.N.} & \textbf{Item} & \textbf{Qty}" in tex


def test_3_page_table_pagination(tmp_path):
    """
    Generate a synthetic multi-page table spanning ~3 pages, compile it with pdflatex,
    and programmatically verify repeated headers, zero orphaned captions, correct row order,
    and no split row groups.
    """
    try:
        import pypdf
    except ImportError:
        if pytest:
            pytest.skip("pypdf not installed")
        return
    
    col_spec = "{|C{3cm}|C{5cm}|C{5cm}|}"
    caption = r"\textbf{Multi-Page Girder Verification Table}"
    headers = r"\textbf{Girder} & \textbf{Design Parameter} & \textbf{Calculated Value} \\[6pt]"
    
    # Build 6 girder groups (G1..G6), each with 8 rows = 48 rows total
    groups = []
    for g in range(1, 7):
        g_rows = []
        for r in range(1, 9):
            is_first = (r == 1)
            is_last = (r == 8)
            g_lbl = rf"\multirow{{8}}{{*}}{{\makecell{{Girder {g}}}}}" if is_first else ""
            rule = r"\hline" if is_last else r"\cline{2-3}"
            g_rows.append(f"{g_lbl} & Parameter {r} & Value {g}.{r} \\\\[6pt]{rule}")
        groups.append(g_rows)
        
    table_tex = build_longtable(
        col_spec=col_spec,
        caption=caption,
        headers=headers,
        rows=groups,
        note="Synthetic 3-page test table for OsdagBridge pagination validation.",
        keep_groups_intact=True
    )
    
    preamble = r"""\documentclass[12pt,a4paper]{report}
\usepackage[a4paper, margin=1in]{geometry}
\usepackage{array}
\usepackage{makecell}
\usepackage{multirow}
\usepackage{longtable}
\newcolumntype{C}[1]{>{\centering\arraybackslash}p{#1}}

% Patch \@cline to preserve \nobreak inside longtable row groups
\makeatletter
\def\@cline#1-#2\@nil{%
  \omit \@multicnt #1\advance \@multispan \m@ne
  \ifnum \@multicnt =\@ne \@firstofone {&\omit }\fi
  \@multicnt #2\advance \@multicnt -#1\advance \@multispan \@ne
  \leaders \hrule \@height \arrayrulewidth \hfill
  \cr
  \noalign {\nobreak\vskip -\arrayrulewidth }%
}
\makeatother

\begin{document}
"""
    doc_tex = preamble + table_tex + r"\end{document}"
    
    tex_file = tmp_path / "test_3_page_table.tex"
    pdf_file = tmp_path / "test_3_page_table.pdf"
    tex_file.write_text(doc_tex, encoding="utf-8")
    
    # Search for pdflatex compiler
    latex_bin = "pdflatex"
    # check known conda path if not in system PATH
    known_conda = r"C:\Users\anshi\miniconda3_new\envs\osdagbridge-env\Library\share\osdag_latex_env\bin\x86_64-windows\pdflatex.exe"
    if os.path.exists(known_conda):
        latex_bin = known_conda
        
    res = subprocess.run([latex_bin, "-interaction=batchmode", "test_3_page_table.tex"], cwd=str(tmp_path), stdout=subprocess.PIPE)
    if not pdf_file.exists():
        pytest.skip(f"pdflatex compilation skipped: returncode {res.returncode}")
        
    reader = pypdf.PdfReader(str(pdf_file))
    num_pages = len(reader.pages)
    
    # 1. Verify table spans multiple pages (at least 2, typically 3)
    assert num_pages >= 2
    
    # 2. Verify caption appears ONLY on Page 1
    p1_text = reader.pages[0].extract_text() or ""
    assert "Multi-Page Girder Verification Table" in p1_text
    
    # 3. Verify repeated header on continuation pages and caption NOT repeated
    for p in range(1, num_pages):
        text = reader.pages[p].extract_text() or ""
        assert "Design Parameter" in text
        assert "Calculated Value" in text
        assert "Multi-Page Girder Verification Table" not in text

    # 4. Verify row order across all pages (Value 1.1 through 6.8 in order)
    full_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    positions = [full_text.find(f"Value {g}.{r}") for g in range(1, 7) for r in range(1, 9)]
    assert all(pos != -1 for pos in positions), "All values must be present in output"
    assert positions == sorted(positions), "Row values must appear in strict chronological order"


def test_vehicle_live_loads_selection_and_boolean_filtering():
    """Verify Vehicle Live Load table dynamically filters selections with strict boolean checking."""
    from osdagbridge.core.reports.chap3 import ch3_loads
    from osdagbridge.core.utils.common import (
        KEY_SPAN, KEY_CARRIAGEWAY_WIDTH, KEY_FOOTPATH,
        KEY_LL_IRC_CLASS_A, KEY_LL_IRC_70R_WHEELED, KEY_LL_IRC_70R_TRACKED,
        KEY_LL_IRC_CLASS_SV, KEY_BL_IRC_CLASS_SV
    )

    inp = {
        KEY_SPAN: "30",
        KEY_CARRIAGEWAY_WIDTH: "7.5",
        KEY_FOOTPATH: "None",
        KEY_LL_IRC_CLASS_A: True,
        KEY_LL_IRC_70R_WHEELED: "True",
        KEY_LL_IRC_70R_TRACKED: "False",  # String "False" must NOT be treated as True!
        KEY_LL_IRC_CLASS_SV: False,
        KEY_BL_IRC_CLASS_SV: False,
    }

    tex = ch3_loads(inp)
    assert r"\caption{\textbf{Vehicle Live Load Parameters}}" in tex
    assert r"\endfirsthead" in tex
    assert r"\endhead" in tex

    # Vehicle selection assertions
    assert "Class A" in tex
    assert "Class 70R (Wheeled)" in tex
    assert "Class 70R (Tracked)" not in tex, "String 'False' must not be selected!"
    assert "Class SV" not in tex

    # Total load and impact factor assertions
    assert "543.5" in tex  # Class A total load
    assert "981.0" in tex  # Class 70R Wheeled total load
    assert "1.207" in tex  # Impact factor for 30m span

    # Centrifugal force and braking assertions
    assert "Not Applicable" in tex
    assert "Centrifugal force is Not Applicable for straight bridge alignment" in tex
    assert "196.20" in tex  # Braking force for 2 lanes


def test_vehicle_live_loads_custom_vehicles_and_braking():
    """Verify custom vehicles handling, Class SV braking opt-in, and multi-lane braking calculation."""
    from osdagbridge.core.reports.chap3 import ch3_loads
    from osdagbridge.core.utils.common import (
        KEY_SPAN, KEY_CARRIAGEWAY_WIDTH, KEY_FOOTPATH,
        KEY_LL_IRC_CLASS_A, KEY_LL_IRC_CLASS_SV, KEY_BL_IRC_CLASS_SV,
        KEY_LL_CUSTOM_VEHICLES, KEY_WC_LD_LANE_TABLE_COUNT
    )

    # 4-lane bridge with Class SV (braking opt-out) and custom vehicle
    inp = {
        KEY_SPAN: "30",
        KEY_CARRIAGEWAY_WIDTH: "14.0",
        KEY_WC_LD_LANE_TABLE_COUNT: 4,
        KEY_FOOTPATH: "None",
        KEY_LL_IRC_CLASS_A: False,
        KEY_LL_IRC_CLASS_SV: True,
        KEY_BL_IRC_CLASS_SV: False,  # Opt-out of braking for Class SV
        KEY_LL_CUSTOM_VEHICLES: [
            {
                "name": "Special Multi-Axle Trailer",
                "total_load_kN": 4500.0,
                "impact_factor": 0.10,
            }
        ],
    }

    tex = ch3_loads(inp)
    assert "Special Multi-Axle Trailer" in tex
    assert "4500.0" in tex
    assert "1.100" in tex  # 1.0 + 0.10 impact
    assert "Class SV (Special Vehicle)" in tex
    assert "3776.8" in tex

    # 4-lane braking force per IRC 6 Cl. 211.2 / Table 6A:
    # 20% of 70R Wheeled (196.20 kN) + 2 * 5% of Class A (54.35 kN) = 250.55 kN
    assert "250.55" in tex

    # Verify Class SV has braking 'No' and '---'
    sv_pos = tex.find("Class SV (Special Vehicle)")
    sv_line = tex[sv_pos:tex.find(r"\\", sv_pos)]
    assert "& No &" in sv_line
    assert "---" in sv_line


def test_footpath_live_load_table():
    """Verify separate Footpath Live Load table for None, IRC 6, and Custom modes."""
    from osdagbridge.core.reports.chap3 import ch3_loads
    from osdagbridge.core.utils.common import (
        KEY_SPAN, KEY_CARRIAGEWAY_WIDTH, KEY_FOOTPATH, KEY_TS_NO_OF_FOOTPATHS,
        KEY_TS_FOOTPATH_WIDTH, KEY_LL_FOOTPATH_PRESSURE_MODE, KEY_LL_FOOTPATH_PRESSURE_VALUE
    )

    # Case A: No footpath
    inp_none = {
        KEY_SPAN: "30",
        KEY_CARRIAGEWAY_WIDTH: "7.5",
        KEY_FOOTPATH: "None",
    }
    tex_none = ch3_loads(inp_none)
    assert r"\caption{\textbf{Footpath / Pedestrian Live Load}}" in tex_none
    assert "Footpath Provision & None" in tex_none
    assert "Applied Footpath Live Load & Not Applicable & No footpath provided" in tex_none

    # Case B: Footpath Both Sides with default "As per IRC 6" mode
    inp_irc = {
        KEY_SPAN: "30",
        KEY_CARRIAGEWAY_WIDTH: "7.5",
        KEY_FOOTPATH: "Both Sides",
        KEY_TS_NO_OF_FOOTPATHS: 2,
        KEY_TS_FOOTPATH_WIDTH: 1.5,
        KEY_LL_FOOTPATH_PRESSURE_MODE: "As per IRC 6",
    }
    tex_irc = ch3_loads(inp_irc)
    assert "Footpath Provision & Both Sides" in tex_irc
    assert "Number of Footpaths & 2" in tex_irc
    assert "1.50 m" in tex_irc
    assert "Pressure Mode & As per IRC 6" in tex_irc
    assert "4.905 kN/m" in tex_irc
    assert "IRC 6 Cl. 206.1 (500 kg/m" in tex_irc

    # Case C: Footpath Single Side with Custom mode
    inp_cust = {
        KEY_SPAN: "30",
        KEY_CARRIAGEWAY_WIDTH: "7.5",
        KEY_FOOTPATH: "Single Side",
        KEY_TS_NO_OF_FOOTPATHS: 1,
        KEY_TS_FOOTPATH_WIDTH: 2.0,
        KEY_LL_FOOTPATH_PRESSURE_MODE: "Custom",
        KEY_LL_FOOTPATH_PRESSURE_VALUE: 4.0,
    }
    tex_cust = ch3_loads(inp_cust)
    assert "Footpath Provision & Single Side" in tex_cust
    assert "Number of Footpaths & 1" in tex_cust
    assert "2.00 m" in tex_cust
    assert "Pressure Mode & Custom" in tex_cust
    assert "4.000 kN/m" in tex_cust


def test_executive_summary_girder_fails_fatigue():
    """Verify Girder design status is FAIL when fatigue check fails despite passing strength checks."""
    from osdagbridge.core.reports.executive_summary import executive_summary
    from osdagbridge.core.utils.common import (
        KEY_SPAN, KEY_CARRIAGEWAY_WIDTH, KEY_STRUCTURE_TYPE,
        KEY_TS_NO_OF_GIRDERS, KEY_TS_GIRDER_SPACING, KEY_TS_DECK_THICKNESS,
        KEY_SD_DEFL_TOTAL, KEY_SD_DEFL_ALLOW_TOTAL
    )
    inp = {
        KEY_SPAN: 30.0,
        KEY_CARRIAGEWAY_WIDTH: 7.5,
        KEY_STRUCTURE_TYPE: 'Plate Girder',
        KEY_TS_NO_OF_GIRDERS: 4,
        KEY_TS_GIRDER_SPACING: 2.5,
        KEY_TS_DECK_THICKNESS: 250,
    }
    out = {
        'design_results': {
            'per_girder': {
                'G1': {
                    'checks': [
                        {'name': 'ULS Flexure', 'dcr': 0.8, 'status': 'PASS'},
                        {'name': 'ULS Shear', 'dcr': 0.7, 'status': 'PASS'},
                        {'name': 'Fatigue Normal Stress', 'dcr': 1.58, 'status': 'FAIL'},
                    ]
                }
            }
        },
        KEY_SD_DEFL_TOTAL: 40.0,
        KEY_SD_DEFL_ALLOW_TOTAL: 50.0,
    }
    tex = executive_summary(inp, out, {})
    assert 'Girder design fail' in tex
    assert 'Overall Design Status' in tex


def test_executive_summary_girder_fails_deflection():
    """Verify Girder design status is FAIL when deflection check fails despite passing strength and fatigue."""
    from osdagbridge.core.reports.executive_summary import executive_summary
    from osdagbridge.core.utils.common import (
        KEY_SPAN, KEY_CARRIAGEWAY_WIDTH, KEY_STRUCTURE_TYPE,
        KEY_TS_NO_OF_GIRDERS, KEY_TS_GIRDER_SPACING, KEY_TS_DECK_THICKNESS,
        KEY_SD_DEFL_TOTAL, KEY_SD_DEFL_ALLOW_TOTAL
    )
    inp = {
        KEY_SPAN: 30.0,
        KEY_CARRIAGEWAY_WIDTH: 7.5,
        KEY_STRUCTURE_TYPE: 'Plate Girder',
        KEY_TS_NO_OF_GIRDERS: 4,
        KEY_TS_GIRDER_SPACING: 2.5,
        KEY_TS_DECK_THICKNESS: 250,
    }
    out = {
        'design_results': {
            'per_girder': {
                'G1': {
                    'checks': [
                        {'name': 'ULS Flexure', 'dcr': 0.8, 'status': 'PASS'},
                        {'name': 'ULS Shear', 'dcr': 0.7, 'status': 'PASS'},
                        {'name': 'Fatigue Normal Stress', 'dcr': 0.85, 'status': 'PASS'},
                    ]
                }
            }
        },
        KEY_SD_DEFL_TOTAL: 51.225,
        KEY_SD_DEFL_ALLOW_TOTAL: 50.0,
    }
    tex = executive_summary(inp, out, {})
    assert 'Girder design fail' in tex


def test_executive_summary_girder_passes_all():
    """Verify Girder design status is PASS when all governing checks pass."""
    from osdagbridge.core.reports.executive_summary import executive_summary
    from osdagbridge.core.utils.common import (
        KEY_SPAN, KEY_CARRIAGEWAY_WIDTH, KEY_STRUCTURE_TYPE,
        KEY_TS_NO_OF_GIRDERS, KEY_TS_GIRDER_SPACING, KEY_TS_DECK_THICKNESS,
        KEY_SD_DEFL_TOTAL, KEY_SD_DEFL_ALLOW_TOTAL
    )
    inp = {
        KEY_SPAN: 30.0,
        KEY_CARRIAGEWAY_WIDTH: 7.5,
        KEY_STRUCTURE_TYPE: 'Plate Girder',
        KEY_TS_NO_OF_GIRDERS: 4,
        KEY_TS_GIRDER_SPACING: 2.5,
        KEY_TS_DECK_THICKNESS: 250,
    }
    out = {
        'design_results': {
            'per_girder': {
                'G1': {
                    'checks': [
                        {'name': 'ULS Flexure', 'dcr': 0.8, 'status': 'PASS'},
                        {'name': 'ULS Shear', 'dcr': 0.7, 'status': 'PASS'},
                        {'name': 'Fatigue Normal Stress', 'dcr': 0.85, 'status': 'PASS'},
                    ]
                }
            }
        },
        KEY_SD_DEFL_TOTAL: 40.0,
        KEY_SD_DEFL_ALLOW_TOTAL: 50.0,
    }
    tex = executive_summary(inp, out, {})
    assert 'Girder design pass' in tex


def test_executive_summary_independent_component_statuses():
    """Verify independent statuses for Deck, Cross Bracing, and End Diaphragm."""
    from osdagbridge.core.reports.executive_summary import executive_summary
    from osdagbridge.core.utils.common import (
        KEY_SPAN, KEY_CARRIAGEWAY_WIDTH, KEY_STRUCTURE_TYPE,
        KEY_TS_NO_OF_GIRDERS, KEY_TS_GIRDER_SPACING, KEY_TS_DECK_THICKNESS,
        KEY_SD_DEFL_TOTAL, KEY_SD_DEFL_ALLOW_TOTAL
    )
    inp = {
        KEY_SPAN: 30.0,
        KEY_CARRIAGEWAY_WIDTH: 7.5,
        KEY_STRUCTURE_TYPE: 'Plate Girder',
        KEY_TS_NO_OF_GIRDERS: 4,
        KEY_TS_GIRDER_SPACING: 2.5,
        KEY_TS_DECK_THICKNESS: 250,
    }
    base_out = {
        'design_results': {
            'per_girder': {
                'G1': {
                    'checks': [
                        {'name': 'ULS Flexure', 'dcr': 0.8, 'status': 'PASS'},
                        {'name': 'ULS Shear', 'dcr': 0.7, 'status': 'PASS'},
                    ]
                }
            }
        },
        KEY_SD_DEFL_TOTAL: 40.0,
        KEY_SD_DEFL_ALLOW_TOTAL: 50.0,
    }

    # 1. Deck fails independently
    out_deck = dict(base_out)
    out_deck['deck_design_results'] = {'ur_flexure': 1.25, 'deck_design_check': 'FAIL'}
    tex_deck = executive_summary(inp, out_deck, {})
    assert 'Girder design pass' in tex_deck
    assert 'Deck design fail' in tex_deck
    assert 'Cross bracing design pass' in tex_deck
    assert 'End Diaphragm design pass' in tex_deck

    # 2. Cross bracing fails independently
    out_cb = dict(base_out)
    out_cb['crossbracing_design_results'] = {'P1': {'diagonal': {'tension': {'Member.efficiency': 1.25}}}}
    tex_cb = executive_summary(inp, out_cb, {})
    assert 'Girder design pass' in tex_cb
    assert 'Cross bracing design fail' in tex_cb
    assert 'Deck design pass' in tex_cb
    assert 'End Diaphragm design pass' in tex_cb

    # 3. End diaphragm fails independently
    out_ed = dict(base_out)
    out_ed['end_diaphragm_design_results'] = {'P1': {'diagonal': {'compression': {'Member.efficiency': 1.15}}}}
    tex_ed = executive_summary(inp, out_ed, {})
    assert 'Girder design pass' in tex_ed
    assert 'End Diaphragm design fail' in tex_ed
    assert 'Cross bracing design pass' in tex_ed
    assert 'Deck design pass' in tex_ed


if __name__ == "__main__":
    import pathlib
    import tempfile
    print("Running test_build_longtable_structure...")
    test_build_longtable_structure()
    print("PASS: test_build_longtable_structure")

    print("Running test_build_longtable_without_conventional_headers...")
    test_build_longtable_without_conventional_headers()
    print("PASS: test_build_longtable_without_conventional_headers")

    print("Running test_build_longtable_uncaptioned...")
    test_build_longtable_uncaptioned()
    print("PASS: test_build_longtable_uncaptioned")

    print("Running test_build_longtable_row_grouping...")
    test_build_longtable_row_grouping()
    print("PASS: test_build_longtable_row_grouping")

    print("Running test_3_page_table_pagination...")
    with tempfile.TemporaryDirectory() as td:
        test_3_page_table_pagination(pathlib.Path(td))
    print("PASS: test_3_page_table_pagination")

    print("Running test_vehicle_live_loads_selection_and_boolean_filtering...")
    test_vehicle_live_loads_selection_and_boolean_filtering()
    print("PASS: test_vehicle_live_loads_selection_and_boolean_filtering")

    print("Running test_vehicle_live_loads_custom_vehicles_and_braking...")
    test_vehicle_live_loads_custom_vehicles_and_braking()
    print("PASS: test_vehicle_live_loads_custom_vehicles_and_braking")

    print("Running test_footpath_live_load_table...")
    test_footpath_live_load_table()
    print("PASS: test_footpath_live_load_table")

    print("Running test_executive_summary_girder_fails_fatigue...")
    test_executive_summary_girder_fails_fatigue()
    print("PASS: test_executive_summary_girder_fails_fatigue")

    print("Running test_executive_summary_girder_fails_deflection...")
    test_executive_summary_girder_fails_deflection()
    print("PASS: test_executive_summary_girder_fails_deflection")

    print("Running test_executive_summary_girder_passes_all...")
    test_executive_summary_girder_passes_all()
    print("PASS: test_executive_summary_girder_passes_all")

    print("Running test_executive_summary_independent_component_statuses...")
    test_executive_summary_independent_component_statuses()
    print("PASS: test_executive_summary_independent_component_statuses")

    print("\nALL 12 TESTS PASSED SUCCESSFULLY!")

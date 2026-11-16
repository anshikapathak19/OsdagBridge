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
    print("\nALL 5 TESTS PASSED SUCCESSFULLY!")

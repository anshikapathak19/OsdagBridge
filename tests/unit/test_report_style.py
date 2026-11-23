"""
Tests for Centralized Style System (Requirement 6).

Verifies:
  1. report_style constants and generators for page layout, geometry, typography,
     colors, table styles, headers/footers, and figure spacings.
  2. format_status_latex behavior on PASS, FAIL, and custom status strings.
  3. Integration into report modules (report_generator, report_utils, chap*,
     ur_charts, material_charts) confirming centralized values are consumed.
"""

import pytest
from osdagbridge.core.reports import report_style
from osdagbridge.core.reports.report_style import (
    PAGE_PAPER_SIZE,
    PAGE_DOC_CLASS,
    PAGE_FONT_SIZE,
    PAGE_TOP_MARGIN,
    PAGE_BOTTOM_MARGIN,
    PAGE_LEFT_MARGIN,
    PAGE_RIGHT_MARGIN,
    PAGE_HEAD_HEIGHT,
    PAGE_HEAD_SEP,
    PAGE_FOOT_SKIP,
    PAGE_LINE_STRETCH,
    get_geometry_setup,
    COLOR_OSDAG_GREEN_HEX,
    COLOR_OSDAG_GREEN,
    COLOR_PASS_LATEX,
    COLOR_FAIL_LATEX,
    COLOR_INFO_LATEX,
    COLOR_WARNING_LATEX,
    COLOR_ERROR_LATEX,
    get_color_definitions,
    format_status_latex,
    CHART_UR_PASS,
    CHART_UR_FAIL,
    CHART_UR_LIMIT,
    CHART_UR_BAR_EDGE,
    CHART_STEEL_BAR_COLORS,
    CHART_STEEL_EDGE,
    CHART_CONCRETE,
    CHART_REBAR,
    TABCOLSEP_DEFAULT,
    TABCOLSEP_COMPACT,
    TABCOLSEP_TIGHT,
    TABCOLSEP_MINIMAL,
    TABCOLSEP_DENSE,
    ARRAY_STRETCH_DEFAULT,
    ARRAY_STRETCH_ANALYSIS,
    EXTRA_ROW_HEIGHT_DEFAULT,
    ARRAY_RULE_WIDTH_DEFAULT,
    LT_PRE_DEFAULT,
    LT_POST_DEFAULT,
    LT_LEFT_DEFAULT,
    LT_RIGHT_DEFAULT,
    LT_LEFT_FLUSH,
    ROW_BREAK_DEFAULT,
    ROW_BREAK_NOBREAK,
    ROW_BREAK_SPACE,
    get_table_style_setup,
    CAPTION_LABEL_FONT,
    CAPTION_JUSTIFICATION,
    CAPTION_ABOVE_SKIP,
    CAPTION_BELOW_SKIP,
    get_caption_setup,
    CHAPTER_TITLE_FORMAT,
    CHAPTER_TITLE_SPACING_DEFAULT,
    CHAPTER_TITLE_SPACING_REDUCED,
    get_chapter_format,
    TOC_DEPTH,
    HEADER_FOOTER_HEADRULE_HEIGHT,
    HEADER_FOOTER_FOOTRULE_HEIGHT,
    HEADER_FOOTER_FOOTER_LEFT,
    HEADER_FOOTER_FOOTER_RIGHT,
    HEADER_FOOTER_SD_NOTE,
    get_fancypagestyles,
    FIG_WIDTH_DEFAULT,
    FIG_WIDTH_FULL,
    FIG_WIDTH_PREVIEW,
    FIG_WIDTH_CHART,
    FIG_WIDTH_ENVELOPE,
    FIG_WIDTH_MINIPAGE,
    FIG_PLACEHOLDER_WIDTH,
    FIG_VSPACE_TOP,
    FIG_VSPACE_CAPTION,
    FIG_VSPACE_BOTTOM,
    FIG_VSPACE_CHART_TOP,
    FIG_VSPACE_DRAWING_TOP,
)


# =============================================================================
# 1. Page Geometry & Layout Tests
# =============================================================================

def test_page_geometry_constants():
    assert PAGE_PAPER_SIZE == "a4paper"
    assert PAGE_DOC_CLASS == "report"
    assert PAGE_FONT_SIZE == "12pt"
    assert PAGE_TOP_MARGIN == "25mm"
    assert PAGE_BOTTOM_MARGIN == "30mm"
    assert PAGE_LEFT_MARGIN == "25mm"
    assert PAGE_RIGHT_MARGIN == "25mm"
    assert PAGE_HEAD_HEIGHT == "18pt"
    assert PAGE_HEAD_SEP == "14pt"
    assert PAGE_FOOT_SKIP == "38pt"
    assert PAGE_LINE_STRETCH == 1.15


def test_get_geometry_setup():
    geo_str = get_geometry_setup()
    assert r"\usepackage[" in geo_str
    assert "a4paper" in geo_str
    assert "top=25mm" in geo_str
    assert "bottom=30mm" in geo_str
    assert "left=25mm" in geo_str
    assert "right=25mm" in geo_str
    assert "headheight=18pt" in geo_str
    assert "headsep=14pt" in geo_str
    assert "footskip=38pt" in geo_str
    assert "{geometry}" in geo_str


# =============================================================================
# 2. Color Palette & Status Formatting Tests
# =============================================================================

def test_color_constants():
    assert COLOR_OSDAG_GREEN_HEX == "91B014"
    assert COLOR_OSDAG_GREEN == "osdagGreen"
    assert COLOR_PASS_LATEX == "black"
    assert COLOR_FAIL_LATEX == "red"
    assert COLOR_INFO_LATEX == "osdagGreen"
    assert COLOR_WARNING_LATEX == "blue"
    assert COLOR_ERROR_LATEX == "red"


def test_get_color_definitions():
    c_str = get_color_definitions()
    assert r"\definecolor{osdagGreen}{HTML}{91B014}" in c_str


def test_format_status_latex():
    assert format_status_latex("PASS") == r"\textcolor{black}{PASS}"
    assert format_status_latex("FAIL") == r"\textcolor{red}{FAIL}"
    assert format_status_latex("pass") == r"\textcolor{black}{pass}"
    assert format_status_latex("fail") == r"\textcolor{red}{fail}"
    assert format_status_latex("WARN") == "WARN"
    assert format_status_latex("---") == "---"


def test_chart_color_constants():
    assert CHART_UR_PASS == "#2e7d32"
    assert CHART_UR_FAIL == "#d32f2f"
    assert CHART_UR_LIMIT == "#d32f2f"
    assert CHART_UR_BAR_EDGE == "#333333"

    assert len(CHART_STEEL_BAR_COLORS) == 3
    assert CHART_STEEL_EDGE == "#0c2340"
    assert CHART_CONCRETE == "#2e7d32"
    assert CHART_REBAR == "#c65102"


# =============================================================================
# 3. Table Style & Dimensions Tests
# =============================================================================

def test_table_style_constants():
    assert TABCOLSEP_DEFAULT == "6pt"
    assert TABCOLSEP_COMPACT == "4pt"
    assert TABCOLSEP_TIGHT == "3.5pt"
    assert TABCOLSEP_MINIMAL == "3pt"
    assert TABCOLSEP_DENSE == "2.5pt"

    assert ARRAY_STRETCH_DEFAULT == 1.12
    assert ARRAY_STRETCH_ANALYSIS == 1.25
    assert EXTRA_ROW_HEIGHT_DEFAULT == "0.6pt"
    assert ARRAY_RULE_WIDTH_DEFAULT == "0.5pt"

    assert LT_PRE_DEFAULT == "0pt"
    assert LT_POST_DEFAULT == "4pt"
    assert LT_LEFT_DEFAULT == r"\fill"
    assert LT_RIGHT_DEFAULT == r"\fill"
    assert LT_LEFT_FLUSH == "0pt"

    assert ROW_BREAK_DEFAULT == r"\\[6pt]"
    assert ROW_BREAK_NOBREAK == r"\\*[6pt]"
    assert ROW_BREAK_SPACE == "6pt"


def test_get_table_style_setup():
    tbl_str = get_table_style_setup()
    assert r"\setlength{\tabcolsep}{6pt}" in tbl_str
    assert r"\renewcommand{\arraystretch}{1.12}" in tbl_str
    assert r"\setlength{\LTpre}{0pt}" in tbl_str
    assert r"\setlength{\LTpost}{4pt}" in tbl_str
    assert r"\setlength{\LTleft}{\fill}" in tbl_str
    assert r"\setlength{\LTright}{\fill}" in tbl_str
    assert r"\setlength{\arrayrulewidth}{0.5pt}" in tbl_str
    assert r"\setlength{\extrarowheight}{0.6pt}" in tbl_str


# =============================================================================
# 4. Typography, Captions & Chapter Headings Tests
# =============================================================================

def test_caption_setup():
    cap_str = get_caption_setup()
    assert r"\captionsetup{" in cap_str
    assert "labelfont=bf" in cap_str
    assert "justification=raggedright" in cap_str
    assert "singlelinecheck=false" in cap_str
    assert "format=plain" in cap_str

    assert CAPTION_ABOVE_SKIP == "2pt"
    assert CAPTION_BELOW_SKIP == "2pt"


def test_chapter_format():
    fmt_def = get_chapter_format(reduced_top=False)
    assert r"\titleformat{\chapter}[block]{\normalfont\Large\bfseries\centering}{\thechapter}{1em}{}" in fmt_def
    assert r"\titlespacing*{\chapter}{0pt}{0pt}{10pt}" in fmt_def

    fmt_red = get_chapter_format(reduced_top=True)
    assert r"\titleformat{\chapter}[block]{\normalfont\Large\bfseries\centering}{\thechapter}{1em}{}" in fmt_red
    assert r"\titlespacing*{\chapter}{0pt}{-30pt}{10pt}" in fmt_red

    assert TOC_DEPTH == 2


# =============================================================================
# 5. Header and Footer Tests
# =============================================================================

def test_get_fancypagestyles():
    hdr_str = get_fancypagestyles("Test Project", "JOB-101", "2026-11-23", "Rev 0")
    assert r"\fancypagestyle{main}" in hdr_str
    assert r"\fancypagestyle{plain}" in hdr_str
    assert r"\fancypagestyle{firstpage}" in hdr_str
    assert "Test Project $|$ JOB-101" in hdr_str
    assert "2026-11-23 $|$ Rev 0" in hdr_str
    assert HEADER_FOOTER_FOOTER_LEFT in hdr_str
    assert HEADER_FOOTER_FOOTER_RIGHT in hdr_str
    assert HEADER_FOOTER_SD_NOTE in hdr_str
    assert r"\color{osdagGreen}\hrule width\headwidth height 1pt \vspace{2pt}" in hdr_str
    assert r"\color{osdagGreen}\hrule width\headwidth height 1pt \vspace{4pt}" in hdr_str


# =============================================================================
# 6. Figure Style Dimensions Tests
# =============================================================================

def test_figure_style_constants():
    assert FIG_WIDTH_DEFAULT == r"0.9\textwidth"
    assert FIG_WIDTH_FULL == r"\textwidth"
    assert FIG_WIDTH_PREVIEW == r"0.85\textwidth"
    assert FIG_WIDTH_CHART == r"0.78\textwidth"
    assert FIG_WIDTH_ENVELOPE == r"0.75\textwidth"
    assert FIG_WIDTH_MINIPAGE == r"0.31\textwidth"
    assert FIG_PLACEHOLDER_WIDTH == r"0.97\textwidth"

    assert FIG_VSPACE_TOP == r"-0.5em"
    assert FIG_VSPACE_CAPTION == r"0.5em"
    assert FIG_VSPACE_BOTTOM == r"-0.5em"
    assert FIG_VSPACE_CHART_TOP == "2pt"
    assert FIG_VSPACE_DRAWING_TOP == "4pt"


# =============================================================================
# 7. Integration Tests: Report Modules Consume Centralized Style
# =============================================================================

def test_report_generator_preamble_uses_style():
    from osdagbridge.core.reports.report_generator import preamble, toc_section
    pre_tex = preamble("Bridge Proj", "JOB-1", "2026-11-23")
    assert "top=25mm" in pre_tex
    assert r"\definecolor{osdagGreen}{HTML}{91B014}" in pre_tex
    assert r"\setlength{\tabcolsep}{6pt}" in pre_tex
    assert r"\renewcommand{\arraystretch}{1.12}" in pre_tex
    assert r"\setstretch{1.15}" in pre_tex

    toc_tex = toc_section()
    assert r"\titleformat{\chapter}" in toc_tex
    assert r"\titlespacing*{\chapter}{0pt}{0pt}{10pt}" in toc_tex
    assert r"\setcounter{tocdepth}{2}" in toc_tex


def test_report_utils_uses_style():
    from osdagbridge.core.reports.report_utils import _fig_or_placeholder, _fig_embed, build_longtable
    # Placeholder
    ph = _fig_or_placeholder(None, "Test Plan")
    assert r"\parbox{0.97\textwidth}" in ph

    # Embed
    emb = _fig_embed("assets/test.png", "Test Fig")
    assert r"\vspace{-0.5em}" in emb
    assert r"\vspace{0.5em}" in emb
    assert r"width=\textwidth" in emb

    # Longtable row breaks
    lt = build_longtable(
        col_spec="|c|c|",
        caption="Sample Table",
        headers="Col A & Col B",
        rows=[["r1c1 & r1c2 \\\\[6pt]", "r2c1 & r2c2 \\\\[6pt]"]]
    )
    assert r"\\*[6pt]" in lt
    assert r"\\[6pt]" in lt


def test_executive_summary_uses_style():
    from osdagbridge.core.reports.executive_summary import executive_summary
    out = executive_summary({}, {}, {})
    assert r"\titleformat{\chapter}" in out
    assert r"\titlespacing*{\chapter}{0pt}{-30pt}{10pt}" in out


def test_chap_modules_use_style():
    from osdagbridge.core.reports.chap2 import ch2_input_parameters
    from osdagbridge.core.reports.chap3 import ch3_loads
    from osdagbridge.core.reports.chap7 import ch7_quantities

    class DummyMeta:
        project_location = "Mumbai"

    ch2_tex = ch2_input_parameters(DummyMeta(), {})
    assert r"\setlength{\abovecaptionskip}{2pt}" in ch2_tex
    assert r"\setlength{\belowcaptionskip}{2pt}" in ch2_tex

    ch3_tex = ch3_loads({})
    assert r"\setlength{\tabcolsep}{2.5pt}" in ch3_tex

    ch7_tex = ch7_quantities({})
    assert r"\setlength{\tabcolsep}{3.5pt}" in ch7_tex

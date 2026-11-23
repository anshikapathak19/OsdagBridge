"""
OsdagBridge — Centralized Report Styling System (Requirement 6)

Provides a single source of truth for:
  • Page layout, dimensions, and geometry
  • Typography, fonts, headings, and TOC formatting
  • Report color palette (brand, status, log, and chart colors)
  • Table formatting, cell padding, rule widths, and spacing
  • Header and footer layouts and rules
  • Figure dimensions, placeholders, and caption spacings
"""

# =============================================================================
# 1. PAGE LAYOUT & GEOMETRY
# =============================================================================
PAGE_PAPER_SIZE = "a4paper"
PAGE_DOC_CLASS = "report"
PAGE_FONT_SIZE = "12pt"

PAGE_TOP_MARGIN = "25mm"
PAGE_BOTTOM_MARGIN = "30mm"
PAGE_LEFT_MARGIN = "25mm"
PAGE_RIGHT_MARGIN = "25mm"

PAGE_HEAD_HEIGHT = "18pt"
PAGE_HEAD_SEP = "14pt"
PAGE_FOOT_SKIP = "38pt"

PAGE_LINE_STRETCH = 1.15


def get_geometry_setup() -> str:
    """Generate LaTeX geometry package setup block."""
    return rf"""\usepackage[
  {PAGE_PAPER_SIZE},
  top={PAGE_TOP_MARGIN},
  bottom={PAGE_BOTTOM_MARGIN},
  left={PAGE_LEFT_MARGIN},
  right={PAGE_RIGHT_MARGIN},
  headheight={PAGE_HEAD_HEIGHT},
  headsep={PAGE_HEAD_SEP},
  footskip={PAGE_FOOT_SKIP}
]{{geometry}}"""


# =============================================================================
# 2. COLOR PALETTE
# =============================================================================
# Osdag Brand Colors
COLOR_OSDAG_GREEN_HEX = "91B014"
COLOR_OSDAG_GREEN = "osdagGreen"

# LaTeX Text & Status Colors
COLOR_PASS_LATEX = "black"
COLOR_FAIL_LATEX = "red"
COLOR_INFO_LATEX = "osdagGreen"
COLOR_WARNING_LATEX = "blue"
COLOR_ERROR_LATEX = "red"

# Matplotlib / Chart Colors: Utilisation Ratio (UR) Charts
CHART_UR_PASS = "#2e7d32"
CHART_UR_FAIL = "#d32f2f"
CHART_UR_LIMIT = "#d32f2f"
CHART_UR_BAR_EDGE = "#333333"
CHART_UR_TITLE = "#212529"
CHART_UR_SUBTITLE = "#495057"
CHART_UR_BOX_BG = "#f8f9fa"
CHART_UR_BOX_EDGE = "#ced4da"
CHART_UR_SPINE = "#666666"
CHART_UR_ANNOT_PASS = "#1b5e20"
CHART_UR_ANNOT_FAIL = "#b71c1c"
CHART_UR_LEGEND_BG = "#ffffff"
CHART_UR_LEGEND_EDGE = "#cccccc"

# Matplotlib / Chart Colors: Material Quantity Charts
CHART_STEEL_GIRDER = "#1f4e78"
CHART_STEEL_CB = "#2e75b6"
CHART_STEEL_ED = "#5b9bd5"
CHART_STEEL_EDGE = "#0c2340"
CHART_STEEL_BAR_COLORS = [CHART_STEEL_GIRDER, CHART_STEEL_CB, CHART_STEEL_ED]

CHART_CONCRETE = "#2e7d32"
CHART_CONCRETE_EDGE = "#1b5e20"
CHART_CONCRETE_BADGE_BG = "#f1f8e9"

CHART_REBAR = "#c65102"
CHART_REBAR_EDGE = "#8c3b00"
CHART_REBAR_BADGE_BG = "#fff3e0"

CHART_GRID_COLOR = "#c0c0c0"
CHART_SPINE_COLOR = "#666666"
CHART_TEXT_MUTED = "#555555"
CHART_SUMMARY_BG = "#f8f9fa"
CHART_SUMMARY_EDGE = "#b0bec5"


def get_color_definitions() -> str:
    """Generate LaTeX color definitions."""
    return rf"\definecolor{{{COLOR_OSDAG_GREEN}}}{{HTML}}{{{COLOR_OSDAG_GREEN_HEX}}}"


def format_status_latex(status: str) -> str:
    """
    Format a PASS/FAIL check status string with standard LaTeX color formatting.
    PASS is rendered in black; FAIL is rendered in red.
    """
    s = str(status).strip()
    upper = s.upper()
    if "FAIL" in upper:
        return rf"\textcolor{{{COLOR_FAIL_LATEX}}}{{{s}}}"
    if "PASS" in upper:
        return rf"\textcolor{{{COLOR_PASS_LATEX}}}{{{s}}}"
    return s


# =============================================================================
# 3. TABLE STYLES & GEOMETRY
# =============================================================================
# Cell padding (tabcolsep)
TABCOLSEP_DEFAULT = "6pt"
TABCOLSEP_COMPACT = "4pt"     # Cross-bracing / End-diaphragm in chap5
TABCOLSEP_TIGHT = "3.5pt"     # BOM in chap7, Code tables in chap8
TABCOLSEP_MINIMAL = "3pt"     # Demand summary in chap4
TABCOLSEP_DENSE = "2.5pt"     # Live load vehicle tables in chap3

# Row spacing & heights
ARRAY_STRETCH_DEFAULT = 1.12
ARRAY_STRETCH_ANALYSIS = 1.25 # Demand summary in chap4
EXTRA_ROW_HEIGHT_DEFAULT = "0.6pt"
ARRAY_RULE_WIDTH_DEFAULT = "0.5pt"

# Longtable pre/post spacing
LT_PRE_DEFAULT = "0pt"
LT_POST_DEFAULT = "4pt"

# Longtable alignment
LT_LEFT_DEFAULT = r"\fill"
LT_RIGHT_DEFAULT = r"\fill"
LT_LEFT_FLUSH = "0pt"

# Row breaks & spacing
ROW_BREAK_DEFAULT = r"\\[6pt]"
ROW_BREAK_NOBREAK = r"\\*[6pt]"
ROW_BREAK_SPACE = "6pt"

# Column definitions
COL_TYPE_L = r">{\raggedright\arraybackslash}p{#1}"
COL_TYPE_C = r">{\centering\arraybackslash}p{#1}"
COL_TYPE_R = r">{\raggedleft\arraybackslash}p{#1}"


def get_table_style_setup() -> str:
    """Generate LaTeX table configuration block for preamble."""
    return rf"""% Table layout and spacing: consistent padding, row height, and longtable pre/post skips
\setlength{{\tabcolsep}}{{{TABCOLSEP_DEFAULT}}}
\renewcommand{{\arraystretch}}{{{ARRAY_STRETCH_DEFAULT}}}
\setlength{{\LTpre}}{{{LT_PRE_DEFAULT}}}
\setlength{{\LTpost}}{{{LT_POST_DEFAULT}}}
\setlength{{\LTleft}}{{{LT_LEFT_DEFAULT}}}
\setlength{{\LTright}}{{{LT_RIGHT_DEFAULT}}}
% Table rules (outline thickness) and small extra row height for clarity
\setlength{{\arrayrulewidth}}{{{ARRAY_RULE_WIDTH_DEFAULT}}}
\setlength{{\extrarowheight}}{{{EXTRA_ROW_HEIGHT_DEFAULT}}}"""


# =============================================================================
# 4. TYPOGRAPHY, CAPTIONS & HEADINGS
# =============================================================================
# Captions
CAPTION_LABEL_FONT = "bf"
CAPTION_JUSTIFICATION = "raggedright"
CAPTION_SINGLELINE_CHECK = "false"
CAPTION_FORMAT = "plain"

CAPTION_ABOVE_SKIP = "2pt"
CAPTION_BELOW_SKIP = "2pt"


def get_caption_setup() -> str:
    """Generate LaTeX caption package configuration block."""
    return rf"""\captionsetup{{
    labelfont={CAPTION_LABEL_FONT},
    justification={CAPTION_JUSTIFICATION},
    singlelinecheck={CAPTION_SINGLELINE_CHECK},
    format={CAPTION_FORMAT}
}}"""


# Chapter formatting
CHAPTER_TITLE_FORMAT = r"\titleformat{\chapter}[block]{\normalfont\Large\bfseries\centering}{\thechapter}{1em}{}"
CHAPTER_TITLE_SPACING_DEFAULT = r"\titlespacing*{\chapter}{0pt}{0pt}{10pt}"
CHAPTER_TITLE_SPACING_REDUCED = r"\titlespacing*{\chapter}{0pt}{-30pt}{10pt}"

TOC_DEPTH = 2


def get_chapter_format(reduced_top: bool = False) -> str:
    """Return LaTeX titleformat and titlespacing commands for chapters."""
    spacing = CHAPTER_TITLE_SPACING_REDUCED if reduced_top else CHAPTER_TITLE_SPACING_DEFAULT
    return f"{CHAPTER_TITLE_FORMAT}\n{spacing}"


# =============================================================================
# 5. HEADER & FOOTER
# =============================================================================
HEADER_FOOTER_HEADRULE_HEIGHT = "1pt"
HEADER_FOOTER_HEADRULE_VSPACE = "2pt"
HEADER_FOOTER_FOOTRULE_HEIGHT = "1pt"
HEADER_FOOTER_FOOTRULE_VSPACE = "4pt"

HEADER_FOOTER_FOOTER_LEFT = r"Osdag $|$ FOSSEE $|$ Indian Institute of Technology Bombay"
HEADER_FOOTER_FOOTER_RIGHT = r"Page \thepage\ of \pageref{LastPage}"
HEADER_FOOTER_SD_NOTE = r"\textcolor{black}{\footnotesize\textit{* Software default value}}"


def get_fancypagestyles(project_name: str, job_number: str, report_date: str, report_version: str) -> str:
    """Generate LaTeX fancypagestyle definitions."""
    return rf"""\fancypagestyle{{main}}{{
  \fancyhf{{}}
  \fancyhead[L]{{{project_name} $|$ {job_number}}}
  \fancyhead[R]{{{report_date} $|$ {report_version}}}
  \fancyfoot[L]{{{HEADER_FOOTER_FOOTER_LEFT}}}
  \fancyfoot[R]{{{HEADER_FOOTER_FOOTER_RIGHT}}}
  \renewcommand{{\headrule}}{{\color{{{COLOR_OSDAG_GREEN}}}\hrule width\headwidth height {HEADER_FOOTER_HEADRULE_HEIGHT} \vspace{{{HEADER_FOOTER_HEADRULE_VSPACE}}}}}
  \renewcommand{{\footrule}}{{%
    \ifbool{{hasSDonPage}}{{%
      \hbox to \headwidth{{{HEADER_FOOTER_SD_NOTE}\hfil}}%
      \vspace{{3pt}}%
    }}{{}}%
    \color{{{COLOR_OSDAG_GREEN}}}\hrule width\headwidth height {HEADER_FOOTER_FOOTRULE_HEIGHT} \vspace{{{HEADER_FOOTER_FOOTRULE_VSPACE}}}%
  }}
}}
\fancypagestyle{{plain}}{{
  \fancyhf{{}}
  \fancyhead[L]{{{project_name} $|$ {job_number}}}
  \fancyhead[R]{{{report_date} $|$ {report_version}}}
  \fancyfoot[L]{{{HEADER_FOOTER_FOOTER_LEFT}}}
  \fancyfoot[R]{{{HEADER_FOOTER_FOOTER_RIGHT}}}
  \renewcommand{{\headrule}}{{\color{{{COLOR_OSDAG_GREEN}}}\hrule width\headwidth height {HEADER_FOOTER_HEADRULE_HEIGHT} \vspace{{{HEADER_FOOTER_HEADRULE_VSPACE}}}}}
  \renewcommand{{\footrule}}{{%
    \ifbool{{hasSDonPage}}{{%
      \hbox to \headwidth{{{HEADER_FOOTER_SD_NOTE}\hfil}}%
      \vspace{{3pt}}%
    }}{{}}%
    \color{{{COLOR_OSDAG_GREEN}}}\hrule width\headwidth height {HEADER_FOOTER_FOOTRULE_HEIGHT} \vspace{{{HEADER_FOOTER_FOOTRULE_VSPACE}}}%
  }}
}}
\fancypagestyle{{firstpage}}{{
  \fancyhf{{}}
  \renewcommand{{\headrulewidth}}{{0pt}}
  \fancyfoot[L]{{{HEADER_FOOTER_FOOTER_LEFT}}}
  \fancyfoot[R]{{{HEADER_FOOTER_FOOTER_RIGHT}}}
  \renewcommand{{\footrule}}{{\color{{{COLOR_OSDAG_GREEN}}}\hrule width\headwidth height {HEADER_FOOTER_FOOTRULE_HEIGHT} \vspace{{{HEADER_FOOTER_FOOTRULE_VSPACE}}}}}
}}"""


# =============================================================================
# 6. FIGURE & CAPTION SPACING
# =============================================================================
FIG_WIDTH_DEFAULT = r"0.9\textwidth"
FIG_WIDTH_FULL = r"\textwidth"
FIG_WIDTH_PREVIEW = r"0.85\textwidth"
FIG_WIDTH_CHART = r"0.78\textwidth"
FIG_WIDTH_ENVELOPE = r"0.75\textwidth"
FIG_WIDTH_MINIPAGE = r"0.31\textwidth"
FIG_PLACEHOLDER_WIDTH = r"0.97\textwidth"

FIG_VSPACE_TOP = r"-0.5em"
FIG_VSPACE_CAPTION = r"0.5em"
FIG_VSPACE_BOTTOM = r"-0.5em"
FIG_VSPACE_CHART_TOP = r"2pt"
FIG_VSPACE_DRAWING_TOP = r"4pt"

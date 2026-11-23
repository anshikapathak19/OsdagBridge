from osdagbridge.core.utils.common import (
    KEY_MP_GD_MEMBER_ID,
    KEY_MP_GD_SELECT_GIRDER,
    KEY_MP_GIRDER_DEPTH,
    KEY_TS_NO_OF_GIRDERS
)
from osdagbridge.core.reports.report_style import (
    FIG_WIDTH_DEFAULT,
    FIG_WIDTH_FULL,
    FIG_PLACEHOLDER_WIDTH,
    FIG_VSPACE_TOP,
    FIG_VSPACE_CAPTION,
    FIG_VSPACE_BOTTOM,
    ROW_BREAK_DEFAULT,
    ROW_BREAK_NOBREAK,
    ROW_BREAK_SPACE,
)


def _tex(value):
    """Escape a Python value for safe LaTeX embedding."""
    s = str(value) if value is not None else ''
    if not s:
        return r''
    # Normalise non-ASCII glyphs from section designations (e.g. "∠ 100 ⅹ 100ⅹ 10")
    # that pdflatex cannot render.
    for uni, ascii_ in [('∠', 'L'), ('ⅹ', 'x'), ('×', 'x')]:
        s = s.replace(uni, ascii_)
    s = s.replace('\\', r'\textbackslash{}')
    for ch, esc in [('&', r'\&'), ('%', r'\%'), ('$', r'\$'), ('#', r'\#'),
                    ('{', r'\{'), ('}', r'\}'),          
                    ('_', r'\_\allowbreak{}'),            
                    ('~', r'\textasciitilde{}'), ('^', r'\^{}')]:
        s = s.replace(ch, esc)
    s = s.replace(':', r':\allowbreak{}')
    return s


def _render_value(source_dict, key, unit=""):
    val = source_dict.get(key)
    if val in ("", None):
        return ""
    val_str = str(val).strip()
    unit_clean = unit.strip()
    if unit_clean and (val_str.endswith(unit_clean) or val_str.endswith(unit)):
        return _tex(val)
    return _tex(val) + unit


def get_girder_entries(input_dict):
    """
    Retrieve all girder labels and member IDs from backend keys.

    Usage Example:
    --------------------------
    girder_entries = get_girder_entries(bridge.input_dict)
    
    # 1. Fallback handling (if backend hasn't populated keys yet)
    if not girder_entries:
        n = int(bridge.input_dict.get(KEY_TS_NO_OF_GIRDERS, 1))
        girder_entries = [(f"Girder {i}", f"M1") for i in range(1, n + 1)]
        
    # 2. Get total number of girders safely
    n_girders = len(girder_entries)
    
    # 3. Iterate over the girders to build table rows
    for lbl, mid in girder_entries:
        # lbl will be e.g., "G1", mid will be e.g., "G1M1"
        # Access girder specific keys dynamically:
        # val = input_dict.get(f"{KEY_MP_GIRDER_DEPTH}.{lbl}.{mid}")
        pass

    Returns:
        List[Tuple[str, str]]
    """
    n = int(input_dict.get(KEY_TS_NO_OF_GIRDERS, 0))

    entries = []

    for i in range(1, n + 1):
        entries.append(
            (
                input_dict.get(f"{KEY_MP_GD_SELECT_GIRDER}.G{i}", ""),
                input_dict.get(f"{KEY_MP_GD_MEMBER_ID}.G{i}.M1", ""),
            )
        )

    return entries


def _fig_or_placeholder(path, caption, width=FIG_WIDTH_DEFAULT):
    """Embed figure if path is provided (file already copied to assets), else show placeholder box.
    path is the relative path as pdflatex will see it (e.g. 'assets/plan.png').
    """
    if path:
        p = path.replace('\\', '/')
        return (r'\begin{figure}[H]' + '\n'
                r'\centering' + '\n'
                r'\includegraphics[width=' + width + ']{' + p + '}\n'
                r'\caption*{' + caption + '}\n'
                r'\end{figure}')
    return (r'\begin{figure}[H]' + '\n'
            r'\centering' + '\n'
            r'\fbox{\parbox{' + FIG_PLACEHOLDER_WIDTH + '}{' + '\n'
            r'\textit{[ PLACEHOLDER: ' + caption + r' ]}' + '\n'
            r'}}' + '\n'
            r'\caption*{' + caption + '}\n'
            r'\end{figure}')

def _fig_embed(path, caption, width=FIG_WIDTH_FULL, height=None):
    """Embed a real figure when path is provided (already copied); otherwise use an fbox placeholder."""
    if path:
        p = path.replace('\\', '/')
        opts = 'width=' + width
        if height:
            opts += ',height=' + height + ',keepaspectratio'
        return (r'\begin{figure}[H]' + '\n'
                r'\vspace{' + FIG_VSPACE_TOP + '}' + '\n'
                r'\centering' + '\n'
                r'\includegraphics[' + opts + ']{' + p + '}\n'
                r'\vspace{' + FIG_VSPACE_CAPTION + '}' + '\n'
                r'\caption*{\small ' + caption + '}\n'
                r'\vspace{' + FIG_VSPACE_BOTTOM + '}' + '\n'
                r'\end{figure}')
    # fbox placeholder — matches template exactly
    return (r'\noindent\fbox{\parbox{' + FIG_PLACEHOLDER_WIDTH + '}{' + '\n'
            r'\textit{[ PLACEHOLDER: ' + caption + r' ]}' + '\n'
            r'}}')


def build_longtable(
    col_spec: str,
    caption: str = None,
    headers: str = None,
    rows: list = None,
    continuation_headers: str = None,
    note: str = None,
    label: str = None,
    keep_groups_intact: bool = True,
    need_clearpage: bool = False,
) -> str:
    """
    Build a robust, multi-page-safe longtable LaTeX environment.

    Guarantees:
    1. Clean Firsthead & Continuation Separation:
       Emits \\caption and first-page header inside \\firsthead, followed
       immediately by an \\endfirsthead marker.
       Emits continuation headers inside \\endhead so that headers automatically
       and correctly repeat at the top of every subsequent page without
       orphaned headers.
    2. Automatic Row Group Protection (Prevent Awkward Page Breaks):
       When `rows` is provided as a list of row groups (e.g., per-girder blocks:
       [[g1_row1, g1_row2, ...], [g2_row1, g2_row2, ...]]), intermediate rows
       within a group automatically end with `\\*[6pt]` and `\\cline{...}`,
       which tells LaTeX's page breaker to forbid breaking inside the group.
       The final row of each group ends with standard `\\[6pt]` and `\\hline`,
       allowing LaTeX to break strictly between member groups.
    3. Proper Footnote and Boundary Management:
       Places any table notes or code references directly below `\\end{longtable}`.
       Optionally prefixes with `\\clearpage` when requested.
    4. Flexible Header & Caption Support:
       Supports standard tables, custom continuation headers, tables without
       conventional header rows, and uncaptioned tables.
    5. Full Column Width & Alignment Preservation:
       Passes through column specifications and content without modifying
       numerical data, formulas, or formatting.

    Parameters:
    -----------
    col_spec : str
        LaTeX column format specification, e.g. `{|C{2.5cm}|C{3.5cm}|p{4.2cm}|C{1.8cm}|}`.
    caption : str, optional
        Table caption string (can include LaTeX formatting like `\\textbf{...}`).
    headers : str, optional
        Header row(s) text, e.g. `\\textbf{Col 1} & \\textbf{Col 2} \\\\[6pt]`.
    rows : list of str or list of list of str, optional
        Either a flat list of formatted row strings, or a list of row groups
        (each group being a list of row strings representing one member block).
    continuation_headers : str, optional
        Custom header for continuation pages. If None, mirrors `headers`.
    note : str, optional
        Footnote / reference note printed below the table (e.g. `Note: IS 800 Cl. 8.4`).
    label : str, optional
        LaTeX label for cross-referencing (e.g. `tab:shear_checks`).
    keep_groups_intact : bool, default True
        When rows are grouped, whether to enforce non-breaking `\\*` within groups.
    need_clearpage : bool, default False
        Whether to precede the table with `\\clearpage`.

    Returns:
    --------
    str: Complete, self-contained LaTeX longtable snippet.
    """
    rows = rows or []
    cp_prefix = "\\clearpage\n" if need_clearpage else ""

    # 1. Format Caption and Label
    caption_block = ""
    if caption:
        clean_caption = caption.strip()
        if clean_caption.endswith(r"\\"):
            clean_caption = clean_caption[:-2].strip()
        lbl_tex = f"\\label{{{label}}}\n" if label else ""
        caption_block = f"\\caption{{{clean_caption}}}\\\\\\hline\n{lbl_tex}"
    elif label:
        caption_block = f"\\label{{{label}}}\n"

    # 2. Format Firsthead and Continuation Headers
    header_block = ""
    if headers:
        hdr_text = headers.strip()
        if not hdr_text.endswith(r"\\") and not hdr_text.endswith(f"[{ROW_BREAK_SPACE}]"):
            hdr_text += f" {ROW_BREAK_DEFAULT}"

        cont_hdr = continuation_headers.strip() if continuation_headers else hdr_text
        if not cont_hdr.endswith(r"\\") and not cont_hdr.endswith(f"[{ROW_BREAK_SPACE}]"):
            cont_hdr += f" {ROW_BREAK_DEFAULT}"

        header_block = (
            f"{hdr_text}\n\\hline\n"
            f"\\endfirsthead\n\\hline\n"
            f"{cont_hdr}\n\\hline\n"
            f"\\endhead\n"
        )
    else:
        # Table without conventional header row
        # Still provide \endfirsthead and \endhead markers to prevent leaks
        header_block = (
            f"\\endfirsthead\n"
            f"\\endhead\n"
        )

    # 3. Assemble Body Rows
    body_lines = []
    if rows and isinstance(rows[0], (list, tuple)):
        for group in rows:
            n_in_grp = len(group)
            for idx, r in enumerate(group):
                r_str = str(r).rstrip()
                is_last = (idx == n_in_grp - 1)
                if keep_groups_intact and not is_last:
                    if ROW_BREAK_NOBREAK not in r_str and ROW_BREAK_DEFAULT in r_str:
                        r_str = r_str.replace(ROW_BREAK_DEFAULT, ROW_BREAK_NOBREAK)
                    elif r"\\*" not in r_str and r"\\" in r_str:
                        r_str = r_str.replace(r"\\", r"\\*")
                body_lines.append(r_str)
            if body_lines and not body_lines[-1].endswith(r"\hline"):
                body_lines.append(r"\hline")
    else:
        for r in rows:
            body_lines.append(str(r).rstrip())

    body_tex = "\n".join(body_lines)
    note_tex = f"\n\\noindent\\textit{{{note}}}\n" if note else ""

    tex = (
        cp_prefix
        + f"\\begin{{longtable}}{{{col_spec}}}\n"
        + caption_block
        + header_block
        + f"{body_tex}\n"
        + f"\\end{{longtable}}"
        + note_tex
    )
    return tex


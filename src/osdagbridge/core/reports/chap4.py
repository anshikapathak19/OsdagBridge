from typing import TYPE_CHECKING
from osdagbridge.core.utils.common import (
    KEY_SPAN,
    KEY_TS_NO_OF_GIRDERS,
    KEY_SD_DEFL_LIVE,
    KEY_SD_DEFL_TOTAL,
)
from osdagbridge.core.reports.report_utils import _tex, _fig_embed
from osdagbridge.core.reports.report_style import (
    TABCOLSEP_MINIMAL,
    ARRAY_STRETCH_ANALYSIS,
    FIG_WIDTH_ENVELOPE,
    format_status_latex,
)

if TYPE_CHECKING:
    from .report_generator import ReportDataBridge

def ch4_analysis(asum, fig_paths, bridge: "ReportDataBridge", span_m: float):
    lc_summary  = (asum or {}).get('load_cases', {})
    rxn_summary = (asum or {}).get('reactions',  {})

    def _is_moving(lc_name: str) -> bool:
        n = lc_name.lower()
        return "moving" in n or " pos_" in n

    lc_summary  = {k: v for k, v in lc_summary.items()  if not _is_moving(k)}
    rxn_summary = {k: v for k, v in rxn_summary.items() if not _is_moving(k)}

    def _fmt(val, nd=3):
        try:
            return f"{float(val):.{nd}f}"
        except (TypeError, ValueError):
            return r"---"

    def _merged_row(lc, bm_d, rxn_d):
        bm_d  = bm_d  or {}
        rxn_d = rxn_d or {}
        return (
            _tex(lc)                              + r" & "
            + _fmt(bm_d.get('max_bm'))           + r" & "
            + _tex(bm_d.get('bm_girder', '---')) + r" & "
            + _fmt(bm_d.get('bm_location'))      + r" & "
            + _fmt(bm_d.get('max_sf'))           + r" & "
            + _tex(bm_d.get('sf_girder', '---')) + r" & "
            + _fmt(bm_d.get('sf_location'))      + r" & "
            + _fmt(rxn_d.get('left_kN'))         + r" & "
            + _fmt(rxn_d.get('right_kN'))        + r" \\[6pt]"
        )

    all_lcs = list(lc_summary.keys()) + [k for k in rxn_summary if k not in lc_summary]

    merged_body = ("\n\\hline\n").join(
        _merged_row(lc, lc_summary.get(lc), rxn_summary.get(lc))
        for lc in all_lcs
    ) if all_lcs else r"--- & --- & --- & --- & --- & --- & --- & --- & --- \\[6pt]"

    _span_m         = float(bridge.input_dict.get(KEY_SPAN, 0) or 0)
    _allow_live_mm  = _span_m * 1000.0 / 800.0
    _allow_total_mm = _span_m * 1000.0 / 600.0

    # Find governing girder — worst (max) deflection across all girders
    try:
        n = int(bridge.input_dict.get(KEY_TS_NO_OF_GIRDERS, 1) or 1)
    except (TypeError, ValueError):
        n = 1

    _live_mm  = None
    _total_mm = None
    for _gi in range(1, n + 1):
        _l = bridge.output_dict.get(f"{KEY_SD_DEFL_LIVE}.G{_gi}")
        _t = bridge.output_dict.get(f"{KEY_SD_DEFL_TOTAL}.G{_gi}")
        if _l is not None:
            _live_mm  = max(_live_mm, float(_l))  if _live_mm  is not None else float(_l)
        if _t is not None:
            _total_mm = max(_total_mm, float(_t)) if _total_mm is not None else float(_t)

    _live_str        = f"{_live_mm:.3f} mm"  if _live_mm  is not None else "---"
    _total_str       = f"{_total_mm:.3f} mm" if _total_mm is not None else "---"
    _allow_live_str  = f"L/800 = {_allow_live_mm:.1f} mm"
    _allow_total_str = f"L/600 = {_allow_total_mm:.1f} mm"
    _live_status     = (format_status_latex("PASS") if _live_mm  <= _allow_live_mm  else format_status_latex("FAIL")) if _live_mm  is not None else "---"
    _total_status    = (format_status_latex("PASS") if _total_mm <= _allow_total_mm else format_status_latex("FAIL")) if _total_mm is not None else "---"

    def _fmt_rxn(val):
        if val is None:
            return "N.A."
        try:
            f = abs(float(val))
            return f"{f:.2f} kN"
        except (TypeError, ValueError):
            return "N.A."

    def _lookup_reaction(target: str):
        if not rxn_summary:
            return None
        t = target.lower()

        # 1. Direct or normalized key match
        for k, v in rxn_summary.items():
            if not isinstance(v, dict):
                continue
            kl = k.lower().strip()
            if t == "dl" and kl in {"1.0 dl", "dl", "dead load", "dead_load"}:
                return v
            if t == "sidl" and kl in {"1.0 sidl", "sidl", "1.0 dw", "dw", "superimposed dead load", "superimposed_dead_load", "wearing coat"}:
                return v
            if t == "ll" and kl in {"1.0 ll", "ll", "live load", "live_load", "ll + impact"}:
                return v
            if t == "factored" and kl in {"envelope uls", "total design reaction", "total design reaction (factored)", "factored", "uls"}:
                return v

        # 2. Secondary checks if direct key was not found
        if t == "dl":
            sw = rxn_summary.get("SW")
            dd = rxn_summary.get("DD")
            if sw and dd and isinstance(sw, dict) and isinstance(dd, dict):
                return {
                    "left_kN": (sw.get("left_kN") or 0.0) + (dd.get("left_kN") or 0.0),
                    "right_kN": (sw.get("right_kN") or 0.0) + (dd.get("right_kN") or 0.0),
                }

        if t == "ll":
            dl_entry = _lookup_reaction("dl")
            combo_entry = None
            for k, v in rxn_summary.items():
                if "1.0 dl + 1.0 ll" in k.lower() and isinstance(v, dict):
                    combo_entry = v
                    break
            if dl_entry and combo_entry:
                try:
                    c_l, c_r = float(combo_entry.get("left_kN", 0)), float(combo_entry.get("right_kN", 0))
                    d_l, d_r = float(dl_entry.get("left_kN", 0)), float(dl_entry.get("right_kN", 0))
                    return {
                        "left_kN": abs(c_l) - abs(d_l),
                        "right_kN": abs(c_r) - abs(d_r),
                    }
                except (TypeError, ValueError):
                    pass

        if t == "factored":
            uls_entries = [
                v for k, v in rxn_summary.items()
                if isinstance(v, dict) and any(tag in k.lower() for tag in ("uls", "basic", "accidental", "seismic"))
            ]
            if uls_entries:
                try:
                    max_left = max(abs(float(v.get("left_kN", 0))) for v in uls_entries)
                    max_right = max(abs(float(v.get("right_kN", 0))) for v in uls_entries)
                    return {"left_kN": max_left, "right_kN": max_right}
                except (TypeError, ValueError):
                    pass

        return None

    dl_data       = _lookup_reaction("dl")
    sidl_data     = _lookup_reaction("sidl")
    ll_data       = _lookup_reaction("ll")
    factored_data = _lookup_reaction("factored")

    table42_rows = [
        ("Dead Load (DL)", _fmt_rxn(dl_data.get("left_kN") if dl_data else None), _fmt_rxn(dl_data.get("right_kN") if dl_data else None)),
        ("Superimposed Dead Load (SIDL)", _fmt_rxn(sidl_data.get("left_kN") if sidl_data else None), _fmt_rxn(sidl_data.get("right_kN") if sidl_data else None)),
        ("Live Load (LL)", _fmt_rxn(ll_data.get("left_kN") if ll_data else None), _fmt_rxn(ll_data.get("right_kN") if ll_data else None)),
        ("Total Design Reaction (Factored)", _fmt_rxn(factored_data.get("left_kN") if factored_data else None), _fmt_rxn(factored_data.get("right_kN") if factored_data else None)),
    ]

    table42_body = "\n\\hline\n".join(
        f"\\textbf{{{label}}} & {left} & {right} \\\\[6pt]"
        for label, left, right in table42_rows
    )
    return r"""
\chapter{Analysis Results}

A grillage model was used for structural analysis. The deck is idealized as a grid of elastic beam elements --- longitudinal members represent the composite steel girders with effective slab, and transverse members represent the slab or cross frames. This section summarizes the critical output from that analysis.

\vspace{1em}
\begingroup
\footnotesize
\setlength{\tabcolsep}{""" + TABCOLSEP_MINIMAL + r"""}
\renewcommand{\arraystretch}{""" + str(ARRAY_STRETCH_ANALYSIS) + r"""}

\begin{longtable}{|
>{\centering\arraybackslash}p{3.1cm}|
>{\centering\arraybackslash}p{1.7cm}|
>{\centering\arraybackslash}p{1.2cm}|
>{\centering\arraybackslash}p{1.3cm}|
>{\centering\arraybackslash}p{1.7cm}|
>{\centering\arraybackslash}p{1.2cm}|
>{\centering\arraybackslash}p{1.3cm}|
>{\centering\arraybackslash}p{1.6cm}|
>{\centering\arraybackslash}p{1.6cm}|}

\caption{\textbf{Summary of Maximum Demands}}\\
\hline
\multirow{2}{*}{\makecell{\textbf{Load Case/}\\\textbf{Comb.}}}
& \multicolumn{3}{c|}{\textbf{Bending Moment}}
& \multicolumn{3}{c|}{\textbf{Shear Force}}
& \multicolumn{2}{c|}{\textbf{Reaction at Supports}}\\
\cline{2-9}

& \makecell{\textbf{Max}\\\textbf{(kNm)}}
& \textbf{Girder}
& \makecell{\textbf{Loc.}\\\textbf{(m)}}
& \makecell{\textbf{Max}\\\textbf{(kN)}}
& \textbf{Girder}
& \makecell{\textbf{Loc.}\\\textbf{(m)}}
& \makecell{\textbf{Left}}
& \makecell{\textbf{Right }}\\
\hline
\endfirsthead

\hline
\multirow{2}{*}{\makecell{\textbf{Load Case/}\\\textbf{Comb.}}}
& \multicolumn{3}{c|}{\textbf{Bending Moment}}
& \multicolumn{3}{c|}{\textbf{Shear Force}}
& \multicolumn{2}{c|}{\textbf{Reaction at Supports}}\\
\cline{2-9}

& \makecell{\textbf{Max}\\\textbf{(kNm)}}
& \textbf{Girder}
& \makecell{\textbf{Loc.}\\\textbf{(m)}}
& \makecell{\textbf{Max}\\\textbf{(kN)}}
& \textbf{Girder}
& \makecell{\textbf{Loc.}\\\textbf{(m)}}
& \makecell{\textbf{Left}}
& \makecell{\textbf{Right}}\\
\hline
\endhead

""" + merged_body + r"""

\hline
\end{longtable}
\endgroup

\clearpage
\begin{longtable}{|>{\centering\arraybackslash}p{5.2cm}|>{\centering\arraybackslash}p{5.2cm}|>{\centering\arraybackslash}p{5.2cm}|}
\caption{\textbf{Reactions at Supports}}\\
\hline
\textbf{Load Case} & \textbf{Left Support (kN)} & \textbf{Right Support (kN)} \\[6pt]
\hline
\endfirsthead
\hline
\textbf{Load Case} & \textbf{Left Support (kN)} & \textbf{Right Support (kN)} \\[6pt]
\hline
\endhead
""" + table42_body + r"""
\hline
\end{longtable}

\vspace{1em}
\begin{longtable}{|L{7cm}|p{8.5cm}|}
\caption{\textbf{Deflection Summary (Live Load \& Total Load)}}\\
\hline
\textbf{parameter} & \textbf{value} \\
\hline
\endfirsthead
\hline
\textbf{parameter} & \textbf{value} \\
\hline
\endhead
\textnormal{Deflection due to Live Load, $\delta_{LL}$} & """ + _live_str + r""" \\[6pt]
\hline
\textnormal{Allowable Live Load Deflection ($\Delta_{allow}$)} & """ + _allow_live_str + r""" \\[6pt]
\hline
\textnormal{Live Load Deflection Check Status} & """ + _live_status + r""" \\[6pt]
\hline
\textnormal{Deflection due to Total Load, $\delta_{total}$} & """ + _total_str + r""" \\[6pt]
\hline
\textnormal{Allowable Total Deflection ($\Delta_{allow}$)} & """ + _allow_total_str + r""" \\[6pt]
\hline
\textnormal{Total Load Deflection Check Status} & """ + _total_status + r""" \\[6pt]
\hline
\end{longtable}

\vspace{1em}
\noindent
""" + _fig_embed(fig_paths.get('bm_envelope'), 'Bending Moment Envelope (Envelope ULS): Max/min BM along span. X-axis: distance from left support (m). Y-axis: Bending Moment (kN-m).', width=FIG_WIDTH_ENVELOPE) + r"""
""" + _fig_embed(fig_paths.get('sf_envelope'), 'Shear Force Envelope (Envelope ULS): Max/min SF along span. X-axis: distance from left support (m). Y-axis: Shear Force (kN).', width=FIG_WIDTH_ENVELOPE) + r"""
""" + _fig_embed(fig_paths.get('defl_ll'), 'Vertical Deflection D$_y$ (1.0 LL): Maximum deflection along span. Load Case: 1.0 LL, Combination: $D_y$. Nodes shown. Isometric view.', width=FIG_WIDTH_ENVELOPE) + r"""
"""


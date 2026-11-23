def ch7_quantities(input_dict, fig_paths=None):
    def _mat_chart_fig(path_key, caption_title, label):
        path = (fig_paths or {}).get(path_key)
        label_tex = (r"\label{" + label + "}\n") if label else ""
        if path:
            p = str(path).replace("\\", "/")
            return (
                r"\begin{figure}[H]" + "\n"
                r"\centering" + "\n"
                r"\vspace{2pt}" + "\n"
                r"\includegraphics[width=0.78\textwidth]{" + p + r"}" + "\n"
                r"\caption{\textbf{" + caption_title + r"}}" + "\n"
                + label_tex
                + r"\end{figure}" + "\n"
            )
        return ""

    steel_fig = _mat_chart_fig("material_chart_steel_tonnage", "Structural Steel Tonnage by Component", "fig:mat_steel_tonnage")
    concrete_fig = _mat_chart_fig("material_chart_concrete_rebar", r"Deck Slab Materials --- Concrete Volume vs.\ Reinforcement Steel Weight", "fig:mat_concrete_rebar")

    vis_content = ""
    if steel_fig or concrete_fig:
        vis_content = r"""
\vspace{1.5em}
\clearpage
\section{Material Quantity Visualizations}
\label{sec:material-charts}

\noindent
The following bar charts summarize the primary material quantities required for superstructure fabrication and deck construction. Figure~\ref{fig:mat_steel_tonnage} details the structural steel tonnage breakdown among the main plate girders, intermediate cross bracing, and support end diaphragms. Figure~\ref{fig:mat_concrete_rebar} presents the concrete volume alongside the corresponding reinforcement steel weight for the reinforced concrete deck slab.

\vspace{0.4em}
""" + steel_fig + r"""

\vspace{0.4em}
""" + concrete_fig

    return r"""
\chapter{Material Take-off \& Quantity Summary}
\label{ch:material-takeoff}

\noindent\textbf{Table 7.1  Bill of Materials (Steel, Concrete, and Reinforcement Quantities)}

\begingroup
\setlength{\tabcolsep}{3.5pt}
\begin{longtable}{|C{1.0cm}|L{3.8cm}|C{2.6cm}|C{1.8cm}|C{1.8cm}|C{1.8cm}|C{1.8cm}|}
\hline
\textbf{S.N.} & \textbf{Item Description} & \textbf{Volume} & \textbf{Quantity} & \textbf{Total Volume} & \textbf{Weight (MT)} & \textbf{Total Weight (MT)} \\
\hline
\endfirsthead
\hline
\textbf{S.N.} & \textbf{Item Description} & \textbf{Volume} & \textbf{Quantity} & \textbf{Total Volume} & \textbf{Weight (MT)} & \textbf{Total Weight (MT)} \\
\hline
\endhead
1 & Structural Steel (IS 2062) for Girders & """ + str(input_dict.get("steel_girders_vol_formula", "N.A.")) + r""" & """ + str(input_dict.get("steel_girders_qty", "N.A.")) + r""" & """ + str(input_dict.get("steel_girders_vol_total", "N.A.")) + r""" & """ + str(input_dict.get("steel_girders_wt_single", "N.A.")) + r""" & """ + str(input_dict.get("steel_girders_wt_total", "N.A.")) + r""" \\
\hline
2(a) & Cross Bracing - Top Chord & """ + str(input_dict.get("bracing_top_vol_formula", "N.A.")) + r""" & """ + str(input_dict.get("bracing_top_qty", "N.A.")) + r""" & """ + str(input_dict.get("bracing_top_vol_total", "N.A.")) + r""" & """ + str(input_dict.get("bracing_top_wt_single", "N.A.")) + r""" & """ + str(input_dict.get("bracing_top_wt_total", "N.A.")) + r""" \\
\hline
2(b) & Cross Bracing - Bottom Chord & """ + str(input_dict.get("bracing_bot_vol_formula", "N.A.")) + r""" & """ + str(input_dict.get("bracing_bot_qty", "N.A.")) + r""" & """ + str(input_dict.get("bracing_bot_vol_total", "N.A.")) + r""" & """ + str(input_dict.get("bracing_bot_wt_single", "N.A.")) + r""" & """ + str(input_dict.get("bracing_bot_wt_total", "N.A.")) + r""" \\
\hline
2(c) & Cross Bracing - Diagonal Chord & """ + str(input_dict.get("bracing_diag_vol_formula", "N.A.")) + r""" & """ + str(input_dict.get("bracing_diag_qty", "N.A.")) + r""" & """ + str(input_dict.get("bracing_diag_vol_total", "N.A.")) + r""" & """ + str(input_dict.get("bracing_diag_wt_single", "N.A.")) + r""" & """ + str(input_dict.get("bracing_diag_wt_total", "N.A.")) + r""" \\
\hline
2(d) & End Diaphragms (at Supports) & """ + str(input_dict.get("end_diaphragm_vol_formula", "N.A.")) + r""" & """ + str(input_dict.get("end_diaphragm_qty", "N.A.")) + r""" & """ + str(input_dict.get("end_diaphragm_vol_total", "N.A.")) + r""" & """ + str(input_dict.get("end_diaphragm_wt_single", "N.A.")) + r""" & """ + str(input_dict.get("end_diaphragm_wt_total", "N.A.")) + r""" \\
\hline
3 & Concrete (M40) for Deck Slab & """ + str(input_dict.get("concrete_deck_vol_formula", "N.A.")) + r""" & """ + str(input_dict.get("concrete_deck_qty", "N.A.")) + r""" & """ + str(input_dict.get("concrete_deck_vol_total", "N.A.")) + r""" & """ + str(input_dict.get("concrete_deck_wt_single", "N.A.")) + r""" & """ + str(input_dict.get("concrete_deck_wt_total", "N.A.")) + r""" \\
\hline
4 & Reinforcement Steel (Fe 500) & """ + str(input_dict.get("rebar_deck_vol_formula", "N.A.")) + r""" & """ + str(input_dict.get("rebar_deck_qty", "N.A.")) + r""" & """ + str(input_dict.get("rebar_deck_vol_total", "N.A.")) + r""" & """ + str(input_dict.get("rebar_deck_wt_single", "N.A.")) + r""" & """ + str(input_dict.get("rebar_deck_wt_total", "N.A.")) + r""" \\
\hline
5 & Shear Stud Connectors & """ + str(input_dict.get("shear_studs_vol_formula", "N.A.")) + r""" & """ + str(input_dict.get("shear_studs_qty", "N.A.")) + r""" & """ + str(input_dict.get("shear_studs_vol_total", "N.A.")) + r""" & """ + str(input_dict.get("shear_studs_wt_single", "N.A.")) + r""" & """ + str(input_dict.get("shear_studs_wt_total", "N.A.")) + r""" \\
\hline
6 & Crash Barrier & """ + str(input_dict.get("crash_barrier_vol_formula", "N.A.")) + r""" & """ + str(input_dict.get("crash_barrier_qty", "N.A.")) + r""" & """ + str(input_dict.get("crash_barrier_vol_total", "N.A.")) + r""" & """ + str(input_dict.get("crash_barrier_wt_single", "N.A.")) + r""" & """ + str(input_dict.get("crash_barrier_wt_total", "N.A.")) + r""" \\
\hline
\end{longtable}
\endgroup

\noindent\textit{Note: Reinforcement steel quantity is estimated based on the standard structural design allowance of $120\text{ kg/m}^3$ of deck concrete volume. For end diaphragms (Item 2(d)), the total volume ($0.01\text{ m}^3$) and weight ($0.10\text{ MT}$) are calculated using the individual member lengths: 12 diagonals at $2.53\text{ m}$ ($0.0047\text{ MT}$ each), 6 top chords at $2.10\text{ m}$ ($0.0039\text{ MT}$ each), and 6 bottom chords at $2.10\text{ m}$ ($0.0039\text{ MT}$ each) across both bridge supports. The displayed length ($2.31\text{ m}$) and weight ($0.0043\text{ MT}$) represent the weighted average equivalent values per member across all 24 members.}
""" + vis_content

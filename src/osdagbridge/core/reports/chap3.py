# =============================================================================
# Chapter 3: Loads and Load Combinations
# Extracted from report_generator.py — DO NOT add business logic here.
# =============================================================================

from osdagbridge.core.utils.common import (
    KEY_BL_IRC_CLASS_SV,
    KEY_CARRIAGEWAY_WIDTH,
    KEY_CB_LOAD,
    KEY_FOOTPATH,
    KEY_LL_CUSTOM_VEHICLES,
    KEY_LL_ECCENTRICITY,
    KEY_LL_FOOTPATH_PRESSURE_MODE,
    KEY_LL_FOOTPATH_PRESSURE_VALUE,
    KEY_LL_IRC_70R_BOGIE,
    KEY_LL_IRC_70R_TRACKED,
    KEY_LL_IRC_70R_WHEELED,
    KEY_LL_IRC_AA_TRACKED,
    KEY_LL_IRC_AA_WHEELED,
    KEY_LL_IRC_CLASS_A,
    KEY_LL_IRC_CLASS_FATIGUE,
    KEY_LL_IRC_CLASS_SV,
    KEY_MATERIAL_DECK_DENSITY,
    KEY_MATERIAL_GIRDER_DENSITY,
    KEY_PL_SELF_WEIGHT_FACTOR,
    KEY_RL_LOAD_VALUE,
    KEY_SL_DAMPING,
    KEY_SL_DEAD_LOAD_MODE,
    KEY_SL_DEAD_LOAD_VALUE,
    KEY_SL_HORIZONTAL_COEFF,
    KEY_SL_IMPORTANCE_FACTOR,
    KEY_SL_LIVE_LOAD_MODE,
    KEY_SL_LIVE_LOAD_VALUE,
    KEY_SL_SEISMIC_ZONE,
    KEY_SL_SOIL_TYPE,
    KEY_SL_SPECTRAL_COEFF,
    KEY_SL_TIME_PERIOD,
    KEY_SL_VERTICAL_COEFF,
    KEY_SL_ZONE_FACTOR,
    KEY_SPAN,
    KEY_TL_BRIDGE_TEMP_MAX,
    KEY_TL_BRIDGE_TEMP_MIN,
    KEY_TL_HIGHEST_MAX_TEMP,
    KEY_TL_LOWEST_MIN_TEMP,
    KEY_TL_TEMP_FALL,
    KEY_TL_TEMP_RISE,
    KEY_TS_FOOTPATH_WIDTH,
    KEY_TS_NO_OF_FOOTPATHS,
    KEY_WC_LD_LANE_TABLE_COUNT,
    KEY_WC_MATERIAL,
    KEY_WC_THICKNESS,
    KEY_WL_AVG_EXPOSED_HEIGHT,
    KEY_WL_BASIC_WIND_SPEED,
    KEY_WL_HOURLY_MEAN_WIND,
    KEY_WL_HOURLY_WIND_PRESSURE,
    KEY_WL_LONGITUDINAL_WIND_FORCE,
    KEY_WL_TERRAIN_TYPE,
    KEY_WL_TRANSVERSE_WIND_FORCE,
    KEY_WL_VERTICAL_WIND_FORCE
)

from osdagbridge.core.reports.report_utils import _tex, _render_value, build_longtable
from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017

def ch3_loads(input_dict):
    # ── Helpers ──────────────────────────────────────────────────────────
    def _is_selected(val):
        """Strict boolean resolution for UI selections (e.g. 'False' is not True)."""
        if val is True:
            return True
        if val is False or val in (None, ""):
            return False
        if isinstance(val, (int, float)):
            return val != 0
        s = str(val).strip().lower()
        return s in ("true", "yes", "1", "checked")

    # ── Table 3.3: Vehicle Live Load Parameters ──────────────────────────
    span_val = input_dict.get(KEY_SPAN)
    try:
        span_m = float(span_val) if span_val not in (None, "") else 30.0
    except (ValueError, TypeError):
        span_m = 30.0

    # Retrieve carriageway width and design lane count per IRC 6 Table 6
    cw_val = input_dict.get(KEY_CARRIAGEWAY_WIDTH)
    try:
        cw_m = float(cw_val) if cw_val not in (None, "") else 7.50
    except (ValueError, TypeError):
        cw_m = 7.50

    lanes_val = input_dict.get(KEY_WC_LD_LANE_TABLE_COUNT)
    if lanes_val in (None, ""):
        try:
            lanes = IRC6_2017.table_6(cw_m)
        except Exception:
            lanes = 2
    else:
        try:
            lanes = int(lanes_val)
        except Exception:
            lanes = 2

    # Dynamic Governing Braking Force calculation per IRC 6 Cl. 211.2 & Table 6A
    braking_info = IRC6_2017.cl_211_2_braking_force(
        design_lanes=lanes,
        vehicle_type="wheeled",
        span_m=span_m,
        carriageway_width=cw_m,
        return_details=True
    )
    governing_braking_force_kN = braking_info.get("governing_force_kN", 196.20)
    gov_comb_str = braking_info.get("governing_combination", "1 Lane of Class 70R Wheeled")
    f_first_val = braking_info.get("first_train_kN", 196.20)
    f_succ_val = braking_info.get("succeeding_train_kN", 0.0)
    f_add_val = braking_info.get("additional_lanes_kN", 0.0)

    ecc_val = input_dict.get(KEY_LL_ECCENTRICITY)
    try:
        ecc_m = float(ecc_val) if ecc_val not in (None, "") else 1.20
    except (ValueError, TypeError):
        ecc_m = 1.20

    # Impact factors per IRC 6 Cl. 208
    try:
        im_a = IRC6_2017.cl_208_2_impact_factor(span_m)
    except Exception:
        im_a = 0.207
    try:
        im_wheeled = IRC6_2017.cl_208_3_impact_factor(span_m, vehicle_type="wheeled")
    except Exception:
        im_wheeled = 0.207
    try:
        im_tracked = IRC6_2017.cl_208_3_impact_factor(span_m, vehicle_type="tracked")
    except Exception:
        im_tracked = 0.10 if span_m >= 5.0 else 0.25

    # Class SV braking opt-in (default True per defaults.py, but checked independently)
    sv_braking_opt_in = _is_selected(input_dict.get(KEY_BL_IRC_CLASS_SV, True))

    try:
        w_class_a_actual = IRC6_2017.get_vehicle_load_kN("class_a")
    except Exception:
        w_class_a_actual = 543.5

    try:
        w_70r_wh_actual = IRC6_2017.get_vehicle_load_kN("wheeled")
    except Exception:
        w_70r_wh_actual = 981.0

    try:
        w_70r_tr_actual = IRC6_2017.get_vehicle_load_kN("tracked")
    except Exception:
        w_70r_tr_actual = 686.7

    standard_vehicles = [
        {
            "key": KEY_LL_IRC_CLASS_A,
            "name": "Class A",
            "load_kN": 543.5,
            "impact": 1.0 + im_a,
            "braking_considered": True,
            "base_braking_kN": 108.70,
        },
        {
            "key": KEY_LL_IRC_70R_WHEELED,
            "name": "Class 70R (Wheeled)",
            "load_kN": 981.0,
            "impact": 1.0 + im_wheeled,
            "braking_considered": True,
            "base_braking_kN": 196.20,
        },
        {
            "key": KEY_LL_IRC_70R_TRACKED,
            "name": "Class 70R (Tracked)",
            "load_kN": 686.7,
            "impact": 1.0 + im_tracked,
            "braking_considered": True,
            "base_braking_kN": 137.34,
        },
        {
            "key": KEY_LL_IRC_70R_BOGIE,
            "name": "Class 70R (Bogie)",
            "load_kN": 392.4,
            "impact": 1.0 + im_wheeled,
            "braking_considered": True,
            "base_braking_kN": 78.48,
        },
        {
            "key": KEY_LL_IRC_AA_WHEELED,
            "name": "Class AA (Wheeled)",
            "load_kN": 392.4,
            "impact": 1.0 + im_wheeled,
            "braking_considered": True,
            "base_braking_kN": 78.48,
        },
        {
            "key": KEY_LL_IRC_AA_TRACKED,
            "name": "Class AA (Tracked)",
            "load_kN": w_70r_tr_actual,
            "impact": 1.0 + im_tracked,
            "braking_considered": True,
            "base_braking_kN": round(0.20 * w_70r_tr_actual, 2),
        },
        {
            "key": KEY_LL_IRC_CLASS_SV,
            "name": "Class SV (Special Vehicle)",
            "load_kN": 3776.85,
            "impact": 1.000,
            "braking_considered": sv_braking_opt_in,
            "base_braking_kN": 755.37,
        },
        {
            "key": KEY_LL_IRC_CLASS_FATIGUE,
            "name": "Class Fatigue",
            "load_kN": 392.4,
            "impact": 1.000,
            "braking_considered": False,
            "base_braking_kN": None,
        },
    ]

    t33_rows = []
    for vdef in standard_vehicles:
        if _is_selected(input_dict.get(vdef["key"])):
            v_name = vdef["name"]
            v_load = f"{vdef['load_kN']:.1f}" if isinstance(vdef['load_kN'], float) else str(vdef['load_kN'])
            v_impact = f"{vdef['impact']:.3f}" if isinstance(vdef['impact'], float) else str(vdef['impact'])
            if vdef["braking_considered"]:
                brk_cons = "Yes"
                b_force_val = vdef.get("base_braking_kN")
                if b_force_val is not None:
                    brk_force = f"{b_force_val:.2f}"
                else:
                    brk_force = f"{0.20 * float(vdef['load_kN']):.2f}"
                brk_ecc = f"{ecc_m:.2f}"
            else:
                brk_cons = "No"
                brk_force = "---"
                brk_ecc = "---"
            v_cf = "Not Applicable"
            t33_rows.append(
                f"{_tex(v_name)} & {v_load} & {v_impact} & {brk_cons} & {brk_force} & {brk_ecc} & {v_cf} \\\\[4pt]\\hline"
            )

    custom = input_dict.get(KEY_LL_CUSTOM_VEHICLES)
    if custom and isinstance(custom, list):
        for c in custom:
            if isinstance(c, dict):
                c_name = c.get("name", "Custom Vehicle")
                if c.get("total_load_kN") is not None:
                    c_load = f"{float(c['total_load_kN']):.1f}"
                elif c.get("axle_loads"):
                    c_load = f"{sum(float(x) for x in c['axle_loads']):.1f}"
                elif c.get("axles"):
                    c_load = f"{sum(float(a.get('load_kN', 0)) for a in c['axles']):.1f}"
                else:
                    c_load = "---"
                c_im_val = c.get("impact_factor")
                if c_im_val is not None:
                    try:
                        c_impact = f"{1.0 + float(c_im_val):.3f}"
                    except (ValueError, TypeError):
                        c_impact = "1.250"
                else:
                    c_impact = "1.250"
            else:
                c_name = str(c)
                c_load = "---"
                c_impact = "1.250"
            if c_load != "---":
                try:
                    c_brk_str = f"{0.20 * float(c_load):.2f}"
                    c_ecc_str = f"{ecc_m:.2f}"
                    c_cons_str = "Yes"
                except Exception:
                    c_brk_str = "---"
                    c_ecc_str = "---"
                    c_cons_str = "No"
            else:
                c_brk_str = "---"
                c_ecc_str = "---"
                c_cons_str = "No"
            t33_rows.append(
                f"{_tex(c_name)} & {c_load} & {c_impact} & {c_cons_str} & {c_brk_str} & {c_ecc_str} & Not Applicable \\\\[4pt]\\hline"
            )

    if not t33_rows:
        t33_rows.append(r"No vehicle selected & --- & --- & --- & --- & --- & --- \\[4pt]\hline")

    col_spec_33 = '|L{3.0cm}|C{1.8cm}|C{1.6cm}|C{2.2cm}|C{1.8cm}|C{1.7cm}|C{2.3cm}|'
    caption_33 = r'\textbf{Vehicle Live Load Parameters}'
    headers_33 = (
        r'\multirow{3}{*}{\makecell{\textbf{Vehicle}\\\textbf{Class}}} & \multirow{3}{*}{\makecell{\textbf{Total}\\\textbf{Load}\\\textbf{(kN)}}} & \multirow{3}{*}{\makecell{\textbf{Impact}\\\textbf{Factor}}} & \multicolumn{3}{c|}{\textbf{Braking Load (IRC 6 Cl. 211)}} & \multirow{3}{*}{\makecell{\textbf{Centrifugal}\\\textbf{Force}\\\textbf{(kN)}}} \\' + '\n'
        + r'\cline{4-6}' + '\n'
        + r' & & & \textbf{Considered} & \makecell{\textbf{Force}\\\textbf{(kN)}} & \makecell{\textbf{Height}\\\textbf{(m)}} & '
    )
    note_33 = 'Note: Braking forces shown above are base vehicle forces (20\\% of vehicle weight per IRC 6 Cl. 211.2). See the governing longitudinal braking table below for bridge-level multi-lane combinations. Centrifugal force is Not Applicable for straight bridge alignment ($R = \\infty$) per IRC 6 Cl. 212.'

    t33_tex = build_longtable(
        col_spec=col_spec_33,
        caption=caption_33,
        headers=headers_33,
        rows=t33_rows,
        note=note_33,
        label='tab:vehicle_live_loads'
    )

    if f_succ_val > 0.0:
        succ_disp = f"{f_succ_val:.2f} kN (IRC 6 Cl. 211.2a)"
    else:
        succ_disp = f"0.00 kN (IRC 6 Cl. 211.2a; succeeding train cannot fit on {span_m:.1f}\\,m span)"

    t33_summary_tex = (
        r"\vspace{1em}" + "\n"
        r"\noindent\textbf{Governing Longitudinal Braking Force (IRC 6 Clause 211.2)}" + "\n"
        r"\vspace{0.5em}" + "\n"
        r"\begin{longtable}{|L{6.0cm}|p{9.5cm}|}" + "\n"
        r"\hline" + "\n"
        r"\textbf{Parameter} & \textbf{Design Value / Reference} \\" + "\n"
        r"\hline" + "\n"
        r"\endfirsthead" + "\n"
        r"\hline" + "\n"
        r"\textbf{Parameter} & \textbf{Design Value / Reference} \\" + "\n"
        r"\hline" + "\n"
        r"\endhead" + "\n"
        f"Number of Design Lanes & {lanes} (determined per IRC 6 Table 6) \\\\[4pt]\n"
        r"\hline" + "\n"
        f"Carriageway Width & {cw_m:.2f} m \\\\[4pt]\n"
        r"\hline" + "\n"
        f"Governing Vehicle Combination & {gov_comb_str} (governs per IRC Table 6A) \\\\[4pt]\n"
        r"\hline" + "\n"
        f"First-Train Contribution (20\\%) & {f_first_val:.2f} kN (IRC 6 Cl. 211.2a) \\\\[4pt]\n"
        r"\hline" + "\n"
        f"Succeeding-Train Contribution (10\\%) & {succ_disp} \\\\[4pt]\n"
        r"\hline" + "\n"
        f"Additional-Lane Contribution (5\\%) & {f_add_val:.2f} kN (IRC 6 Cl. 211.2b) \\\\[4pt]\n"
        r"\hline" + "\n"
        f"\\textbf{{Total Governing Braking Force}} & \\textbf{{{governing_braking_force_kN:.2f} kN}} \\\\[4pt]\n"
        r"\hline" + "\n"
        f"Application Height above Roadway & {ecc_m:.2f} m (IRC 6 Cl. 211.3) \\\\[4pt]\n"
        r"\hline" + "\n"
        r"\end{longtable}" + "\n"
        r"\vspace{-0.5em}" + "\n"
        r"\noindent\textit{\footnotesize Note: Per IRC 6:2017 Cl. 211.2, braking effect is evaluated on one lane only for the first two lanes (20\% of first train + 10\% of succeeding trains per Cl. 211.2a). For bridges with $> 2$ lanes, 5\% of vehicle loads on each additional lane is added per Cl. 211.2(b). All permitted vehicle combinations under IRC 6:2017 Table 6A are evaluated to establish the governing longitudinal braking force.}"
    )

    # ── Table 3.4: Footpath / Pedestrian Live Load ───────────────────────
    fp_provision = str(input_dict.get(KEY_FOOTPATH, "")).strip()
    if not fp_provision or fp_provision.lower() in ("none", "false", "no", "0"):
        t34_rows = [
            r"Footpath Provision & None & geometry.footpath \\[6pt]\hline",
            r"Number of Footpaths & 0 & typical\_section.no\_of\_footpaths \\[6pt]\hline",
            r"Footpath Width (m) & --- & Not Applicable \\[6pt]\hline",
            r"Pressure Mode & --- & Not Applicable \\[6pt]\hline",
            r"Applied Footpath Live Load & Not Applicable & No footpath provided \\[6pt]\hline",
        ]
    else:
        n_fp = input_dict.get(KEY_TS_NO_OF_FOOTPATHS)
        if n_fp in (None, ""):
            n_fp = 1 if "single" in fp_provision.lower() else 2
        fp_w = input_dict.get(KEY_TS_FOOTPATH_WIDTH)
        try:
            fp_w_disp = f"{float(fp_w):.2f} m" if fp_w not in (None, "") else "1.50 m"
        except (ValueError, TypeError):
            fp_w_disp = f"{fp_w} m" if fp_w else "1.50 m"

        fp_mode = str(input_dict.get(KEY_LL_FOOTPATH_PRESSURE_MODE, "")).strip()
        fp_value = input_dict.get(KEY_LL_FOOTPATH_PRESSURE_VALUE)

        if fp_mode.lower() in ("custom", "user-defined") and fp_value not in (None, ""):
            fp_mode_disp = "Custom"
            try:
                fp_pressure_disp = f"{float(fp_value):.3f} kN/m\\textsuperscript{{2}}"
            except (ValueError, TypeError):
                fp_pressure_disp = f"{fp_value} kN/m\\textsuperscript{{2}}"
            fp_ref_disp = "User-defined custom pressure"
        else:
            fp_mode_disp = "As per IRC 6"
            try:
                fp_pressure_disp = f"{IRC6_2017.cl_206_1_footway_load():.3f} kN/m\\textsuperscript{{2}}"
            except Exception:
                fp_pressure_disp = r"4.905 kN/m\textsuperscript{2}"
            fp_ref_disp = r"IRC 6 Cl. 206.1 (500 kg/m\textsuperscript{2})"

        t34_rows = [
            f"Footpath Provision & {_tex(fp_provision.title())} & geometry.footpath \\\\[6pt]\\hline",
            f"Number of Footpaths & {n_fp} & typical\\_section.no\\_of\\_footpaths \\\\[6pt]\\hline",
            f"Footpath Width (m) & {fp_w_disp} & IRC 5 Cl. 104.3.6 (min: 1.5 m) \\\\[6pt]\\hline",
            f"Pressure Mode & {_tex(fp_mode_disp)} & User configuration \\\\[6pt]\\hline",
            f"Applied Footpath Live Load & {fp_pressure_disp} & {fp_ref_disp} \\\\[6pt]\\hline",
        ]

    col_spec_34 = '|L{5.5cm}|C{3.5cm}|L{6.0cm}|'
    caption_34 = r'\textbf{Footpath / Pedestrian Live Load}'
    headers_34 = r'\textbf{Parameter} & \textbf{Design Value} & \textbf{Reference / Note}'
    note_34 = 'Note: Pedestrian live load is applied uniformly over the clear footway area per IRC 6 Cl. 206.1.'

    t34_tex = build_longtable(
        col_spec=col_spec_34,
        caption=caption_34,
        headers=headers_34,
        rows=t34_rows,
        note=note_34,
        label='tab:footpath_live_load'
    )

    # Vz / Pz — prefer stored computed values; fall back to IRC6 Table 12
    vz_val = input_dict.get(KEY_WL_HOURLY_MEAN_WIND)
    pz_val = input_dict.get(KEY_WL_HOURLY_WIND_PRESSURE)
    if not vz_val or not pz_val:
        try:
            _vb  = input_dict.get(KEY_WL_BASIC_WIND_SPEED) or input_dict.get('wind_speed')
            _h   = input_dict.get(KEY_WL_AVG_EXPOSED_HEIGHT)
            _ter = {
                "Plain Terrain": "plain",
                "Terrain with Obstructions": "obstructed",
            }.get(str(input_dict.get(KEY_WL_TERRAIN_TYPE, "")).strip(), "plain")
            _res = IRC6_2017.table_12(float(_h), _ter, float(_vb))
            if not vz_val:
                vz_val = _res.get("Vz")
            if not pz_val:
                pz_val = _res.get("Pz")
        except Exception:
            pass
    vz_str = f"{float(vz_val):.2f} m/s" if vz_val not in (None, "") else "N/A"
    pz_str = f"{float(pz_val):.2f} N/m²" if pz_val not in (None, "") else "N/A"

    # Table 3.5 — Seismic: prefer stored computed values; fall back to IRC6 cl_218_5_1
    sl_zone_factor = input_dict.get(KEY_SL_ZONE_FACTOR)
    sl_spectral    = input_dict.get(KEY_SL_SPECTRAL_COEFF)
    sl_ah          = input_dict.get(KEY_SL_HORIZONTAL_COEFF)
    sl_av          = input_dict.get(KEY_SL_VERTICAL_COEFF)
    if not sl_ah or not sl_zone_factor:
        try:
            _zone = input_dict.get(KEY_SL_SEISMIC_ZONE) or input_dict.get('seismic_zone')
            _zmap = {"1": "I", "2": "II", "3": "III", "4": "IV", "5": "V"}
            _z    = str(_zone).strip().upper()
            if _z.isdigit():
                _z = _zmap.get(_z)
            _smap = {"Type I – Rocky or Hard": 1, "Type II – Medium Soil": 2, "Type III – Soft Soil": 3}
            _st   = _smap.get(str(input_dict.get(KEY_SL_SOIL_TYPE, "")), 1)
            _tp   = input_dict.get(KEY_SL_TIME_PERIOD)
            _damp = input_dict.get(KEY_SL_DAMPING) or "5"
            _dl_v = input_dict.get(KEY_SL_DEAD_LOAD_VALUE)
            _ll_v = input_dict.get(KEY_SL_LIVE_LOAD_VALUE)
            _dead = float(_dl_v) if str(input_dict.get(KEY_SL_DEAD_LOAD_MODE, "")) == "Custom" and _dl_v else 0.0
            _live = float(_ll_v) if str(input_dict.get(KEY_SL_LIVE_LOAD_MODE, "")) == "Custom" and _ll_v else 0.0
            _res  = IRC6_2017.cl_218_5_1(zone=f"Zone {_z}", soil_type=_st, dead_load_kN=_dead,
                        live_load_kN=_live, period_T=float(_tp) if _tp else None,
                        damping_percent=float(_damp))
            if not sl_zone_factor:
                sl_zone_factor = _res.get("Z")
            if not sl_spectral:
                sl_spectral    = _res.get("Sa_g_adjusted")
            if not sl_ah:
                sl_ah          = _res.get("Ah")
            if not sl_av:
                sl_av          = round(_res.get("Ah", 0) * 2 / 3, 4)
        except Exception:
            pass

    def _sl(v, unit=""):
        return f"{float(v):.4f}{unit}" if v not in (None, "") else "N/A"

    # Table 3.6 — Temperature: compute effective bridge temp range from shade temps
    tl_temp_min = tl_temp_max = tl_rise = tl_fall = "N/A"
    try:
        _tmax = input_dict.get(KEY_TL_HIGHEST_MAX_TEMP) or input_dict.get('shade_temp_max')
        _tmin = input_dict.get(KEY_TL_LOWEST_MIN_TEMP)  or input_dict.get('shade_temp_min')
        if _tmax and _tmin:
            _res    = IRC6_2017.cl_215_2_effective_bridge_temperature(
                          float(_tmax), float(_tmin), 'metallic', False)
            _bt_min = _res.get('T_min', 0)
            _bt_max = _res.get('T_max', 0)
            _mean   = (_bt_max + _bt_min) / 2.0
            tl_temp_min = f"{_bt_min:.2f}"
            tl_temp_max = f"{_bt_max:.2f}"
            tl_rise     = f"{_bt_max - _mean:.2f}"
            tl_fall     = f"{_mean - _bt_min:.2f}"
    except Exception:
        pass

    # --- Table 3.7: Load Combinations (dynamically generated from IRC 6) ---
    _LOAD_LABEL_MAP = {
        'dead_load':         'DL',
        'surfacing':         'SIDL',
        'live_load':         'LL',
        'wind_load':         'WL',
        'thermal_load':      'TL',
        'vehicle_collision': 'VC',
        'barge_impact':      'BI',
        'floating_bodies':   'FB',
        'seismic':           'EQ',
    }

    def _fmt_factors(factors):
        """Format a factors dict into a compact load-case string for the table."""
        parts = []
        for load, val in factors.items():
            label = _LOAD_LABEL_MAP.get(load, load.upper())
            if isinstance(val, dict):  # permanent load with adding/relieving
                add = val.get('adding')
                rel = val.get('relieving')
                add_s = f"{add:.2f}" if add is not None else '--'
                rel_s = f"{rel:.2f}" if rel is not None else '--'
                parts.append(f"{label}({add_s}/{rel_s})")
            else:
                if val is None:
                    continue  # skip N/A factors
                parts.append(f"{label}({val:.2f})")
        return ' + '.join(parts)

    uls_combos = IRC6_2017.uls_load_combinations()
    sls_combos = IRC6_2017.sls_load_combinations()
    lc_rows = []
    for i, combo in enumerate(uls_combos, start=1):
        cases = _fmt_factors(combo['factors'])
        lc_rows.append(
            f"ULS-{i:02d}" + r" & " + cases + r" \\[6pt]" + "\n"
            + r"\hline"
        )
    for i, combo in enumerate(sls_combos, start=1):
        cases = _fmt_factors(combo['factors'])
        lc_rows.append(
            f"SLS-{i:02d}" + r" & " + cases + r" \\[6pt]" + "\n"
            + r"\hline"
        )

    lc_rows_str = "\n".join(lc_rows)

    return r"""
\chapter{Loads and Load Combinations}

This section summarizes all loads applied to the bridge and the load combinations considered for analysis and design.

\vspace{1em}
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
\caption{\textbf{Dead Load -- Self Weight}}\\
\hline
\textbf{parameter} & \textbf{value} \\
\hline
\endfirsthead
\hline
\textbf{parameter} & \textbf{value} \\
\hline
\endhead
\textnormal{Steel Self-Weight Applied} & """ + (_render_value(input_dict, KEY_MATERIAL_GIRDER_DENSITY, ' kN/m\\textsuperscript{3}')) + r""" \\[6pt]
\hline
\textnormal{Concrete Deck Weight} & """ + (_render_value(input_dict, KEY_MATERIAL_DECK_DENSITY, ' kN/m\\textsuperscript{3}')) + r""" \\[6pt]
\hline
\textnormal{Self-Weight Factor} & """ + (_render_value(input_dict, KEY_PL_SELF_WEIGHT_FACTOR)) + r""" \\[6pt]
\hline
\end{longtable}

\vspace{1em}
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
\caption{\textbf{Dead Load for Surfacing (DW)}}\\
\hline
\textbf{parameter} & \textbf{value} \\
\hline
\endfirsthead
\hline
\textbf{parameter} & \textbf{value} \\
\hline
\endhead
\textnormal{Wearing Course Load} & """ + (_render_value(input_dict, KEY_WC_MATERIAL)) + r""" x """ + (_render_value(input_dict, KEY_WC_THICKNESS)) + r""" \\[6pt]
\hline
\textnormal{Additional SIDL (Crash Barrier)} & """ + (_render_value(input_dict, KEY_CB_LOAD)) + r""" kN/m per barrier \\[6pt]
\hline
\textnormal{Railing Load} & """ + (_render_value(input_dict, KEY_RL_LOAD_VALUE)) + r""" kN/m\sdstar{} \\[6pt]
\hline
\end{longtable}

\vspace{1em}
{\small
\setlength{\tabcolsep}{2.5pt}
""" + t33_tex + r"""
}

""" + t33_summary_tex + r"""

\vspace{1em}
""" + t34_tex + r"""

\vspace{1em}
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
\caption{\textbf{Wind Load (WL) --- per IRC 6}}\\
\hline
\textbf{parameter} & \textbf{value} \\
\hline
\endfirsthead
\hline
\textbf{parameter} & \textbf{value} \\
\hline
\endhead
\textnormal{Basic Wind Speed, Vb} & """ + (_render_value(input_dict,'wind_speed', ' m/s')) + r""" [from Project Location] \\[6pt]
\hline
\textnormal{Terrain Type} & """ + (_render_value(input_dict, KEY_WL_TERRAIN_TYPE)) + r""" \\[6pt]
\hline
\textnormal{Average Exposed Height, H (m)} & """ + (_render_value(input_dict, KEY_WL_AVG_EXPOSED_HEIGHT, ' m')) + r""" \\[6pt]
\hline
\textnormal{Hourly Mean Wind Speed, Vz} & """ + (_render_value(input_dict, KEY_WL_HOURLY_MEAN_WIND, ' m/s')) + r""" \\[6pt]
\hline
\textnormal{Hourly Wind Pressure, Pz} & """ + (_render_value(input_dict, KEY_WL_HOURLY_WIND_PRESSURE, ' N/m\\textsuperscript{2}')) + r""" \\[6pt]
\hline
\textnormal{Transverse Wind Force} & """ + (_render_value(input_dict, KEY_WL_TRANSVERSE_WIND_FORCE, ' kN')) + r""" \\[6pt]
\hline
\textnormal{Longitudinal Wind Force} & """ + (_render_value(input_dict, KEY_WL_LONGITUDINAL_WIND_FORCE, ' kN')) + r""" \\[6pt]
\hline
\textnormal{Vertical Wind Force} & """ + (_render_value(input_dict, KEY_WL_VERTICAL_WIND_FORCE, ' kN')) + r""" \\[6pt]
\hline
\end{longtable}

\vspace{1em}
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
\caption{\textbf{Earthquake Load (EL) --- per IRC 6}}\\
\hline
\textbf{parameter} & \textbf{value} \\
\hline
\endfirsthead
\hline
\textbf{parameter} & \textbf{value} \\
\hline
\endhead
\textnormal{Seismic Zone} & """ + (_render_value(input_dict,'seismic_zone')) + r""" [from Project Location] \\[6pt]
\hline
\textnormal{Zone Factor, Z} & """ + (_render_value(input_dict, KEY_SL_ZONE_FACTOR)) + r""" \\[6pt]
\hline
\textnormal{Importance Factor, I} & """ + (_render_value(input_dict, KEY_SL_IMPORTANCE_FACTOR)) + r""" \\[6pt]
\hline
\textnormal{Type of Soil} & """ + (_render_value(input_dict, KEY_SL_SOIL_TYPE)) + r""" \\[6pt]
\hline
\textnormal{Sa/g} & """ + (_render_value(input_dict, KEY_SL_SPECTRAL_COEFF)) + r""" \\[6pt]
\hline
\textnormal{Horizontal Seismic Coefficient, Ah} & """ + (_render_value(input_dict, KEY_SL_HORIZONTAL_COEFF)) + r""" \\[6pt]
\hline
\textnormal{Vertical Seismic Coefficient, Av} & """ + (_render_value(input_dict, KEY_SL_VERTICAL_COEFF)) + r""" \\[6pt]
\hline
\textnormal{Horizontal Seismic Force (longitudinal)} & """ + '' + r""" kN \\[6pt]
\hline
\textnormal{Horizontal Seismic Force (transverse)} & """ + '' + r""" kN \\[6pt]
\hline
\end{longtable}

\vspace{1em}
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
\caption{\textbf{Temperature Load (TL) --- per IRC 6}}\\
\hline
\textbf{parameter} & \textbf{value} \\
\hline
\endfirsthead
\hline
\textbf{parameter} & \textbf{value} \\
\hline
\endhead
\textnormal{Maximum Shade Temperature} & """ + (_render_value(input_dict,'shade_temp_max')) + r""" $^\circ$C \\[6pt]
\hline
\textnormal{Minimum Shade Temperature} & """ + (_render_value(input_dict,'shade_temp_min')) + r""" $^\circ$C \\[6pt]
\hline
\textnormal{Effective Bridge Temp. Range} & """ + (_render_value(input_dict, KEY_TL_BRIDGE_TEMP_MIN)) + r""" to """ + (_render_value(input_dict, KEY_TL_BRIDGE_TEMP_MAX)) + r""" $^\circ$C \\[6pt]
\hline
\textnormal{Temperature Rise / Fall for Design} & +""" + (_render_value(input_dict, KEY_TL_TEMP_RISE)) + r""" $^\circ$C / \textminus{}""" + (_render_value(input_dict, KEY_TL_TEMP_FALL)) + r""" $^\circ$C \\[6pt]
\hline
\end{longtable}

\vspace{1em}
\begin{longtable}{|C{4.0cm}|p{11.5cm}|}
\caption{\textbf{Load Combinations}}\\
\hline
\textbf{Combination ID} & \textbf{Load Cases} \\[6pt]
\hline
\endfirsthead
\hline
\textbf{Combination ID} & \textbf{Load Cases} \\[6pt]
\hline
\endhead
""" + lc_rows_str + r"""
\end{longtable}

\noindent\textit{Note: All IRC 6 load combinations are auto-generated by OsdagBridge. User-defined custom combinations, if any, are appended.}
"""



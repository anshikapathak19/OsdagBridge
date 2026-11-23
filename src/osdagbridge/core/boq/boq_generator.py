# =============================================================================
# OsdagBridge — BOQ (Bill of Quantities) Generator
# =============================================================================

import logging
import math
import sqlite3
from pathlib import Path
from typing import Any

from osdagbridge.core.utils.common import (
    KEY_SPAN,
    KEY_TS_NO_OF_GIRDERS,
    KEY_TS_DECK_THICKNESS,
    KEY_TS_GIRDER_SPACING,
    KEY_MP_GIRDER_DEPTH,
    KEY_MP_CB_TOP_CHORD,
    KEY_MP_CB_BOTTOM_CHORD,
    KEY_MP_ED_TYPE,
    KEY_MP_ED_BRACING_TYPE,
    KEY_MP_ED_BRACING_SECTION_DESIGNATION,
    KEY_MP_ED_IS_SECTION,
    KEY_MP_ED_TOP_CHORD,
    KEY_MP_ED_BOTTOM_CHORD,
    KEY_MP_ED_TOTAL_DEPTH,
    KEY_MP_ED_WEB_THICKNESS,
    KEY_MP_ED_TOP_FLANGE_WIDTH,
    KEY_MP_ED_BOTTOM_FLANGE_WIDTH,
    KEY_MP_ED_TOP_FLANGE_THICKNESS,
    KEY_MP_ED_BOTTOM_FLANGE_THICKNESS,
    KEY_TD_ED_PROP_A,
    KEY_TD_ED_PROP_M,
    KEY_TD_ED_TOP_CHORD_PROP_A,
    KEY_TD_ED_BOTTOM_CHORD_PROP_A,
)

logger = logging.getLogger("osdagbridge.core.boq_generator")


_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "ResourceFiles" / "Intg_osdag.sqlite"


def _query_steel_section(designation: str) -> dict | None:
    """Query Osdag sqlite database for steel section properties (Beams, Channels, Angles)."""
    if not designation or not _DB_PATH.exists():
        return None
    des = designation.strip()
    if des.startswith("2-"):
        des = des[2:].strip()
    candidates = [des]
    if des.startswith("IS"):
        candidates.append(des[2:].strip())
    if des.startswith("ISA"):
        candidates.append(des[3:].strip())

    try:
        con = sqlite3.connect(_DB_PATH)
        cur = con.cursor()
        for tbl in ("Beams", "Channels", "EqualAngle", "UnequalAngle"):
            for c in candidates:
                cur.execute(f"SELECT Designation, Mass, Area FROM {tbl} WHERE Designation = ? OR LOWER(Designation) = LOWER(?)", (c, c))
                row = cur.fetchone()
                if not row:
                    c_ns = c.replace(" ", "")
                    sql = f"SELECT Designation, Mass, Area FROM {tbl} WHERE REPLACE(Designation, ' ', '') = ? OR LOWER(REPLACE(Designation, ' ', '')) = LOWER(?)"
                    cur.execute(sql, (c_ns, c_ns))
                    row = cur.fetchone()
                if row:
                    con.close()
                    return {
                        "designation": row[0],
                        "Mass": float(row[1]) if row[1] is not None else 0.0,
                        "Area": float(row[2]) if row[2] is not None else 0.0,
                    }
        con.close()
    except Exception:
        pass
    return None


def resolve_girder_value(source: dict, base_key: str, i: int = 0) -> Any:
    """Resolve a girder property from an input/output dict, tolerating both the
    per-girder dynamic key scheme and the legacy scalar key.
    """
    candidates = [
        f"{base_key}.G{i + 1}.M1",
        base_key,
        f"{base_key}.G1.M1"
    ]
    for key in candidates:
        if key in source:
            return source[key]
    raise KeyError(base_key)


def calculate_material_quantities(inputs: dict, outputs: dict) -> dict:
    """Calculate quantities (steel tonnage, concrete volume, rebar, studs)
    needed for the material take-off summary (Chapter 7).
    """
    quantities = {
        "steel_girders_vol_formula": r"\placeholder{Area $\times$ Length}",
        "steel_girders_qty": "N.A.",
        "steel_girders_vol_total": "N.A.",
        "steel_girders_wt_single": "N.A.",
        "steel_girders_wt_total": "N.A.",
        
        "steel_bracing_vol_formula": r"\placeholder{Area $\times$ Length}",
        "steel_bracing_qty": "N.A.",
        "steel_bracing_vol_total": "N.A.",
        "steel_bracing_wt_single": "N.A.",
        "steel_bracing_wt_total": "N.A.",

        "bracing_top_vol_formula": r"\placeholder{Area $\times$ Length}",
        "bracing_top_qty": "N.A.",
        "bracing_top_vol_total": "N.A.",
        "bracing_top_wt_single": "N.A.",
        "bracing_top_wt_total": "N.A.",

        "bracing_bot_vol_formula": r"\placeholder{Area $\times$ Length}",
        "bracing_bot_qty": "N.A.",
        "bracing_bot_vol_total": "N.A.",
        "bracing_bot_wt_single": "N.A.",
        "bracing_bot_wt_total": "N.A.",

        "bracing_diag_vol_formula": r"\placeholder{Area $\times$ Length}",
        "bracing_diag_qty": "N.A.",
        "bracing_diag_vol_total": "N.A.",
        "bracing_diag_wt_single": "N.A.",
        "bracing_diag_wt_total": "N.A.",

        "end_diaphragm_vol_formula": r"\placeholder{Area $\times$ Length}",
        "end_diaphragm_qty": "N.A.",
        "end_diaphragm_vol_total": "N.A.",
        "end_diaphragm_wt_single": "N.A.",
        "end_diaphragm_wt_total": "N.A.",
        
        "concrete_deck_vol_formula": r"\placeholder{Width $\times$ Thickness $\times$ Length}",
        "concrete_deck_qty": "N.A.",
        "concrete_deck_vol_total": "N.A.",
        "concrete_deck_wt_single": "N.A.",
        "concrete_deck_wt_total": "N.A.",
        
        "rebar_deck_vol_formula": r"\placeholder{Area $\times$ Length}",
        "rebar_deck_qty": "N.A.",
        "rebar_deck_vol_total": "N.A.",
        "rebar_deck_wt_single": "N.A.",
        "rebar_deck_wt_total": "N.A.",
        
        "shear_studs_vol_formula": r"\placeholder{Area $\times$ Height}",
        "shear_studs_qty": "N.A.",
        "shear_studs_vol_total": "N.A.",
        "shear_studs_wt_single": "N.A.",
        "shear_studs_wt_total": "N.A.",

        "crash_barrier_vol_formula": r"\placeholder{Area $\times$ Length}",
        "crash_barrier_qty": "N.A.",
        "crash_barrier_vol_total": "N.A.",
        "crash_barrier_wt_single": "N.A.",
        "crash_barrier_wt_total": "N.A.",
    }
    try:
        span_val = inputs.get(KEY_SPAN)
        n_girders_val = inputs.get(KEY_TS_NO_OF_GIRDERS)
        if span_val is None or n_girders_val is None:
            return quantities
            
        try:
            span = float(span_val)
            n_girders = int(n_girders_val)
        except Exception:
            return quantities

        if span <= 0 or n_girders <= 0:
            return quantities

        # 1. Concrete deck volume (Cu.m) and Weight (MT)
        overall_width_val = inputs.get("typical_section.overall_bridge_width")
        deck_thickness_val = inputs.get(KEY_TS_DECK_THICKNESS)
        
        if overall_width_val is not None and deck_thickness_val is not None:
            try:
                overall_width = float(overall_width_val)
                deck_thickness = float(deck_thickness_val) / 1000.0  # mm to m
                if overall_width > 0 and deck_thickness > 0:
                    concrete_vol = span * overall_width * deck_thickness
                    quantities["concrete_deck_vol_formula"] = f"${overall_width:.2f}\\text{{ m}} \\times {deck_thickness:.2f}\\text{{ m}} \\times {span:.2f}\\text{{ m}} = {concrete_vol:.2f}\\text{{ m}}^3$"
                    quantities["concrete_deck_qty"] = "1"
                    quantities["concrete_deck_vol_total"] = f"{concrete_vol:.2f}"
                    quantities["concrete_deck_wt_single"] = f"{(concrete_vol * 2.5):.2f}"
                    quantities["concrete_deck_wt_total"] = f"{(concrete_vol * 2.5):.2f}"

                    # 2. Reinforcement Steel (Cu.m) and Weight (MT)
                    rebar_wt_kg = concrete_vol * 120.0
                    rebar_vol = rebar_wt_kg / 7850.0
                    rebar_area = rebar_vol / span if span > 0 else 0.0
                    quantities["rebar_deck_vol_formula"] = f"${rebar_area:.6f}\\text{{ m}}^2 \\times {span:.2f}\\text{{ m}} = {rebar_vol:.5f}\\text{{ m}}^3$"
                    quantities["rebar_deck_qty"] = "1"
                    quantities["rebar_deck_vol_total"] = f"{rebar_vol:.2f}"
                    
                    rebar_wt_mt = rebar_wt_kg / 1000.0
                    quantities["rebar_deck_wt_single"] = f"{rebar_wt_mt:.2f}"
                    quantities["rebar_deck_wt_total"] = f"{rebar_wt_mt:.2f}"
            except Exception:
                pass

        # 3. Steel Girders (Cu.m) and Weight (MT)
        girder_area = 0.0
        try:
            # Resolve representative girder sectional area
            girder_area = float(resolve_girder_value(inputs, "member_properties.girder_details.section_properties.area", 0))
        except Exception:
            pass

        # Calculate from inputs if not in properties
        if girder_area <= 0:
            try:
                dw_val = resolve_girder_value(inputs, "member_properties.girder_details.section_input.web_depth", 0)
                tw_val = resolve_girder_value(inputs, "member_properties.girder_details.section_input.web_thickness", 0)
                bft_val = resolve_girder_value(inputs, "member_properties.girder_details.section_input.top_flange_width", 0)
                tft_val = resolve_girder_value(inputs, "member_properties.girder_details.section_input.top_flange_thickness", 0)
                bfb_val = resolve_girder_value(inputs, "member_properties.girder_details.section_input.bottom_flange_width", 0)
                tfb_val = resolve_girder_value(inputs, "member_properties.girder_details.section_input.bottom_flange_thickness", 0)
                
                if (dw_val is not None and tw_val is not None and 
                    bft_val is not None and tft_val is not None and 
                    bfb_val is not None and tfb_val is not None):
                    
                    dw = float(dw_val)
                    tw = float(tw_val)
                    bft = float(bft_val)
                    tft = float(tft_val)
                    bfb = float(bfb_val)
                    tfb = float(tfb_val)
                    
                    # All dimensions in mm, compute in m²
                    girder_area = ((dw * tw) + (bft * tft) + (bfb * tfb)) / 1e6
            except Exception:
                pass

        total_girder_mass = 0.0
        if girder_area > 0:
            girder_vol = girder_area * span
            quantities["steel_girders_vol_formula"] = f"${girder_area:.5f}\\text{{ m}}^2 \\times {span:.2f}\\text{{ m}} = {girder_vol:.5f}\\text{{ m}}^3$"
            quantities["steel_girders_qty"] = str(n_girders)
            
            # calculate tonnage / volume
            for gi in range(n_girders):
                try:
                    mass_per_m = float(resolve_girder_value(inputs, "member_properties.girder_details.section_properties.mass", gi))
                    total_girder_mass += mass_per_m * span
                except Exception:
                    total_girder_mass += girder_area * span * 7850.0
            
            girder_total_vol = n_girders * girder_vol
            quantities["steel_girders_vol_total"] = f"{girder_total_vol:.2f}"
            
            single_girder_wt = (total_girder_mass / n_girders) / 1000.0
            total_girder_wt = total_girder_mass / 1000.0
            quantities["steel_girders_wt_single"] = f"{single_girder_wt:.2f}"
            quantities["steel_girders_wt_total"] = f"{total_girder_wt:.2f}"

        # 4. Shear Stud Connectors (Cu.m) and Weight (MT)
        spacing_mm = 0.0
        studs_per_sec = 0
        stud_d = 0.0
        stud_h_mm = 0.0

        spacing_val = outputs.get("steeldesign.details.shear.longitudinal_spacing")
        studs_val = outputs.get("steeldesign.details.shear.studs_per_section")
        stud_d_val = outputs.get("steeldesign.details.shear.diameter") or inputs.get("design_options.shear_studs.diameter")
        stud_h_val = outputs.get("steeldesign.details.shear.height") or inputs.get("design_options.shear_studs.height")

        if spacing_val is not None and studs_val is not None and stud_d_val is not None and stud_h_val is not None:
            try:
                spacing_mm = float(spacing_val)
                studs_per_sec = int(studs_val)
                stud_d = float(stud_d_val)
                stud_h_mm = float(stud_h_val)
            except Exception:
                pass

        if spacing_mm > 0.0 and studs_per_sec > 0 and stud_d > 0.0 and stud_h_mm > 0.0:
            stud_h = stud_h_mm / 1000.0  # mm to m
            n_sections = int(span * 1000.0 / spacing_mm) + 1
            total_studs = n_girders * studs_per_sec * n_sections
            
            stud_area = (3.14159 * (stud_d / 1000.0) ** 2) / 4.0
            stud_vol = stud_area * stud_h
            quantities["shear_studs_vol_formula"] = f"${stud_area:.6f}\\text{{ m}}^2 \\times {stud_h:.3f}\\text{{ m}} = {stud_vol:.6f}\\text{{ m}}^3$"
            quantities["shear_studs_qty"] = str(total_studs)
            
            studs_total_vol = total_studs * stud_vol
            quantities["shear_studs_vol_total"] = f"{studs_total_vol:.2f}"
            
            # density of steel = 7850 kg/m^3 = 7.85 tonnes/m^3
            single_stud_wt = stud_vol * 7.85
            total_studs_wt = studs_total_vol * 7.85
            quantities["shear_studs_wt_single"] = f"{single_stud_wt:.6f}"
            quantities["shear_studs_wt_total"] = f"{total_studs_wt:.3f}"
        else:
            quantities["shear_studs_vol_formula"] = "N.A."
            quantities["shear_studs_qty"] = "N.A."
            quantities["shear_studs_vol_total"] = "N.A."
            quantities["shear_studs_wt_single"] = "N.A."
            quantities["shear_studs_wt_total"] = "N.A."

        # 5. Steel Bracings (Cu.m) and Weight (MT)
        # Process intermediate cross bracings dynamically across all girder bays:
        # Diagonal:     transverse_member_design.cb.section_properties.bracing.{pair_id}.A (cm²)
        # Top Chord:    transverse_member_design.cb.section_properties.top_chord.{pair_id}.A (cm²)
        # Bottom Chord: transverse_member_design.cb.section_properties.bottom_chord.{pair_id}.A (cm²)
        # Chords have length = girder spacing; diagonals have length = diagonal_length_m.

        spacing_val = inputs.get(KEY_TS_GIRDER_SPACING)
        spacing = 0.0
        if spacing_val is not None:
            try:
                spacing = float(spacing_val)
            except Exception:
                pass

        cb_forces = outputs.get("crossbracing_forces_dict", {}) or {}
        cb_geom = cb_forces.get("geometry", {}) or {}

        # Frame height for geometry calculation if needed
        D_girder = 0.0
        try:
            D_girder = float(resolve_girder_value(inputs, KEY_MP_GIRDER_DEPTH, 0))
        except Exception:
            pass
        if D_girder <= 0:
            try:
                dw = float(resolve_girder_value(inputs, "member_properties.girder_details.section_input.web_depth", 0) or 0)
                tft = float(resolve_girder_value(inputs, "member_properties.girder_details.section_input.top_flange_thickness", 0) or 0)
                tfb = float(resolve_girder_value(inputs, "member_properties.girder_details.section_input.bottom_flange_thickness", 0) or 0)
                if dw > 0:
                    D_girder = (dw + tft + tfb) / 1000.0
            except Exception:
                pass
        if D_girder <= 0:
            D_girder = 1.65
        h_frame = D_girder * 0.85

        bracing_len_val = cb_geom.get("diagonal_length_m")
        bracing_len = 0.0
        if bracing_len_val is not None:
            try:
                bracing_len = float(bracing_len_val)
            except Exception:
                pass
        if bracing_len <= 0 and spacing > 0 and h_frame > 0:
            bracing_len = math.sqrt(spacing**2 + h_frame**2)

        cb_spacing_val = cb_geom.get("cb_spacing_m")
        cb_spacing = 0.0
        if cb_spacing_val is not None:
            try:
                cb_spacing = float(cb_spacing_val)
            except Exception:
                pass
        if cb_spacing > 0.0:
            n_panels = max(1, round(span / cb_spacing) - 1)
        else:
            n_panels = max(3, int(span / 5.0))

        # Check whether intermediate cross bracing is present in design outputs
        # Note: Do not pull initial input trial sections from inputs as final design!
        has_cb_outputs = any("transverse_member_design.cb." in k for k in outputs)

        if has_cb_outputs and spacing > 0.0 and bracing_len > 0.0 and n_girders > 1:
            n_bays = n_girders - 1

            # 5a. Top Chord
            tc_valid = True
            tc_enabled_any = False
            tc_members_total = 0
            tc_vol_total = 0.0
            tc_wt_total = 0.0
            tc_areas = []

            for i in range(1, n_girders):
                pair_id = f"G{i}G{i+1}"
                tc_enabled = True
                for k in (
                    f"member_properties.cross_bracing_details.top_chord.{pair_id}",
                    "member_properties.cross_bracing_details.top_chord",
                    f"{KEY_MP_CB_TOP_CHORD}.{pair_id}.B{i}M1",
                    KEY_MP_CB_TOP_CHORD,
                ):
                    v = outputs.get(k) if k in outputs else inputs.get(k)
                    if v is not None:
                        tc_enabled = str(v).strip().lower() not in ("no", "false", "0")
                        break
                if tc_enabled:
                    tc_enabled_any = True
                    tc_a = None
                    for k in (
                        f"transverse_member_design.cb.section_properties.top_chord.{pair_id}.A",
                        "transverse_member_design.cb.section_properties.top_chord.G1G2.A",
                        "transverse_member_design.cb.section_properties.top_chord.A",
                    ):
                        v = outputs.get(k)
                        if v is not None:
                            try:
                                val = float(v) / 10000.0
                                if val > 0:
                                    tc_a = val
                                    break
                            except Exception:
                                pass
                    if tc_a is None:
                        for k in (
                            f"transverse_member_design.cb.section_properties.top_chord.{pair_id}.M",
                            "transverse_member_design.cb.section_properties.top_chord.G1G2.M",
                        ):
                            v = outputs.get(k)
                            if v is not None:
                                try:
                                    val = float(v) / 7850.0
                                    if val > 0:
                                        tc_a = val
                                        break
                                except Exception:
                                    pass
                    if tc_a is None:
                        for k in (
                            f"transverse_member_design.cb.section_properties.bracing.{pair_id}.A",
                            "transverse_member_design.cb.section_properties.bracing.G1G2.A",
                        ):
                            v = outputs.get(k)
                            if v is not None:
                                try:
                                    val = float(v) / 10000.0
                                    if val > 0:
                                        tc_a = val
                                        break
                                except Exception:
                                    pass
                    if tc_a is not None and tc_a > 0:
                        tc_qty = n_panels
                        vol_bay = tc_qty * tc_a * spacing
                        tc_vol_total += vol_bay
                        tc_wt_total += vol_bay * 7.85
                        tc_members_total += tc_qty
                        tc_areas.append((tc_a, tc_qty))
                    else:
                        tc_valid = False

            if tc_enabled_any and tc_valid and tc_members_total > 0:
                rep_area = tc_vol_total / (tc_members_total * spacing)
                single_vol = tc_vol_total / tc_members_total
                single_wt = tc_wt_total / tc_members_total
                all_same = all(abs(a - tc_areas[0][0]) < 1e-9 for a, _ in tc_areas)
                if all_same:
                    quantities["bracing_top_vol_formula"] = (
                        f"${tc_areas[0][0]:.5f}\\text{{ m}}^2 \\times {spacing:.2f}\\text{{ m}} = {single_vol:.5f}\\text{{ m}}^3$"
                    )
                else:
                    quantities["bracing_top_vol_formula"] = (
                        f"${rep_area:.5f}\\text{{ m}}^2 \\times {spacing:.2f}\\text{{ m (avg)}} = {single_vol:.5f}\\text{{ m}}^3$"
                    )
                quantities["bracing_top_qty"] = str(tc_members_total)
                quantities["bracing_top_vol_total"] = f"{tc_vol_total:.2f}"
                quantities["bracing_top_wt_single"] = f"{single_wt:.4f}"
                quantities["bracing_top_wt_total"] = f"{tc_wt_total:.2f}"
            elif not tc_enabled_any:
                quantities["bracing_top_vol_formula"] = "N.A."
                quantities["bracing_top_qty"] = "0"
                quantities["bracing_top_vol_total"] = "0.00"
                quantities["bracing_top_wt_single"] = "0.0000"
                quantities["bracing_top_wt_total"] = "0.00"
            else:
                quantities["bracing_top_vol_formula"] = "N.A."
                quantities["bracing_top_qty"] = "N.A."
                quantities["bracing_top_vol_total"] = "N.A."
                quantities["bracing_top_wt_single"] = "N.A."
                quantities["bracing_top_wt_total"] = "N.A."

            # 5b. Bottom Chord
            bc_valid = True
            bc_enabled_any = False
            bc_members_total = 0
            bc_vol_total = 0.0
            bc_wt_total = 0.0
            bc_areas = []

            for i in range(1, n_girders):
                pair_id = f"G{i}G{i+1}"
                bc_enabled = True
                for k in (
                    f"member_properties.cross_bracing_details.bottom_chord.{pair_id}",
                    "member_properties.cross_bracing_details.bottom_chord",
                    f"{KEY_MP_CB_BOTTOM_CHORD}.{pair_id}.B{i}M1",
                    KEY_MP_CB_BOTTOM_CHORD,
                ):
                    v = outputs.get(k) if k in outputs else inputs.get(k)
                    if v is not None:
                        bc_enabled = str(v).strip().lower() not in ("no", "false", "0")
                        break
                if bc_enabled:
                    bc_enabled_any = True
                    bc_a = None
                    for k in (
                        f"transverse_member_design.cb.section_properties.bottom_chord.{pair_id}.A",
                        "transverse_member_design.cb.section_properties.bottom_chord.G1G2.A",
                        "transverse_member_design.cb.section_properties.bottom_chord.A",
                    ):
                        v = outputs.get(k)
                        if v is not None:
                            try:
                                val = float(v) / 10000.0
                                if val > 0:
                                    bc_a = val
                                    break
                            except Exception:
                                pass
                    if bc_a is None:
                        for k in (
                            f"transverse_member_design.cb.section_properties.bottom_chord.{pair_id}.M",
                            "transverse_member_design.cb.section_properties.bottom_chord.G1G2.M",
                        ):
                            v = outputs.get(k)
                            if v is not None:
                                try:
                                    val = float(v) / 7850.0
                                    if val > 0:
                                        bc_a = val
                                        break
                                except Exception:
                                    pass
                    if bc_a is None:
                        for k in (
                            f"transverse_member_design.cb.section_properties.bracing.{pair_id}.A",
                            "transverse_member_design.cb.section_properties.bracing.G1G2.A",
                        ):
                            v = outputs.get(k)
                            if v is not None:
                                try:
                                    val = float(v) / 10000.0
                                    if val > 0:
                                        bc_a = val
                                        break
                                except Exception:
                                    pass
                    if bc_a is not None and bc_a > 0:
                        bc_qty = n_panels
                        vol_bay = bc_qty * bc_a * spacing
                        bc_vol_total += vol_bay
                        bc_wt_total += vol_bay * 7.85
                        bc_members_total += bc_qty
                        bc_areas.append((bc_a, bc_qty))
                    else:
                        bc_valid = False

            if bc_enabled_any and bc_valid and bc_members_total > 0:
                rep_area = bc_vol_total / (bc_members_total * spacing)
                single_vol = bc_vol_total / bc_members_total
                single_wt = bc_wt_total / bc_members_total
                all_same = all(abs(a - bc_areas[0][0]) < 1e-9 for a, _ in bc_areas)
                if all_same:
                    quantities["bracing_bot_vol_formula"] = (
                        f"${bc_areas[0][0]:.5f}\\text{{ m}}^2 \\times {spacing:.2f}\\text{{ m}} = {single_vol:.5f}\\text{{ m}}^3$"
                    )
                else:
                    quantities["bracing_bot_vol_formula"] = (
                        f"${rep_area:.5f}\\text{{ m}}^2 \\times {spacing:.2f}\\text{{ m (avg)}} = {single_vol:.5f}\\text{{ m}}^3$"
                    )
                quantities["bracing_bot_qty"] = str(bc_members_total)
                quantities["bracing_bot_vol_total"] = f"{bc_vol_total:.2f}"
                quantities["bracing_bot_wt_single"] = f"{single_wt:.4f}"
                quantities["bracing_bot_wt_total"] = f"{bc_wt_total:.2f}"
            elif not bc_enabled_any:
                quantities["bracing_bot_vol_formula"] = "N.A."
                quantities["bracing_bot_qty"] = "0"
                quantities["bracing_bot_vol_total"] = "0.00"
                quantities["bracing_bot_wt_single"] = "0.0000"
                quantities["bracing_bot_wt_total"] = "0.00"
            else:
                quantities["bracing_bot_vol_formula"] = "N.A."
                quantities["bracing_bot_qty"] = "N.A."
                quantities["bracing_bot_vol_total"] = "N.A."
                quantities["bracing_bot_wt_single"] = "N.A."
                quantities["bracing_bot_wt_total"] = "N.A."

            # 5c. Diagonal
            diag_valid = True
            diag_members_total = 0
            diag_vol_total = 0.0
            diag_wt_total = 0.0
            diag_areas = []

            for i in range(1, n_girders):
                pair_id = f"G{i}G{i+1}"
                diag_a = None
                for k in (
                    f"transverse_member_design.cb.section_properties.bracing.{pair_id}.A",
                    "transverse_member_design.cb.section_properties.bracing.G1G2.A",
                    "transverse_member_design.cb.section_properties.bracing.A",
                ):
                    v = outputs.get(k)
                    if v is not None:
                        try:
                            val = float(v) / 10000.0
                            if val > 0:
                                diag_a = val
                                break
                        except Exception:
                            pass
                if diag_a is None:
                    for k in (
                        f"transverse_member_design.cb.section_properties.bracing.{pair_id}.M",
                        "transverse_member_design.cb.section_properties.bracing.G1G2.M",
                    ):
                        v = outputs.get(k)
                        if v is not None:
                            try:
                                val = float(v) / 7850.0
                                if val > 0:
                                    diag_a = val
                                    break
                            except Exception:
                                pass
                if diag_a is not None and diag_a > 0:
                    d_qty = 2 * n_panels
                    vol_bay = d_qty * diag_a * bracing_len
                    diag_vol_total += vol_bay
                    diag_wt_total += vol_bay * 7.85
                    diag_members_total += d_qty
                    diag_areas.append((diag_a, d_qty))
                else:
                    diag_valid = False

            if diag_valid and diag_members_total > 0:
                rep_area = diag_vol_total / (diag_members_total * bracing_len)
                single_vol = diag_vol_total / diag_members_total
                single_wt = diag_wt_total / diag_members_total
                all_same = all(abs(a - diag_areas[0][0]) < 1e-9 for a, _ in diag_areas)
                if all_same:
                    quantities["bracing_diag_vol_formula"] = (
                        f"${diag_areas[0][0]:.5f}\\text{{ m}}^2 \\times {bracing_len:.2f}\\text{{ m}} = {single_vol:.5f}\\text{{ m}}^3$"
                    )
                else:
                    quantities["bracing_diag_vol_formula"] = (
                        f"${rep_area:.5f}\\text{{ m}}^2 \\times {bracing_len:.2f}\\text{{ m (avg)}} = {single_vol:.5f}\\text{{ m}}^3$"
                    )
                quantities["bracing_diag_qty"] = str(diag_members_total)
                quantities["bracing_diag_vol_total"] = f"{diag_vol_total:.2f}"
                quantities["bracing_diag_wt_single"] = f"{single_wt:.4f}"
                quantities["bracing_diag_wt_total"] = f"{diag_wt_total:.2f}"
            else:
                quantities["bracing_diag_vol_formula"] = "N.A."
                quantities["bracing_diag_qty"] = "N.A."
                quantities["bracing_diag_vol_total"] = "N.A."
                quantities["bracing_diag_wt_single"] = "N.A."
                quantities["bracing_diag_wt_total"] = "N.A."
        else:
            # Keep all bracing volumes, quantities, and weights as default placeholder "N.A."
            for prefix in ("bracing_top", "bracing_bot", "bracing_diag"):
                quantities[f"{prefix}_vol_formula"] = "N.A."
                quantities[f"{prefix}_qty"] = "N.A."
                quantities[f"{prefix}_vol_total"] = "N.A."
                quantities[f"{prefix}_wt_single"] = "N.A."
                quantities[f"{prefix}_wt_total"] = "N.A."

        # 5d. End Diaphragms (at Supports)
        # End diaphragms are located at both bridge supports (Support 1 and Support 2).
        # Total ends = 2; bays per end = (n_girders - 1).
        # Supports all configurations: Cross Bracing, Rolled Beam, Welded Beam.
        # CRITICAL SAFEGUARD: NO fallback to intermediate cross bracing (transverse_member_design.cb.*)
        # or initial input trial sections. If required final design properties are missing, report N.A.
        ed_type = ""
        for k in (
            "transverse_member_design.ed.type.G1G2",
            KEY_MP_ED_TYPE,
            "member_properties.end_diaphragm_type",
            f"{KEY_MP_ED_TYPE}.G1G2.E1M1",
        ):
            v = outputs.get(k) or inputs.get(k)
            if v:
                ed_type = str(v).strip()
                break
        if not ed_type:
            for k in outputs:
                if "transverse_member_design.ed." in k:
                    ed_type = "Cross Bracing"
                    break

        has_ed_outputs = any("transverse_member_design.ed." in k for k in outputs)
        is_welded_or_rolled = ed_type.lower() in ("welded beam", "welded", "rolled beam", "rolled")

        if ed_type and (has_ed_outputs or is_welded_or_rolled) and spacing > 0.0 and n_girders > 1:
            n_bays = n_girders - 1
            n_ends = 2

            total_ed_vol = 0.0
            total_ed_wt = 0.0
            total_ed_members = 0
            sum_len_area = 0.0
            sum_len = 0.0
            ed_valid = True

            if ed_type.lower() in ("cross bracing", "cross-bracing", "braced"):
                for i in range(1, n_girders):
                    pair_id = f"G{i}G{i+1}"
                    # Diagonals
                    b_type = str(
                        inputs.get(f"{KEY_MP_ED_BRACING_TYPE}.{pair_id}.E{i}M1")
                        or inputs.get(KEY_MP_ED_BRACING_TYPE)
                        or outputs.get(f"transverse_member_design.ed.bracing_type.{pair_id}")
                        or "X"
                    ).strip()
                    horiz_proj = spacing if b_type in ("X", "X-Bracing", "Cross") else spacing / 2.0
                    L_diag = math.sqrt(horiz_proj**2 + h_frame**2)

                    # Diagonal section area (cm² to m²) - from outputs only
                    diag_a = None
                    for k in (
                        f"transverse_member_design.ed.section_properties.end_diaphragm.{pair_id}.A",
                        "transverse_member_design.ed.section_properties.end_diaphragm.G1G2.A",
                        "transverse_member_design.ed.section_properties.end_diaphragm.A",
                    ):
                        val = outputs.get(k)
                        if val is not None:
                            try:
                                a = float(val) / 10000.0
                                if a > 0:
                                    diag_a = a
                                    break
                            except Exception:
                                pass
                    if diag_a is None:
                        for k in (
                            f"transverse_member_design.ed.section_properties.end_diaphragm.{pair_id}.M",
                            "transverse_member_design.ed.section_properties.end_diaphragm.G1G2.M",
                        ):
                            val = outputs.get(k)
                            if val is not None:
                                try:
                                    a = float(val) / 7850.0
                                    if a > 0:
                                        diag_a = a
                                        break
                                except Exception:
                                    pass

                    if diag_a is None or diag_a <= 0:
                        ed_valid = False
                        break

                    diag_count = 4 if b_type in ("X", "X-Bracing", "Cross") else 2 * n_ends
                    vol_diag = diag_count * diag_a * L_diag
                    total_ed_vol += vol_diag
                    total_ed_members += diag_count
                    sum_len_area += diag_count * diag_a * L_diag
                    sum_len += diag_count * L_diag

                    # Top Chord
                    tc_enabled = True
                    for k in (
                        f"{KEY_MP_ED_TOP_CHORD}.{pair_id}.E{i}M1",
                        KEY_MP_ED_TOP_CHORD,
                        f"transverse_member_design.ed.top_chord.{pair_id}",
                    ):
                        val = outputs.get(k) if k in outputs else inputs.get(k)
                        if val is not None:
                            tc_enabled = str(val).strip().lower() not in ("no", "false", "0")
                            break
                    if tc_enabled:
                        tc_a = None
                        for k in (
                            f"transverse_member_design.ed.section_properties.top_chord.{pair_id}.A",
                            "transverse_member_design.ed.section_properties.top_chord.G1G2.A",
                            "transverse_member_design.ed.section_properties.top_chord.A",
                        ):
                            val = outputs.get(k)
                            if val is not None:
                                try:
                                    a = float(val) / 10000.0
                                    if a > 0:
                                        tc_a = a
                                        break
                                except Exception:
                                    pass
                        if tc_a is None and diag_a is not None:
                            # In Osdag, if top chord does not have distinct section output,
                            # it shares the designed end-diaphragm bracing section
                            tc_a = diag_a
                        if tc_a is None or tc_a <= 0:
                            ed_valid = False
                            break
                        tc_count = n_ends
                        vol_tc = tc_count * tc_a * spacing
                        total_ed_vol += vol_tc
                        total_ed_members += tc_count
                        sum_len_area += tc_count * tc_a * spacing
                        sum_len += tc_count * spacing

                    # Bottom Chord
                    bc_enabled = True
                    for k in (
                        f"{KEY_MP_ED_BOTTOM_CHORD}.{pair_id}.E{i}M1",
                        KEY_MP_ED_BOTTOM_CHORD,
                        f"transverse_member_design.ed.bottom_chord.{pair_id}",
                    ):
                        val = outputs.get(k) if k in outputs else inputs.get(k)
                        if val is not None:
                            bc_enabled = str(val).strip().lower() not in ("no", "false", "0")
                            break
                    if bc_enabled:
                        bc_a = None
                        for k in (
                            f"transverse_member_design.ed.section_properties.bottom_chord.{pair_id}.A",
                            "transverse_member_design.ed.section_properties.bottom_chord.G1G2.A",
                            "transverse_member_design.ed.section_properties.bottom_chord.A",
                        ):
                            val = outputs.get(k)
                            if val is not None:
                                try:
                                    a = float(val) / 10000.0
                                    if a > 0:
                                        bc_a = a
                                        break
                                except Exception:
                                    pass
                        if bc_a is None and diag_a is not None:
                            bc_a = diag_a
                        if bc_a is None or bc_a <= 0:
                            ed_valid = False
                            break
                        bc_count = n_ends
                        vol_bc = bc_count * bc_a * spacing
                        total_ed_vol += vol_bc
                        total_ed_members += bc_count
                        sum_len_area += bc_count * bc_a * spacing
                        sum_len += bc_count * spacing

            elif ed_type.lower() in ("rolled beam", "rolled"):
                for i in range(1, n_girders):
                    pair_id = f"G{i}G{i+1}"
                    beam_a = None
                    for k in (
                        f"transverse_member_design.ed.section_properties.end_diaphragm.{pair_id}.A",
                        "transverse_member_design.ed.section_properties.end_diaphragm.G1G2.A",
                        "transverse_member_design.ed.section_properties.end_diaphragm.A",
                    ):
                        val = outputs.get(k)
                        if val is not None:
                            try:
                                a = float(val) / 10000.0
                                if a > 0:
                                    beam_a = a
                                    break
                            except Exception:
                                pass
                    if beam_a is None:
                        for k in (
                            f"transverse_member_design.ed.section_properties.end_diaphragm.{pair_id}.M",
                            "transverse_member_design.ed.section_properties.end_diaphragm.G1G2.M",
                        ):
                            val = outputs.get(k)
                            if val is not None:
                                try:
                                    a = float(val) / 7850.0
                                    if a > 0:
                                        beam_a = a
                                        break
                                except Exception:
                                    pass
                    if beam_a is None:
                        beam_des = ""
                        for k in (
                            f"transverse_member_design.ed.section_designation.{pair_id}",
                            "transverse_member_design.ed.section_designation.G1G2",
                            f"member_properties.end_diaphragm_details.bracing_section_designation.{pair_id}",
                            f"{KEY_MP_ED_BRACING_SECTION_DESIGNATION}.{pair_id}.E{i}M1",
                            KEY_MP_ED_BRACING_SECTION_DESIGNATION,
                            f"{KEY_MP_ED_IS_SECTION}.{pair_id}.E{i}M1",
                            KEY_MP_ED_IS_SECTION,
                        ):
                            v = outputs.get(k) or inputs.get(k)
                            if v:
                                beam_des = str(v).strip()
                                break
                        if beam_des:
                            sec_details = _query_steel_section(beam_des)
                            if sec_details and sec_details.get("Area", 0) > 0:
                                beam_a = float(sec_details["Area"]) / 10000.0  # cm² -> m²
                    if beam_a is not None and beam_a > 0:
                        beam_count = n_ends
                        vol_b = beam_count * beam_a * spacing
                        total_ed_vol += vol_b
                        total_ed_members += beam_count
                        sum_len_area += beam_count * beam_a * spacing
                        sum_len += beam_count * spacing
                    else:
                        ed_valid = False
                        break

            elif ed_type.lower() in ("welded beam", "welded"):
                for i in range(1, n_girders):
                    pair_id = f"G{i}G{i+1}"
                    w_area = None
                    for k in (
                        f"transverse_member_design.ed.section_properties.end_diaphragm.{pair_id}.A",
                        "transverse_member_design.ed.section_properties.end_diaphragm.G1G2.A",
                        "transverse_member_design.ed.section_properties.end_diaphragm.A",
                    ):
                        val = outputs.get(k)
                        if val is not None:
                            try:
                                a = float(val) / 10000.0
                                if a > 0:
                                    w_area = a
                                    break
                            except Exception:
                                pass
                    if w_area is None:
                        try:
                            _d = float(inputs.get(f"{KEY_MP_ED_TOTAL_DEPTH}.{pair_id}") or inputs.get(KEY_MP_ED_TOTAL_DEPTH) or 0.0)
                            _tw = float(inputs.get(f"{KEY_MP_ED_WEB_THICKNESS}.{pair_id}") or inputs.get(KEY_MP_ED_WEB_THICKNESS) or 0.0)
                            _tf_top = float(inputs.get(f"{KEY_MP_ED_TOP_FLANGE_THICKNESS}.{pair_id}") or inputs.get(KEY_MP_ED_TOP_FLANGE_THICKNESS) or 0.0)
                            _bf_top = float(inputs.get(f"{KEY_MP_ED_TOP_FLANGE_WIDTH}.{pair_id}") or inputs.get(KEY_MP_ED_TOP_FLANGE_WIDTH) or 0.0)
                            _tf_bot = float(inputs.get(f"{KEY_MP_ED_BOTTOM_FLANGE_THICKNESS}.{pair_id}") or inputs.get(KEY_MP_ED_BOTTOM_FLANGE_THICKNESS) or 0.0)
                            _bf_bot = float(inputs.get(f"{KEY_MP_ED_BOTTOM_FLANGE_WIDTH}.{pair_id}") or inputs.get(KEY_MP_ED_BOTTOM_FLANGE_WIDTH) or 0.0)
                            if _d > 0:
                                hw = _d - _tf_top - _tf_bot
                                a_total_mm2 = (_bf_top * _tf_top) + (_bf_bot * _tf_bot) + (hw * _tw)
                                w_area = a_total_mm2 / 1e6
                        except Exception:
                            pass
                    if w_area is not None and w_area > 0:
                        w_count = n_ends
                        vol_w = w_count * w_area * spacing
                        total_ed_vol += vol_w
                        total_ed_members += w_count
                        sum_len_area += w_count * w_area * spacing
                        sum_len += w_count * spacing
                    else:
                        ed_valid = False
                        break

            if ed_valid and total_ed_members > 0 and total_ed_vol > 0.0 and sum_len > 0:
                total_ed_wt = total_ed_vol * 7.85
                rep_area = sum_len_area / sum_len
                rep_len = sum_len / total_ed_members
                rep_vol = rep_area * rep_len
                single_ed_wt = total_ed_wt / total_ed_members
                if ed_type.lower() in ("cross bracing", "cross-bracing", "braced"):
                    quantities["end_diaphragm_vol_formula"] = (
                        f"${rep_area:.5f}\\text{{ m}}^2 \\times {rep_len:.2f}\\text{{ m (avg)}} = {rep_vol:.5f}\\text{{ m}}^3$"
                    )
                else:
                    quantities["end_diaphragm_vol_formula"] = (
                        f"${rep_area:.5f}\\text{{ m}}^2 \\times {rep_len:.2f}\\text{{ m}} = {rep_vol:.5f}\\text{{ m}}^3$"
                    )
                quantities["end_diaphragm_qty"] = str(total_ed_members)
                quantities["end_diaphragm_vol_total"] = f"{total_ed_vol:.2f}"
                quantities["end_diaphragm_wt_single"] = f"{single_ed_wt:.4f}"
                quantities["end_diaphragm_wt_total"] = f"{total_ed_wt:.2f}"
            else:
                quantities["end_diaphragm_vol_formula"] = "N.A."
                quantities["end_diaphragm_qty"] = "N.A."
                quantities["end_diaphragm_vol_total"] = "N.A."
                quantities["end_diaphragm_wt_single"] = "N.A."
                quantities["end_diaphragm_wt_total"] = "N.A."
        else:
            quantities["end_diaphragm_vol_formula"] = "N.A."
            quantities["end_diaphragm_qty"] = "N.A."
            quantities["end_diaphragm_vol_total"] = "N.A."
            quantities["end_diaphragm_wt_single"] = "N.A."
            quantities["end_diaphragm_wt_total"] = "N.A."

        # 6. Crash Barrier (Cu.m) and Weight (MT)
        KEY_CB_AREA = "typical_section.crash_barrier.area"
        cb_area = 0.0
        cb_area_val = inputs.get(KEY_CB_AREA)
        
        if cb_area_val is not None:
            try:
                cb_area = float(cb_area_val) / 1e6
            except Exception:
                pass
        
        if cb_area > 0.0:
            cb_vol = cb_area * span
            quantities["crash_barrier_vol_formula"] = f"${cb_area:.5f}\\text{{ m}}^2 \\times {span:.2f}\\text{{ m}} = {cb_vol:.5f}\\text{{ m}}^3$"
            quantities["crash_barrier_qty"] = "2"
            
            cb_total_vol = 2 * cb_vol
            quantities["crash_barrier_vol_total"] = f"{cb_total_vol:.2f}"
            
            single_cb_wt = cb_vol * 2.5
            total_cb_wt = cb_total_vol * 2.5
            quantities["crash_barrier_wt_single"] = f"{single_cb_wt:.2f}"
            quantities["crash_barrier_wt_total"] = f"{total_cb_wt:.2f}"
        else:
            quantities["crash_barrier_vol_formula"] = "N.A."
            quantities["crash_barrier_qty"] = "N.A."
            quantities["crash_barrier_vol_total"] = "N.A."
            quantities["crash_barrier_wt_single"] = "N.A."
            quantities["crash_barrier_wt_total"] = "N.A."

    except Exception as exc:
        logger.warning(f"Error calculating material quantities: {exc}")

    return quantities

"""
SkyMetrics Web -- browser front end for the same SkyMetrics physics
engine used by the desktop (CustomTkinter) app.

Run with:
    streamlit run web_app.py

Imports ONLY from src.physics / src.units / src.validation -- same
SI-only physics engine, same conversion layer, same validators as the
desktop app. No duplicated logic, no duplicated conversion constants.
"""

from __future__ import annotations

import textwrap

import numpy as np
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.physics.atmosphere import (
    isa_temperature, isa_pressure, isa_atmosphere, speed_of_sound, AtmosphereError,
    MIN_VALID_ALTITUDE_M, MAX_VALID_ALTITUDE_M,
)
from src.physics.performance import AircraftState, PerformanceError, compute_performance, velocity_sweep
from src.units import conversions as u
from src.validation import validators as v

st.set_page_config(page_title="SkyMetrics Web", page_icon="\u2708\ufe0f", layout="wide")

METRIC = "Metric"
IMPERIAL = "Imperial"

DEMO_METRIC = dict(
    altitude=1500.0, airspeed=45.0, temperature=8.5, pressure=84.6,
    wing_area=16.2, mass_weight=1050.0, cl=0.55, cd=0.045,
)

ACCENT = "#2C7BE5"
ACCENT_2 = "#7C4DFF"
GOOD = "#1DB954"
WARN = "#F5A623"
BAD = "#E5572C"

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
CUSTOM_CSS = f"""
<style>
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #0F1729 0%, #16213E 100%);
}}
[data-testid="stSidebar"] * {{
    color: #E8ECF7 !important;
}}
[data-testid="stSidebar"] .stNumberInput input {{
    background-color: #1E2A47 !important;
    border: 1px solid #2E3D5F !important;
    color: #F2F5FF !important;
}}
[data-testid="stSidebar"] label {{
    font-weight: 500;
    opacity: 0.9;
}}
.hero-banner {{
    background: linear-gradient(120deg, {ACCENT} 0%, {ACCENT_2} 100%);
    border-radius: 16px;
    padding: 28px 32px;
    color: white;
    margin-bottom: 22px;
    box-shadow: 0 8px 24px rgba(44,123,229,0.25);
}}
.hero-banner h1 {{
    margin: 0;
    font-size: 30px;
    font-weight: 800;
}}
.hero-banner p {{
    margin: 4px 0 0 0;
    opacity: 0.92;
    font-size: 14px;
}}
.result-card {{
    background: white;
    border-radius: 14px;
    padding: 16px 18px;
    box-shadow: 0 2px 10px rgba(20,30,60,0.08);
    border: 1px solid #EEF1F8;
    height: 100%;
}}
.result-card .rc-label {{
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: #6B7590;
    text-transform: uppercase;
    display: flex;
    align-items: center;
    gap: 6px;
}}
.result-card .rc-value {{
    font-size: 26px;
    font-weight: 800;
    color: #14203D;
    margin-top: 6px;
}}
.result-card .rc-unit {{
    font-size: 13px;
    color: #8A93AC;
    font-weight: 600;
    margin-left: 4px;
}}
.summary-card {{
    background: #F7F9FE;
    border-radius: 14px;
    padding: 16px 18px;
    border: 1px solid #EEF1F8;
}}
.summary-row {{
    display: flex;
    justify-content: space-between;
    padding: 7px 0;
    border-bottom: 1px dashed #E3E8F5;
    font-size: 14px;
}}
.summary-row:last-child {{ border-bottom: none; }}
.summary-row .sr-label {{ color: #6B7590; font-weight: 500; }}
.summary-row .sr-value {{ color: #14203D; font-weight: 700; }}
.rc-badge {{
    display: inline-block;
    font-size: 11px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 999px;
    margin-top: 8px;
}}
.rc-badge.up {{ background: #E6F7EC; color: #1DB954; }}
.rc-badge.down {{ background: #FDECEA; color: #E5572C; }}
.rc-badge.flat {{ background: #EEF1F8; color: #6B7590; }}
.eff-chip {{
    display: inline-block;
    font-size: 13px;
    font-weight: 800;
    padding: 4px 14px;
    border-radius: 999px;
    margin-top: 8px;
}}
.eff-chip.excellent {{ background: #E6F7EC; color: #1DB954; }}
.eff-chip.good {{ background: #FFF6E5; color: #C98A00; }}
.eff-chip.poor {{ background: #FDECEA; color: #E5572C; }}
.gauge-card {{
    background: white;
    border-radius: 14px;
    padding: 8px 6px 0 6px;
    box-shadow: 0 2px 10px rgba(20,30,60,0.08);
    border: 1px solid #EEF1F8;
}}
.section-title {{
    font-weight: 800;
    font-size: 17px;
    color: #14203D;
    margin: 4px 0 10px 0;
}}
div.stButton > button[kind="primary"] {{
    background: linear-gradient(120deg, {ACCENT} 0%, {ACCENT_2} 100%);
    border: none;
    font-weight: 700;
    border-radius: 10px;
    height: 46px;
}}
</style>
"""


def unit_suffix(key: str, imperial: bool) -> str:
    return {
        "altitude": "ft" if imperial else "m",
        "airspeed": "kt" if imperial else "m/s",
        "temperature": "\u00b0F" if imperial else "\u00b0C",
        "pressure": "psi" if imperial else "kPa",
        "wing_area": "ft\u00b2" if imperial else "m\u00b2",
        "mass_weight": "lb (weight)" if imperial else "kg (mass)",
    }[key]


def init_state() -> None:
    if "unit_system" not in st.session_state:
        st.session_state.unit_system = METRIC
    if "vals" not in st.session_state:
        st.session_state.vals = dict(DEMO_METRIC)


def convert_all_fields(old_system: str, new_system: str) -> None:
    to_imperial = new_system == IMPERIAL
    vals = st.session_state.vals

    def conv(key, value):
        if key == "altitude":
            return u.m_to_ft(value) if to_imperial else u.ft_to_m(value)
        if key == "airspeed":
            return u.mps_to_kt(value) if to_imperial else u.kt_to_mps(value)
        if key == "temperature":
            kelvin = u.f_to_k(value) if old_system == IMPERIAL else u.c_to_k(value)
            return u.k_to_f(kelvin) if to_imperial else u.k_to_c(kelvin)
        if key == "pressure":
            pa = u.psi_to_pa(value) if old_system == IMPERIAL else value * 1000.0
            return u.pa_to_psi(pa) if to_imperial else pa / 1000.0
        if key == "wing_area":
            return u.m2_to_ft2(value) if to_imperial else u.ft2_to_m2(value)
        if key == "mass_weight":
            if old_system == METRIC and to_imperial:
                return u.mass_kg_to_weight_lbf(value)
            if old_system == IMPERIAL and not to_imperial:
                return u.weight_lbf_to_mass_kg(value)
            return value
        return value

    for key in vals:
        vals[key] = conv(key, vals[key])


def build_aircraft_state(imperial: bool, raw: dict) -> tuple[AircraftState | None, list[str]]:
    errors: list[str] = []
    errors += v.validate_non_negative("Airspeed", raw["airspeed"]) if raw["airspeed"] < 0 else []
    errors += v.validate_positive("Airspeed", raw["airspeed"]) if raw["airspeed"] == 0 else []
    errors += v.validate_positive("Wing Area", raw["wing_area"])
    errors += v.validate_positive("Pressure", raw["pressure"])
    errors += v.validate_non_negative("Mass/Weight", raw["mass_weight"])
    errors += v.validate_coefficient("CL", raw["cl"])
    errors += v.validate_coefficient("CD", raw["cd"], low=0.0, high=5.0)
    if errors:
        return None, errors

    altitude_m = u.ft_to_m(raw["altitude"]) if imperial else raw["altitude"]
    velocity_mps = u.kt_to_mps(raw["airspeed"]) if imperial else raw["airspeed"]
    temperature_k = u.f_to_k(raw["temperature"]) if imperial else u.c_to_k(raw["temperature"])
    pressure_pa = u.psi_to_pa(raw["pressure"]) if imperial else raw["pressure"] * 1000.0
    wing_area_m2 = u.ft2_to_m2(raw["wing_area"]) if imperial else raw["wing_area"]
    mass_kg = u.weight_lbf_to_mass_kg(raw["mass_weight"]) if imperial else raw["mass_weight"]

    errors += v.validate_altitude(altitude_m)
    errors += v.validate_temperature_pressure(temperature_k, pressure_pa)
    if errors:
        return None, errors

    state = AircraftState(
        altitude_m=altitude_m, temperature_k=temperature_k, pressure_pa=pressure_pa,
        velocity_mps=velocity_mps, wing_area_m2=wing_area_m2, mass_kg=mass_kg,
        cl=raw["cl"], cd=raw["cd"],
    )
    return state, []


def result_card(col, icon: str, label: str, value: str, unit: str, badge: str | None = None,
                 badge_kind: str = "flat") -> None:
    badge_html = f'<div class="rc-badge {badge_kind}">{badge}</div>' if badge else ""
    with col:
        st.markdown(
            textwrap.dedent(f"""\
                <div class="result-card">
                    <div class="rc-label">{icon} {label}</div>
                    <div class="rc-value">{value}<span class="rc-unit">{unit}</span></div>
                    {badge_html}
                </div>"""),
            unsafe_allow_html=True,
        )


def efficiency_chip(ld: float) -> str:
    """Classify L/D into a color-coded efficiency chip (rough GA-aircraft bands)."""
    if ld == float("inf"):
        return '<div class="eff-chip excellent">No drag</div>'
    if ld >= 15:
        return '<div class="eff-chip excellent">Excellent efficiency</div>'
    if ld >= 8:
        return '<div class="eff-chip good">Typical efficiency</div>'
    return '<div class="eff-chip poor">Low efficiency</div>'


def gauge_figure(value: float, title: str, max_value: float, zones: list[tuple[float, float, str]],
                  suffix: str = "") -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": suffix, "font": {"size": 30, "color": "#14203D"}},
        title={"text": title, "font": {"size": 14, "color": "#6B7590"}},
        gauge={
            "axis": {"range": [0, max_value], "tickcolor": "#B7C0DA"},
            "bar": {"color": "#14203D", "thickness": 0.25},
            "bgcolor": "white",
            "borderwidth": 0,
            "steps": [{"range": [lo, hi], "color": c} for lo, hi, c in zones],
        },
    ))
    fig.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=10),
                       paper_bgcolor="white", font=dict(family="Inter, Segoe UI, sans-serif"))
    return fig


def atmosphere_profile_figure(current_altitude_m: float, current_density: float) -> go.Figure:
    """ISA density-vs-altitude reference profile with the current point marked."""
    altitudes = np.linspace(MIN_VALID_ALTITUDE_M, MAX_VALID_ALTITUDE_M, 120)
    densities = [isa_atmosphere(alt).density_kg_m3 for alt in altitudes]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=densities, y=altitudes / 1000.0, mode="lines",
        line=dict(color="#94A3C4", width=2, dash="dot"), name="ISA standard",
    ))
    fig.add_trace(go.Scatter(
        x=[current_density], y=[current_altitude_m / 1000.0], mode="markers",
        marker=dict(color=ACCENT, size=13, symbol="diamond", line=dict(color="white", width=2)),
        name="Current point",
    ))
    fig.update_layout(
        height=260, plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="Air Density [kg/m\u00b3]", yaxis_title="Altitude [km]",
        font=dict(family="Inter, Segoe UI, sans-serif", size=12, color="#33415C"),
        xaxis=dict(gridcolor="#EEF1F8"), yaxis=dict(gridcolor="#EEF1F8"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return fig


def styled_line_chart(x, y, x_title: str, y_title: str, color: str, current_x: float) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="lines+markers", line=dict(color=color, width=3, shape="spline"),
        marker=dict(size=4, color=color), fill="tozeroy",
        fillcolor=color.replace(")", ",0.10)").replace("rgb", "rgba") if color.startswith("rgb") else None,
        name=y_title,
    ))
    fig.add_vline(x=current_x, line_dash="dash", line_color="#94A3C4", line_width=1.5)
    fig.update_layout(
        xaxis_title=x_title, yaxis_title=y_title, height=420,
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=10, r=10, t=10, b=10),
        font=dict(family="Inter, Segoe UI, sans-serif", size=13, color="#33415C"),
        xaxis=dict(gridcolor="#EEF1F8", zeroline=False),
        yaxis=dict(gridcolor="#EEF1F8", zeroline=False),
        showlegend=False,
    )
    return fig


def main() -> None:
    init_state()
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### \u2708\ufe0f  Inputs")
        st.caption("Unit System")
        new_system = st.radio("Unit System", [METRIC, IMPERIAL],
                               index=0 if st.session_state.unit_system == METRIC else 1,
                               horizontal=True, label_visibility="collapsed")
        if new_system != st.session_state.unit_system:
            convert_all_fields(st.session_state.unit_system, new_system)
            st.session_state.unit_system = new_system

        imperial = st.session_state.unit_system == IMPERIAL
        vals = st.session_state.vals

        vals["altitude"] = st.number_input(
            f"Altitude [{unit_suffix('altitude', imperial)}]", value=float(vals["altitude"]))

        if st.button("\u2601\ufe0f  Fill ISA Standard Atmosphere for Altitude", width='stretch'):
            altitude_m = u.ft_to_m(vals["altitude"]) if imperial else vals["altitude"]
            try:
                t_k = isa_temperature(altitude_m)
                p_pa = isa_pressure(altitude_m)
                vals["temperature"] = u.k_to_f(t_k) if imperial else u.k_to_c(t_k)
                vals["pressure"] = u.pa_to_psi(p_pa) if imperial else p_pa / 1000.0
            except AtmosphereError as exc:
                st.error(str(exc))

        vals["airspeed"] = st.number_input(
            f"Airspeed [{unit_suffix('airspeed', imperial)}]", value=float(vals["airspeed"]))
        vals["temperature"] = st.number_input(
            f"Temperature [{unit_suffix('temperature', imperial)}]", value=float(vals["temperature"]))
        vals["pressure"] = st.number_input(
            f"Pressure (absolute) [{unit_suffix('pressure', imperial)}]", value=float(vals["pressure"]))
        vals["wing_area"] = st.number_input(
            f"Wing Area [{unit_suffix('wing_area', imperial)}]", value=float(vals["wing_area"]))
        vals["mass_weight"] = st.number_input(
            f"{'Weight (force)' if imperial else 'Mass'} [{unit_suffix('mass_weight', imperial)}]",
            value=float(vals["mass_weight"]))
        vals["cl"] = st.number_input("CL (Lift Coefficient)", value=float(vals["cl"]))
        vals["cd"] = st.number_input("CD (Drag Coefficient)", value=float(vals["cd"]))

        st.markdown("<br>", unsafe_allow_html=True)
        calc = st.button("\u2708\ufe0f  Run Analysis", type="primary", width='stretch')
        if st.button("\u21bb  Load Demo Values", width='stretch'):
            st.session_state.unit_system = METRIC
            st.session_state.vals = dict(DEMO_METRIC)
            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("\u24d8\ufe0f Educational tool only, not certified flight-planning software.")

    st.markdown(
        textwrap.dedent("""\
            <div class="hero-banner">
                <h1>\u2708\ufe0f SkyMetrics Web</h1>
                <p>Aircraft Performance Analysis &mdash; browser version of the SkyMetrics desktop tool.</p>
            </div>"""),
        unsafe_allow_html=True,
    )

    if not calc:
        st.info("Set inputs in the sidebar and press **Run Analysis**.")
        return

    state, errors = build_aircraft_state(imperial, vals)
    if errors:
        for e in errors:
            st.error(e)
        return

    try:
        result = compute_performance(state)
    except PerformanceError as exc:
        st.error(str(exc))
        return

    a = speed_of_sound(state.temperature_k)
    mach = state.velocity_mps / a
    ld = result.aero.l_over_d

    # Real ISA reference comparison (not decorative) -- only meaningful
    # within the model's supported altitude range.
    isa_ref = None
    if MIN_VALID_ALTITUDE_M <= state.altitude_m <= MAX_VALID_ALTITUDE_M:
        isa_ref = isa_atmosphere(state.altitude_m)

    def isa_badge(current: float, reference: float | None, higher_is_kind: str = "up") -> tuple[str | None, str]:
        if reference is None or reference == 0:
            return None, "flat"
        pct = (current - reference) / reference * 100.0
        if abs(pct) < 0.5:
            return "Matches ISA", "flat"
        direction = "up" if pct > 0 else "down"
        return f"{pct:+.1f}% vs ISA", direction

    density_badge, density_kind = isa_badge(result.atmosphere.density_kg_m3, isa_ref.density_kg_m3 if isa_ref else None)
    pressure_badge, pressure_kind = isa_badge(result.atmosphere.pressure_pa, isa_ref.pressure_pa if isa_ref else None)

    if imperial:
        density_txt, density_unit = f"{result.atmosphere.density_kg_m3:,.4f}", "kg/m\u00b3"
        q_val = u.n_to_lbf(result.aero.dynamic_pressure_pa) / u.m2_to_ft2(1.0)
        q_txt, q_unit = f"{q_val:,.3f}", "lbf/ft\u00b2"
        lift_txt, lift_unit = f"{u.n_to_lbf(result.aero.lift_n):,.1f}", "lbf"
        drag_txt, drag_unit = f"{u.n_to_lbf(result.aero.drag_n):,.1f}", "lbf"
        weight_txt, weight_unit = f"{u.n_to_lbf(result.weight_n):,.1f}", "lbf"
    else:
        density_txt, density_unit = f"{result.atmosphere.density_kg_m3:,.4f}", "kg/m\u00b3"
        q_txt, q_unit = f"{result.aero.dynamic_pressure_pa:,.1f}", "Pa"
        lift_txt, lift_unit = f"{result.aero.lift_n:,.1f}", "N"
        drag_txt, drag_unit = f"{result.aero.drag_n:,.1f}", "N"
        weight_txt, weight_unit = f"{result.weight_n:,.1f}", "N"
    ld_txt = "\u221e" if ld == float("inf") else f"{ld:,.2f}"

    st.markdown("#### \U0001F4CA Results")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    result_card(c1, "\u269b\ufe0f", "Air Density", density_txt, density_unit, density_badge, density_kind)
    result_card(c2, "\U0001F4CF", "Dynamic Pressure", q_txt, q_unit)
    result_card(c3, "\u2b06\ufe0f", "Lift", lift_txt, lift_unit)
    result_card(c4, "\u27a1\ufe0f", "Drag", drag_txt, drag_unit)
    result_card(c5, "\u2696\ufe0f", "Weight", weight_txt, weight_unit)
    with c6:
        st.markdown(
            textwrap.dedent(f"""\
                <div class="result-card">
                    <div class="rc-label">\u2696\ufe0f L/D</div>
                    <div class="rc-value">{ld_txt}</div>
                    {efficiency_chip(ld)}
                </div>"""),
            unsafe_allow_html=True,
        )

    if ld == float("inf"):
        st.warning("Drag is zero: L/D is undefined/infinite for this input.")
    if isa_ref is not None and pressure_badge:
        st.caption(f"Pressure is {pressure_badge.lower()} standard-day ISA at this altitude ({isa_ref.pressure_pa:,.0f} Pa reference).")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">\U0001F6E9\ufe0f Flight Envelope Gauges</div>', unsafe_allow_html=True)
    g1, g2, g3 = st.columns(3)
    with g1:
        st.markdown('<div class="gauge-card">', unsafe_allow_html=True)
        st.plotly_chart(
            gauge_figure(mach, "Mach Number", max_value=1.2,
                         zones=[(0, 0.3, "#E6F7EC"), (0.3, 0.8, "#FFF6E5"), (0.8, 1.2, "#FDECEA")]),
            width='stretch',
        )
        st.markdown("</div>", unsafe_allow_html=True)
    with g2:
        ld_gauge_val = 0.0 if ld == float("inf") else min(ld, 30.0)
        st.markdown('<div class="gauge-card">', unsafe_allow_html=True)
        st.plotly_chart(
            gauge_figure(ld_gauge_val, "L/D Ratio", max_value=30,
                         zones=[(0, 8, "#FDECEA"), (8, 15, "#FFF6E5"), (15, 30, "#E6F7EC")]),
            width='stretch',
        )
        st.markdown("</div>", unsafe_allow_html=True)
    with g3:
        st.markdown('<div class="gauge-card">', unsafe_allow_html=True)
        st.plotly_chart(
            gauge_figure(result.atmosphere.density_kg_m3, "Air Density [kg/m\u00b3]", max_value=1.4,
                         zones=[(0, 0.5, "#FDECEA"), (0.5, 1.0, "#FFF6E5"), (1.0, 1.4, "#E6F7EC")]),
            width='stretch',
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### \U0001F4C8 Performance Visualization")

    v_center = max(state.velocity_mps, 1.0)
    velocities, lift_arr, drag_arr, ld_arr = velocity_sweep(
        state, v_min_mps=max(v_center * 0.2, 0.5), v_max_mps=v_center * 2.0, num_points=150
    )
    if imperial:
        x = [u.mps_to_kt(val) for val in velocities]
        x_title = "Airspeed [kt]"
        lift_y = [u.n_to_lbf(val) for val in lift_arr]
        drag_y = [u.n_to_lbf(val) for val in drag_arr]
        force_unit = "lbf"
        current_v = u.mps_to_kt(state.velocity_mps)
    else:
        x = list(velocities)
        x_title = "Airspeed [m/s]"
        lift_y = list(lift_arr)
        drag_y = list(drag_arr)
        force_unit = "N"
        current_v = state.velocity_mps

    col_plot, col_summary = st.columns([2.6, 1])
    with col_plot:
        tab1, tab2, tab3 = st.tabs(["Lift vs Airspeed", "Drag vs Airspeed", "L/D vs Airspeed"])
        with tab1:
            st.plotly_chart(
                styled_line_chart(x, lift_y, x_title, f"Lift [{force_unit}]", ACCENT, current_v),
                width='stretch',
            )
        with tab2:
            st.plotly_chart(
                styled_line_chart(x, drag_y, x_title, f"Drag [{force_unit}]", BAD, current_v),
                width='stretch',
            )
        with tab3:
            st.plotly_chart(
                styled_line_chart(x, list(ld_arr), x_title, "L/D [-]", GOOD, current_v),
                width='stretch',
            )

    with col_summary:
        alt_disp = f"{vals['altitude']:,.2f} {unit_suffix('altitude', imperial)}"
        speed_disp = f"{vals['airspeed']:,.2f} {unit_suffix('airspeed', imperial)}"
        temp_disp = f"{vals['temperature']:,.2f} {unit_suffix('temperature', imperial)}"
        pres_disp = f"{vals['pressure']:,.2f} {unit_suffix('pressure', imperial)}"
        st.markdown(
            textwrap.dedent(f"""\
                <div class="summary-card">
                    <div style="font-weight:800; font-size:15px; margin-bottom:8px;">\U0001F4CB Flight Summary</div>
                    <div class="summary-row"><span class="sr-label">\u26f0\ufe0f Altitude</span><span class="sr-value">{alt_disp}</span></div>
                    <div class="summary-row"><span class="sr-label">\U0001F4A8 Airspeed</span><span class="sr-value">{speed_disp}</span></div>
                    <div class="summary-row"><span class="sr-label">\U0001F321\ufe0f Temperature</span><span class="sr-value">{temp_disp}</span></div>
                    <div class="summary-row"><span class="sr-label">\U0001F4CA Pressure (abs)</span><span class="sr-value">{pres_disp}</span></div>
                    <div class="summary-row"><span class="sr-label">\U0001F680 Mach Number</span><span class="sr-value">{mach:,.3f}</span></div>
                    <div class="summary-row"><span class="sr-label">\U0001F50A Speed of Sound</span><span class="sr-value">{a:,.1f} m/s</span></div>
                </div>"""),
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-title" style="font-size:14px;">\U0001F30D Atmosphere Profile (ISA)</div>', unsafe_allow_html=True)
        st.plotly_chart(
            atmosphere_profile_figure(state.altitude_m, result.atmosphere.density_kg_m3),
            width='stretch',
        )

    st.markdown(
        textwrap.dedent("""\
            <div style="text-align:center; color:#9AA3BD; font-size:12px; margin-top:28px;">
                &copy; 2026 SkyMetrics Web &mdash; Educational Tool &nbsp;|&nbsp; Not for real-world operational use
            </div>"""),
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()

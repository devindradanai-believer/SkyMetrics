"""
ApogeeLab -- browser front end for the rocket trajectory engine.

Run with:
    streamlit run apogeelab_app.py

Imports ONLY from src.physics.rocket (which itself reuses
src.physics.aerodynamics for drag and src.physics.atmosphere for
density) and src.validation -- same "physics engine stays separate
from UI" architecture as web_app.py / main.py.
"""

from __future__ import annotations

import textwrap

import streamlit as st
import plotly.graph_objects as go

from src.physics.rocket import RocketConfig, RocketError, simulate_trajectory, thrust_to_weight
from src.units import conversions as u
from src.validation import validators as v

st.set_page_config(page_title="ApogeeLab", page_icon="\U0001F680", layout="wide")

ACCENT = "#7C4DFF"
ACCENT_2 = "#FF6B4A"
GOOD = "#1DB954"
WARN = "#F5A623"
BAD = "#E5572C"

CUSTOM_CSS = f"""
<style>
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #150F29 0%, #241633 100%);
}}
[data-testid="stSidebar"] * {{ color: #EDE7F7 !important; }}
[data-testid="stSidebar"] .stNumberInput input {{
    background-color: #2A1F42 !important;
    border: 1px solid #3D2C5C !important;
    color: #F5F0FF !important;
}}
[data-testid="stSidebar"] label {{ font-weight: 500; opacity: 0.9; }}
.hero-banner {{
    background: linear-gradient(120deg, {ACCENT} 0%, {ACCENT_2} 100%);
    border-radius: 16px;
    padding: 28px 32px;
    color: white;
    margin-bottom: 22px;
    box-shadow: 0 8px 24px rgba(124,77,255,0.25);
}}
.hero-banner h1 {{ margin: 0; font-size: 30px; font-weight: 800; }}
.hero-banner p {{ margin: 4px 0 0 0; opacity: 0.92; font-size: 14px; }}
.result-card {{
    background: white;
    border-radius: 14px;
    padding: 16px 18px;
    box-shadow: 0 2px 10px rgba(20,30,60,0.08);
    border: 1px solid #EEF1F8;
    height: 100%;
}}
.result-card .rc-label {{
    font-size: 12px; font-weight: 700; letter-spacing: 0.04em;
    color: #6B7590; text-transform: uppercase;
}}
.result-card .rc-value {{ font-size: 24px; font-weight: 800; color: #14203D; margin-top: 6px; }}
.result-card .rc-unit {{ font-size: 13px; color: #8A93AC; font-weight: 600; margin-left: 4px; }}
.rc-badge {{
    display: inline-block; font-size: 11px; font-weight: 700;
    padding: 2px 8px; border-radius: 999px; margin-top: 8px;
}}
.rc-badge.good {{ background: #E6F7EC; color: #1DB954; }}
.rc-badge.warn {{ background: #FFF6E5; color: #C98A00; }}
.rc-badge.bad {{ background: #FDECEA; color: #E5572C; }}
.section-title {{ font-weight: 800; font-size: 17px; color: #14203D; margin: 4px 0 10px 0; }}
div.stButton > button[kind="primary"] {{
    background: linear-gradient(120deg, {ACCENT} 0%, {ACCENT_2} 100%);
    border: none; font-weight: 700; border-radius: 10px; height: 46px;
}}
</style>
"""

DEMO = dict(
    dry_mass=1.0, propellant_mass=0.2, thrust=100.0, burn_time=1.5,
    cd=0.5, diameter=0.10,
)


def init_state() -> None:
    if "rvals" not in st.session_state:
        st.session_state.rvals = dict(DEMO)


def result_card(col, icon: str, label: str, value: str, unit: str, badge: str | None = None,
                 badge_kind: str = "good") -> None:
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


def twr_badge(twr: float) -> tuple[str, str]:
    if twr < 1.0:
        return "Will not lift off", "bad"
    if twr < 5.0:
        return "Marginal liftoff", "warn"
    return "Healthy liftoff", "good"


def trajectory_figure(result, y_key: str, y_title: str, color: str) -> go.Figure:
    y = getattr(result, y_key)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=result.time_s, y=y, mode="lines", line=dict(color=color, width=3),
        fill="tozeroy", name=y_title,
    ))
    fig.add_vline(x=result.apogee_time_s, line_dash="dash", line_color="#94A3C4", line_width=1.5,
                  annotation_text="Apogee", annotation_font_size=10)
    if result.landing_time_s:
        fig.add_vline(x=result.landing_time_s, line_dash="dot", line_color="#C4A594", line_width=1.5,
                      annotation_text="Landing", annotation_font_size=10)
    fig.update_layout(
        xaxis_title="Time [s]", yaxis_title=y_title, height=380,
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=10, r=10, t=20, b=10),
        font=dict(family="Inter, Segoe UI, sans-serif", size=13, color="#33415C"),
        xaxis=dict(gridcolor="#EEF1F8"), yaxis=dict(gridcolor="#EEF1F8"),
        showlegend=False,
    )
    return fig


def main() -> None:
    init_state()
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### \U0001F680  Rocket Inputs")
        vals = st.session_state.rvals

        vals["dry_mass"] = st.number_input("Dry Mass [kg]", value=float(vals["dry_mass"]), min_value=0.0)
        vals["propellant_mass"] = st.number_input("Propellant Mass [kg]", value=float(vals["propellant_mass"]), min_value=0.0)
        vals["thrust"] = st.number_input("Motor Thrust [N]", value=float(vals["thrust"]), min_value=0.0)
        vals["burn_time"] = st.number_input("Burn Time [s]", value=float(vals["burn_time"]), min_value=0.0)
        vals["cd"] = st.number_input("Drag Coefficient CD [-]", value=float(vals["cd"]), min_value=0.0)
        vals["diameter"] = st.number_input("Body Diameter [m]", value=float(vals["diameter"]), min_value=0.0)

        st.markdown("<br>", unsafe_allow_html=True)
        calc = st.button("\U0001F680  Launch Simulation", type="primary", width="stretch")
        if st.button("\u21bb  Load Demo Values", width="stretch"):
            st.session_state.rvals = dict(DEMO)
            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("\u24d8\ufe0f 1-D vertical trajectory model. No wind, no parachute, no thrust vector control. Educational estimate only.")

    st.markdown(
        textwrap.dedent("""\
            <div class="hero-banner">
                <h1>\U0001F680 ApogeeLab</h1>
                <p>Thrust-to-weight, drag, and altitude/velocity vs time trajectory simulation.</p>
            </div>"""),
        unsafe_allow_html=True,
    )

    if not calc:
        st.info("Set motor and airframe inputs in the sidebar and press **Launch Simulation**.")
        return

    errors: list[str] = []
    errors += v.validate_positive("Dry Mass", vals["dry_mass"])
    errors += v.validate_non_negative("Propellant Mass", vals["propellant_mass"])
    errors += v.validate_non_negative("Thrust", vals["thrust"])
    errors += v.validate_non_negative("Burn Time", vals["burn_time"])
    errors += v.validate_non_negative("CD", vals["cd"])
    errors += v.validate_positive("Body Diameter", vals["diameter"])
    if errors:
        for e in errors:
            st.error(e)
        return

    reference_area_m2 = 3.14159265 * (vals["diameter"] / 2.0) ** 2
    config = RocketConfig(
        dry_mass_kg=vals["dry_mass"], propellant_mass_kg=vals["propellant_mass"],
        thrust_n=vals["thrust"], burn_time_s=vals["burn_time"],
        cd=vals["cd"], reference_area_m2=reference_area_m2,
    )

    try:
        launch_mass = config.dry_mass_kg + config.propellant_mass_kg
        twr = thrust_to_weight(config.thrust_n, launch_mass) if launch_mass > 0 else 0.0
        result = simulate_trajectory(config, dt=0.01, max_time_s=300.0)
    except RocketError as exc:
        st.error(str(exc))
        return

    badge_text, badge_kind = twr_badge(twr)

    st.markdown("#### \U0001F4CA Results")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    result_card(c1, "\u2696\ufe0f", "Thrust-to-Weight", f"{twr:,.2f}", "", badge_text, badge_kind)
    result_card(c2, "\U0001F3D4\ufe0f", "Apogee", f"{result.apogee_m:,.1f}", "m")
    result_card(c3, "\u23F1\ufe0f", "Time to Apogee", f"{result.apogee_time_s:,.2f}", "s")
    result_card(c4, "\U0001F4A8", "Max Velocity", f"{result.max_velocity_mps:,.1f}", "m/s")
    result_card(c5, "\U0001F525", "Max Acceleration", f"{result.max_acceleration_mps2:,.1f}", "m/s\u00b2")
    landing_txt = f"{result.landing_time_s:,.1f}" if result.landing_time_s else "N/A"
    result_card(c6, "\U0001F3AF", "Landing Time", landing_txt, "s" if result.landing_time_s else "")

    if twr < 1.0:
        st.warning("Thrust-to-weight ratio is below 1.0 -- this configuration will not leave the pad.")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">\U0001F4C8 Trajectory</div>', unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["Altitude vs Time", "Velocity vs Time", "Acceleration vs Time"])
    with tab1:
        st.plotly_chart(trajectory_figure(result, "altitude_m", "Altitude [m]", ACCENT), width="stretch")
    with tab2:
        st.plotly_chart(trajectory_figure(result, "velocity_mps", "Velocity [m/s]", ACCENT_2), width="stretch")
    with tab3:
        st.plotly_chart(trajectory_figure(result, "acceleration_mps2", "Acceleration [m/s\u00b2]", GOOD), width="stretch")

    st.markdown(
        textwrap.dedent("""\
            <div style="text-align:center; color:#9AA3BD; font-size:12px; margin-top:28px;">
                &copy; 2026 ApogeeLab &mdash; Educational Tool &nbsp;|&nbsp; Not for real flight safety analysis
            </div>"""),
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()

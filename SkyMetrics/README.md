# SkyMetrics - Aircraft Performance Analysis Tool

[![Tests](https://github.com/devindradanai-believer/SkyMetrics/actions/workflows/tests.yml/badge.svg)](https://github.com/devindradanai-believer/SkyMetrics/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

SkyMetrics is a desktop application for interactive aircraft
performance calculations: air density, dynamic pressure, lift, drag,
weight, and lift-to-drag ratio (L/D), for a user-defined aircraft and
flight condition. It supports both Metric and Imperial (aviation-style)
input directly — no manual unit conversion required. A browser-based
version (Streamlit) is included as well, sharing the same physics
engine.

> **Not certified flight-planning software.** SkyMetrics is an
> educational / personal aircraft-performance analysis tool. It is
> **not** validated or certified for real flight planning, dispatch,
> or airworthiness decisions.

---

## Features

- Enter Altitude, Airspeed, Temperature, Pressure, Wing Area, and
  Mass/Weight directly in aviation-style Imperial units (ft, kt, °F,
  psi, ft², lb) **or** SI-friendly Metric units (m, m/s, °C, kPa, m²,
  kg) — switch at any time without losing or corrupting entered values.
- One-click **Fill ISA Standard Atmosphere** helper: given an altitude,
  auto-fills Temperature and Pressure from the International Standard
  Atmosphere model (still fully editable for non-standard-day
  conditions).
- Correct handling of the lbf-vs-lbm distinction: an Imperial "Weight"
  entry is treated as a *force* (lbf) and converted to mass via
  `W = m·g`, never silently treated as pounds-mass.
- Strong input validation with clear, field-level error messages; the
  app never crashes on bad input.
- Live results panel: Air Density, Dynamic Pressure, Lift, Drag,
  Weight, L/D — displayed in the selected unit system.
- Matplotlib performance plots: Lift, Drag, or L/D vs. Airspeed, swept
  around the current operating point, with the current point marked.
- Safe division-by-zero handling for L/D (shown as "∞ (undefined)"
  rather than crashing).
- Automated pytest suite covering unit conversions, atmosphere,
  aerodynamics, validation, and Metric/Imperial cross-consistency.

---

## Physics Equations

All calculations are performed internally in **SI units**; the GUI
converts to/from the selected display unit system only at the input
and output boundaries.

| Quantity | Equation | Units |
|---|---|---|
| Air density | `ρ = p / (R·T)` (ideal gas law) | kg/m³ |
| Dynamic pressure | `q = 0.5·ρ·V²` | Pa |
| Lift | `L = 0.5·ρ·V²·S·C_L` | N |
| Drag | `D = 0.5·ρ·V²·S·C_D` | N |
| Weight | `W = m·g` | N |
| Lift-to-drag ratio | `L/D = L / D` | – |

Constants: `g = 9.80665 m/s²`, `R_air = 287.05 J/(kg·K)`.

### Atmosphere model

SkyMetrics implements the **International Standard Atmosphere (ISA)**
for two layers:

1. **Troposphere (0–11,000 m):** linear temperature lapse rate of
   0.0065 K/m from the sea-level reference `T0 = 288.15 K`,
   `p0 = 101,325 Pa`.
2. **Lower stratosphere (11,000–20,000 m):** isothermal at 216.65 K,
   pressure via the exponential barometric formula.

Altitudes outside **0–20,000 m** are rejected — this is the supported
range of the implemented model and comfortably covers conventional
subsonic/transonic aircraft operations.

Air density is always computed from whatever Temperature and Pressure
values are currently in those fields (via the ideal gas law), **not**
solely from altitude — so a user can model a non-standard ("hot day" /
"cold day" / off-standard pressure) atmosphere by editing Temperature
and/or Pressure after using the ISA-fill helper, or by entering them
directly. **Pressure is always treated as absolute pressure**, never
gauge pressure.

---

## Unit Systems

| Field | Metric | Imperial |
|---|---|---|
| Altitude | m | ft |
| Airspeed | m/s | kt |
| Temperature | °C | °F |
| Pressure (absolute) | kPa | psi |
| Wing Area | m² | ft² |
| Mass/Weight | kg (**mass**) | lb (**weight force**, lbf) |
| C_L, C_D | – | – |

Switching unit systems converts every currently-entered value in
place (via the SI intermediate) so no data is lost or silently
misinterpreted.

---

## Architecture

```
SkyMetrics/
├── main.py                  # Desktop entry point
├── web_app.py                # Web (Streamlit) entry point -- same physics/units/validation
├── apogeelab_app.py           # ApogeeLab: rocket trajectory simulator (Streamlit) -- separate physics domain
├── requirements.txt
├── README.md
├── LICENSE
├── .gitignore
├── .github/
│   └── workflows/
│       └── tests.yml        # CI: runs pytest on push/PR across Python 3.10-3.12
├── src/
│   ├── gui/                 # CustomTkinter UI (no physics/unit-conversion logic)
│   │   ├── app.py           # Main window, orchestrates panels
│   │   ├── input_panel.py   # Input fields, unit switching, validation call-out
│   │   ├── results_panel.py # Formats/display of computed results
│   │   └── plots.py         # Matplotlib Lift/Drag/L-D vs Airspeed plots
│   ├── physics/              # Pure SI-unit physics engine (independently testable)
│   │   ├── atmosphere.py    # ISA model, ideal gas law density
│   │   ├── aerodynamics.py  # q, L, D, L/D
│   │   ├── performance.py   # Orchestration: AircraftState -> PerformanceResult
│   │   └── rocket.py         # Thrust-to-weight, RK4 trajectory integration
│   ├── units/
│   │   └── conversions.py   # ALL conversion constants/functions live here
│   └── validation/
│       └── validators.py    # Field parsing + physical sanity checks
└── tests/
    ├── test_units.py
    ├── test_atmosphere.py
    ├── test_aerodynamics.py         # also covers performance.py
    ├── test_validation.py
    ├── test_rocket.py
    └── test_metric_imperial_consistency.py
```

**Data flow:** `User Input → Validation → Unit Conversion → SI Physics
Engine → Results → Display Conversion`. The physics layer
(`src/physics/`) never imports GUI code or unit-conversion code with
GUI-facing units baked in — it only ever sees SI floats. The unit
system selection lives entirely in the GUI layer.

---

## Installation

Requires Python 3.10+ with Tk support (the standard CPython installer
for Windows/macOS includes this; on Debian/Ubuntu Linux you may need
`sudo apt-get install python3-tk`).

```bash
pip install -r requirements.txt
```

## Running the application

Desktop (CustomTkinter):

```bash
python main.py
```

Web (Streamlit, same physics/units/validation code, browser UI):

```bash
streamlit run web_app.py
```

ApogeeLab -- rocket trajectory simulator (Streamlit, separate physics domain, reuses drag/atmosphere):

```bash
streamlit run apogeelab_app.py
```

Opens at `http://localhost:8501`. Uses `src/physics`, `src/units`, and
`src/validation` directly — no duplicated logic between the desktop
and web front ends.

### ApogeeLab (Rocket Trajectory Simulator)

`apogeelab_app.py` (ApogeeLab) is a separate tool for 1-D vertical rocket flight —
thrust-to-weight ratio, and a full ascent/coast/descent trajectory
(altitude, velocity, acceleration vs time) under constant motor
thrust, gravity, and drag, with propellant mass burning off linearly
over the burn time. Lives in `src/physics/rocket.py`, and reuses
`aerodynamics.drag()` (same `D = 0.5*rho*V²*S*CD` equation, just with
a rocket's cross-sectional area/CD instead of a wing's) and the
`atmosphere` module's ISA density model, extrapolated exponentially
above 20,000 m. Not a substitute for OpenRocket/RASAero — no wind,
recovery system, or thrust vector control.

## Running tests

```bash
pytest
```

(54 tests covering unit conversions, ISA atmosphere, aerodynamics,
performance orchestration, input validation, and Metric/Imperial
cross-consistency.)

---

## Assumptions

- Dry air, no humidity correction.
- ISA sea-level reference: `T0 = 288.15 K`, `p0 = 101,325 Pa`.
- Air treated as an ideal gas.
- Pressure inputs are always **absolute**, never gauge.
- An Imperial "Weight" input is a **force** in lbf; a Metric
  "Mass" input is a **mass** in kg.
- CL/CD are accepted only within a physically plausible sanity range
  (roughly [-5, 5] / [0, 5]) to catch data-entry mistakes.

## Limitations

- ISA model covers 0–20,000 m only (troposphere + lower stratosphere).
- No compressibility, Mach, or Reynolds-number effects (incompressible
  aerodynamics only).
- No drag polar (parasite/induced drag split), stall speed, climb
  performance, or range/endurance modeling in this version.
- No persistent aircraft database — inputs are entered manually each
  session (a "Load Demo Values" button fills clearly hypothetical
  sample data for quick exploration only).
- Not validated against flight-test or published type-certificate
  data; **do not use for real flight planning.**

## Future Development

The architecture is intentionally modular so the following can be
added without restructuring existing code:

- Drag polar (parasite + induced drag), stall speed, best glide speed
- Rate of climb, power/thrust required, range/endurance
- Mach number and Reynolds number effects
- A richer standard-atmosphere model (upper stratosphere+)
- Aircraft preset database with CSV import/export
- Performance envelopes, interactive plots, multi-aircraft comparison
- Validation against published aircraft performance data

## License

MIT — see [LICENSE](LICENSE).

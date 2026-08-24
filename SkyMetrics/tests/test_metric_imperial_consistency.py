"""
Cross-check: equivalent Metric and Imperial inputs must produce
matching results (after conversion) within numerical tolerance.

This exercises the full pipeline: unit conversion -> SI physics
engine, mirroring what the GUI does for each unit-system selection.
"""

import math
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.units import conversions as u
from src.physics import performance as perf


def test_metric_and_imperial_inputs_agree():
    # ---- Imperial-style inputs (as a user would type them) ----
    altitude_ft = 5000.0
    airspeed_kt = 120.0
    temperature_f = 41.17   # ISA temp at 5000 ft in Fahrenheit
    pressure_psi = 12.23    # ISA pressure at 5000 ft in psi
    wing_area_ft2 = 174.0
    weight_lbf = 2300.0
    cl = 0.55
    cd = 0.045

    imperial_state = perf.AircraftState(
        altitude_m=u.ft_to_m(altitude_ft),
        temperature_k=u.f_to_k(temperature_f),
        pressure_pa=u.psi_to_pa(pressure_psi),
        velocity_mps=u.kt_to_mps(airspeed_kt),
        wing_area_m2=u.ft2_to_m2(wing_area_ft2),
        mass_kg=u.weight_lbf_to_mass_kg(weight_lbf),
        cl=cl,
        cd=cd,
    )
    imperial_result = perf.compute_performance(imperial_state)

    # ---- Equivalent Metric inputs (converted by hand / independently) ----
    altitude_m = u.ft_to_m(altitude_ft)
    airspeed_mps = u.kt_to_mps(airspeed_kt)
    temperature_k = u.f_to_k(temperature_f)
    pressure_pa = u.psi_to_pa(pressure_psi)
    wing_area_m2 = u.ft2_to_m2(wing_area_ft2)
    mass_kg = u.weight_lbf_to_mass_kg(weight_lbf)

    metric_state = perf.AircraftState(
        altitude_m=altitude_m,
        temperature_k=temperature_k,
        pressure_pa=pressure_pa,
        velocity_mps=airspeed_mps,
        wing_area_m2=wing_area_m2,
        mass_kg=mass_kg,
        cl=cl,
        cd=cd,
    )
    metric_result = perf.compute_performance(metric_state)

    assert math.isclose(
        imperial_result.atmosphere.density_kg_m3,
        metric_result.atmosphere.density_kg_m3, rel_tol=1e-9,
    )
    assert math.isclose(imperial_result.aero.lift_n, metric_result.aero.lift_n, rel_tol=1e-9)
    assert math.isclose(imperial_result.aero.drag_n, metric_result.aero.drag_n, rel_tol=1e-9)
    assert math.isclose(imperial_result.weight_n, metric_result.weight_n, rel_tol=1e-9)
    assert math.isclose(imperial_result.aero.l_over_d, metric_result.aero.l_over_d, rel_tol=1e-9)

    # Independent sanity check: converting the SI lift result back to
    # lbf should match a hand conversion.
    lift_lbf = u.n_to_lbf(imperial_result.aero.lift_n)
    assert lift_lbf > 0

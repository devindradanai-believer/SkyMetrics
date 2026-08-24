"""Tests for src.physics.aerodynamics and src.physics.performance."""

import math
import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.physics import aerodynamics as aero
from src.physics import performance as perf


def test_dynamic_pressure_known_value():
    # rho=1.225, V=100 -> q = 0.5*1.225*100^2 = 6125 Pa
    q = aero.dynamic_pressure(1.225, 100.0)
    assert math.isclose(q, 6125.0, rel_tol=1e-9)


def test_dynamic_pressure_rejects_negative_velocity():
    with pytest.raises(aero.AerodynamicsError):
        aero.dynamic_pressure(1.225, -10.0)


def test_lift_known_value():
    # q=6125, S=16, CL=0.5 -> L = 6125*16*0.5 = 49000 N
    l = aero.lift(density_kg_m3=1.225, velocity_mps=100.0, wing_area_m2=16.0, cl=0.5)
    assert math.isclose(l, 49000.0, rel_tol=1e-6)


def test_drag_known_value():
    d = aero.drag(density_kg_m3=1.225, velocity_mps=100.0, wing_area_m2=16.0, cd=0.05)
    assert math.isclose(d, 4900.0, rel_tol=1e-6)


def test_lift_rejects_non_positive_wing_area():
    with pytest.raises(aero.AerodynamicsError):
        aero.lift(density_kg_m3=1.225, velocity_mps=100.0, wing_area_m2=0.0, cl=0.5)
    with pytest.raises(aero.AerodynamicsError):
        aero.drag(density_kg_m3=1.225, velocity_mps=100.0, wing_area_m2=-1.0, cd=0.05)


def test_lift_to_drag_normal_case():
    assert math.isclose(aero.lift_to_drag(1000.0, 100.0), 10.0, rel_tol=1e-9)


def test_lift_to_drag_zero_drag_is_inf_not_crash():
    assert aero.lift_to_drag(1000.0, 0.0) == float("inf")


def test_lift_to_drag_zero_zero_is_zero():
    assert aero.lift_to_drag(0.0, 0.0) == 0.0


def test_lift_to_drag_rejects_negative_drag():
    with pytest.raises(aero.AerodynamicsError):
        aero.lift_to_drag(1000.0, -5.0)


def test_weight_known_value():
    # m=1000 kg -> W = 1000 * 9.80665 = 9806.65 N
    w = perf.weight(1000.0)
    assert math.isclose(w, 9806.65, rel_tol=1e-9)


def test_weight_rejects_negative_mass():
    with pytest.raises(perf.PerformanceError):
        perf.weight(-100.0)


def test_compute_performance_end_to_end_sea_level():
    state = perf.AircraftState(
        altitude_m=0.0,
        temperature_k=288.15,
        pressure_pa=101325.0,
        velocity_mps=51.4444,   # ~100 kt
        wing_area_m2=16.17,     # ~174 ft^2 (roughly a C172-class wing)
        mass_kg=1043.26,        # ~2300 lb
        cl=0.6,
        cd=0.06,
    )
    result = perf.compute_performance(state)
    assert math.isclose(result.atmosphere.density_kg_m3, 1.225, rel_tol=1e-3)
    assert result.aero.lift_n > 0
    assert result.aero.drag_n > 0
    assert math.isclose(result.aero.l_over_d, result.aero.lift_n / result.aero.drag_n, rel_tol=1e-9)
    assert math.isclose(result.weight_n, 1043.26 * 9.80665, rel_tol=1e-6)


def test_velocity_sweep_shapes_and_monotonic_lift():
    state = perf.AircraftState(
        altitude_m=0.0, temperature_k=288.15, pressure_pa=101325.0,
        velocity_mps=50.0, wing_area_m2=16.0, mass_kg=1000.0, cl=0.5, cd=0.05,
    )
    v, l, d, ld = perf.velocity_sweep(state, v_min_mps=10.0, v_max_mps=100.0, num_points=10)
    assert len(v) == len(l) == len(d) == len(ld) == 10
    # Lift and drag both increase with V^2 for fixed CL, CD -> strictly increasing
    assert all(l[i] < l[i + 1] for i in range(len(l) - 1))
    assert all(d[i] < d[i + 1] for i in range(len(d) - 1))

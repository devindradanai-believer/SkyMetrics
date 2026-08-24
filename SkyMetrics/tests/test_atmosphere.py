"""Tests for src.physics.atmosphere."""

import math
import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.physics import atmosphere as atm


def test_isa_sea_level_temperature():
    assert math.isclose(atm.isa_temperature(0.0), 288.15, rel_tol=1e-9)


def test_isa_sea_level_pressure():
    assert math.isclose(atm.isa_pressure(0.0), 101325.0, rel_tol=1e-9)


def test_isa_sea_level_density():
    state = atm.isa_atmosphere(0.0)
    assert math.isclose(state.density_kg_m3, 1.225, rel_tol=1e-3)


def test_isa_11000m_matches_published_tropopause_values():
    # Published ISA tropopause: T = 216.65 K, p ~= 22632 Pa
    state = atm.isa_atmosphere(11000.0)
    assert math.isclose(state.temperature_k, 216.65, rel_tol=1e-4)
    assert math.isclose(state.pressure_pa, 22632.0, rel_tol=2e-3)


def test_isa_temperature_decreases_with_altitude_in_troposphere():
    t_low = atm.isa_temperature(1000.0)
    t_high = atm.isa_temperature(5000.0)
    assert t_high < t_low


def test_isa_isothermal_layer_constant_temperature():
    t1 = atm.isa_temperature(12000.0)
    t2 = atm.isa_temperature(18000.0)
    assert math.isclose(t1, t2, rel_tol=1e-9)
    assert math.isclose(t1, atm.ISA_T_TROPOPAUSE, rel_tol=1e-9)


def test_altitude_out_of_range_raises():
    with pytest.raises(atm.AtmosphereError):
        atm.isa_temperature(-500.0)
    with pytest.raises(atm.AtmosphereError):
        atm.isa_pressure(25000.0)


def test_air_density_ideal_gas_law():
    rho = atm.air_density(pressure_pa=101325.0, temperature_k=288.15)
    assert math.isclose(rho, 1.225, rel_tol=1e-3)


def test_air_density_rejects_non_positive_pressure():
    with pytest.raises(atm.AtmosphereError):
        atm.air_density(pressure_pa=0.0, temperature_k=288.15)


def test_air_density_rejects_non_positive_temperature():
    with pytest.raises(atm.AtmosphereError):
        atm.air_density(pressure_pa=101325.0, temperature_k=-1.0)


def test_custom_atmosphere_uses_supplied_values_not_isa():
    # Hot, low-pressure "non-standard day" at sea-level altitude label.
    state = atm.custom_atmosphere(altitude_m=0.0, temperature_k=310.0, pressure_pa=99000.0)
    expected_rho = 99000.0 / (atm.R_AIR * 310.0)
    assert math.isclose(state.density_kg_m3, expected_rho, rel_tol=1e-9)
    assert state.temperature_k == 310.0
    assert state.pressure_pa == 99000.0

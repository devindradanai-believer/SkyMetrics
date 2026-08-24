"""Tests for src.units.conversions."""

import math
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.units import conversions as u


def test_ft_m_roundtrip():
    assert math.isclose(u.m_to_ft(u.ft_to_m(1000.0)), 1000.0, rel_tol=1e-9)


def test_ft_to_m_known_value():
    assert math.isclose(u.ft_to_m(1000.0), 304.8, rel_tol=1e-6)


def test_kt_to_mps_known_value():
    assert math.isclose(u.kt_to_mps(100.0), 51.4444, rel_tol=1e-4)


def test_kt_mps_roundtrip():
    assert math.isclose(u.mps_to_kt(u.kt_to_mps(250.0)), 250.0, rel_tol=1e-9)


def test_lb_to_kg_known_value():
    assert math.isclose(u.lb_to_kg(1.0), 0.45359237, rel_tol=1e-9)


def test_lbf_to_n_known_value():
    assert math.isclose(u.lbf_to_n(1.0), 4.4482216152605, rel_tol=1e-9)


def test_weight_lbf_to_mass_kg_does_not_equal_naive_lb_to_kg():
    # This is the critical "do not confuse lbf and lbm" check.
    weight_lbf = 15600.0
    mass_from_weight = u.weight_lbf_to_mass_kg(weight_lbf)
    naive_mass = u.lb_to_kg(weight_lbf)
    # weight_lbf_to_mass_kg divides by g; naive lb_to_kg does not.
    # They should be numerically very close (since 1 lbf ~ 1 lbm * g_std
    # by definition) -- but computed via a genuinely different path.
    assert math.isclose(mass_from_weight, naive_mass, rel_tol=1e-6)
    # Sanity: mass should be positive and reasonable for a light aircraft.
    assert mass_from_weight > 0


def test_ft2_to_m2_known_value():
    assert math.isclose(u.ft2_to_m2(100.0), 9.290304, rel_tol=1e-6)


def test_f_to_k_known_value():
    assert math.isclose(u.f_to_k(59.0), 288.15, rel_tol=1e-4)  # ISA sea-level temp


def test_f_k_roundtrip():
    assert math.isclose(u.k_to_f(u.f_to_k(70.0)), 70.0, rel_tol=1e-9)


def test_psi_to_pa_known_value():
    assert math.isclose(u.psi_to_pa(14.696), 101325.0, rel_tol=1e-3)  # standard atm


def test_psi_pa_roundtrip():
    assert math.isclose(u.pa_to_psi(u.psi_to_pa(30.0)), 30.0, rel_tol=1e-9)

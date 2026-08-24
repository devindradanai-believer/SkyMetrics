"""Tests for src.physics.rocket."""

import math
import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.physics import rocket as rk


def make_config(**overrides):
    defaults = dict(
        dry_mass_kg=1.0, propellant_mass_kg=0.2, thrust_n=100.0,
        burn_time_s=1.5, cd=0.5, reference_area_m2=0.008,
    )
    defaults.update(overrides)
    return rk.RocketConfig(**defaults)


def test_thrust_to_weight_known_value():
    # T=100N, m=1kg -> W=9.80665N -> TWR ~= 10.197
    twr = rk.thrust_to_weight(100.0, 1.0)
    assert math.isclose(twr, 100.0 / 9.80665, rel_tol=1e-9)


def test_thrust_to_weight_rejects_non_positive_mass():
    with pytest.raises(rk.RocketError):
        rk.thrust_to_weight(100.0, 0.0)


def test_thrust_to_weight_rejects_negative_thrust():
    with pytest.raises(rk.RocketError):
        rk.thrust_to_weight(-1.0, 1.0)


def test_get_density_matches_isa_within_range():
    from src.physics.atmosphere import isa_atmosphere
    assert math.isclose(rk.get_density(5000.0), isa_atmosphere(5000.0).density_kg_m3, rel_tol=1e-9)


def test_get_density_extrapolates_above_isa_ceiling():
    from src.physics.atmosphere import isa_atmosphere, MAX_VALID_ALTITUDE_M
    rho_ceiling = isa_atmosphere(MAX_VALID_ALTITUDE_M).density_kg_m3
    rho_above = rk.get_density(MAX_VALID_ALTITUDE_M + 5000.0)
    assert rho_above < rho_ceiling  # density must keep decreasing
    assert rho_above > 0.0


def test_get_density_clamped_below_sea_level():
    assert math.isclose(rk.get_density(-500.0), rk.get_density(0.0), rel_tol=1e-9)


def test_simulate_trajectory_liftoff_reaches_positive_apogee():
    cfg = make_config()
    result = rk.simulate_trajectory(cfg, dt=0.01, max_time_s=60)
    assert result.apogee_m > 0
    assert result.apogee_time_s > 0


def test_simulate_trajectory_apogee_after_burnout():
    cfg = make_config()
    result = rk.simulate_trajectory(cfg, dt=0.01, max_time_s=60)
    assert result.apogee_time_s >= cfg.burn_time_s


def test_simulate_trajectory_mass_decreases_then_holds_constant():
    cfg = make_config()
    result = rk.simulate_trajectory(cfg, dt=0.01, max_time_s=60)
    assert result.mass_kg[0] == pytest.approx(cfg.dry_mass_kg + cfg.propellant_mass_kg)
    # After burnout, mass should equal dry mass
    burnout_index = next(i for i, t in enumerate(result.time_s) if t >= cfg.burn_time_s)
    assert result.mass_kg[burnout_index] == pytest.approx(cfg.dry_mass_kg, rel=1e-6)


def test_simulate_trajectory_lands_back_near_zero_altitude():
    cfg = make_config()
    result = rk.simulate_trajectory(cfg, dt=0.005, max_time_s=120)
    assert result.landing_time_s is not None
    assert result.altitude_m[-1] == pytest.approx(0.0, abs=1e-6)


def test_simulate_trajectory_higher_thrust_gives_higher_apogee():
    low = rk.simulate_trajectory(make_config(thrust_n=60.0), dt=0.01, max_time_s=60)
    high = rk.simulate_trajectory(make_config(thrust_n=150.0), dt=0.01, max_time_s=60)
    assert high.apogee_m > low.apogee_m


def test_simulate_trajectory_more_drag_reduces_apogee():
    low_drag = rk.simulate_trajectory(make_config(cd=0.2), dt=0.01, max_time_s=60)
    high_drag = rk.simulate_trajectory(make_config(cd=1.2), dt=0.01, max_time_s=60)
    assert high_drag.apogee_m < low_drag.apogee_m


def test_simulate_trajectory_rejects_invalid_inputs():
    with pytest.raises(rk.RocketError):
        rk.simulate_trajectory(make_config(dry_mass_kg=0.0))
    with pytest.raises(rk.RocketError):
        rk.simulate_trajectory(make_config(propellant_mass_kg=-1.0))
    with pytest.raises(rk.RocketError):
        rk.simulate_trajectory(make_config(reference_area_m2=0.0))
    with pytest.raises(rk.RocketError):
        rk.simulate_trajectory(make_config(thrust_n=-10.0))


def test_zero_thrust_never_leaves_pad_meaningfully():
    # A "motor" with zero thrust: rocket shouldn't gain altitude.
    cfg = make_config(thrust_n=0.0, propellant_mass_kg=0.0, burn_time_s=0.0)
    result = rk.simulate_trajectory(cfg, dt=0.01, max_time_s=5)
    assert result.apogee_m == pytest.approx(0.0, abs=1e-6)

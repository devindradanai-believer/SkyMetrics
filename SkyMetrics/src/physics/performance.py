"""
Top-level performance-analysis orchestration for SkyMetrics.

Combines the atmosphere and aerodynamics modules into a single
AircraftState -> PerformanceResult pipeline. This is the only module
the GUI layer should call into for a full calculation; it in turn
depends only on the physics sub-modules (atmosphere, aerodynamics)
and never on units or GUI code, keeping the physics engine unit- and
UI-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.physics.atmosphere import (
    G,
    AtmosphereError,
    AtmosphericState,
    custom_atmosphere,
)
from src.physics.aerodynamics import AeroForces, compute_aero_forces


class PerformanceError(ValueError):
    """Raised when a performance calculation cannot be completed."""


@dataclass(frozen=True)
class AircraftState:
    """
    Fully SI-unit description of an aircraft + flight condition, ready
    for the physics engine. Built by the GUI/validation layer from
    user (possibly Imperial) inputs.
    """
    altitude_m: float
    temperature_k: float
    pressure_pa: float
    velocity_mps: float
    wing_area_m2: float
    mass_kg: float
    cl: float
    cd: float


@dataclass(frozen=True)
class PerformanceResult:
    """Full SI-unit performance calculation result."""
    atmosphere: AtmosphericState
    aero: AeroForces
    weight_n: float


def weight(mass_kg: float, g: float = G) -> float:
    """
    Weight force: W = m * g  [N]

    mass_kg : aircraft mass [kg]
    g       : gravitational acceleration [m/s^2], defaults to standard
              gravity (9.80665 m/s^2).
    """
    if mass_kg < 0:
        raise PerformanceError("Mass cannot be negative.")
    return mass_kg * g


def compute_performance(state: AircraftState) -> PerformanceResult:
    """
    Run the full physics pipeline for a given AircraftState (all SI):
    atmosphere -> dynamic pressure -> lift/drag -> weight -> L/D.
    """
    try:
        atmo = custom_atmosphere(
            altitude_m=state.altitude_m,
            temperature_k=state.temperature_k,
            pressure_pa=state.pressure_pa,
        )
    except AtmosphereError as exc:
        raise PerformanceError(str(exc)) from exc

    aero = compute_aero_forces(
        density_kg_m3=atmo.density_kg_m3,
        velocity_mps=state.velocity_mps,
        wing_area_m2=state.wing_area_m2,
        cl=state.cl,
        cd=state.cd,
    )
    w = weight(state.mass_kg)
    return PerformanceResult(atmosphere=atmo, aero=aero, weight_n=w)


def velocity_sweep(
    state: AircraftState, v_min_mps: float, v_max_mps: float, num_points: int = 100
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate Lift, Drag, and L/D as functions of airspeed, holding all
    other AircraftState parameters (altitude/atmosphere, wing area,
    CL, CD, mass) fixed. Used to drive the Lift/Drag/L-D vs Airspeed
    plots.

    Returns
    -------
    (velocities_mps, lift_n, drag_n, l_over_d) as NumPy arrays.
    """
    if v_max_mps <= v_min_mps:
        raise PerformanceError("Max airspeed must be greater than min airspeed.")
    if num_points < 2:
        raise PerformanceError("Need at least 2 points for a velocity sweep.")

    velocities = np.linspace(v_min_mps, v_max_mps, num_points)
    atmo = custom_atmosphere(
        altitude_m=state.altitude_m,
        temperature_k=state.temperature_k,
        pressure_pa=state.pressure_pa,
    )
    rho = atmo.density_kg_m3

    lift_arr = 0.5 * rho * velocities ** 2 * state.wing_area_m2 * state.cl
    drag_arr = 0.5 * rho * velocities ** 2 * state.wing_area_m2 * state.cd

    with np.errstate(divide="ignore", invalid="ignore"):
        ld_arr = np.where(drag_arr != 0, lift_arr / drag_arr, np.inf)

    return velocities, lift_arr, drag_arr, ld_arr

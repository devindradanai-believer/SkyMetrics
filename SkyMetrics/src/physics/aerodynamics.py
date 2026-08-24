"""
Core aerodynamic force equations for SkyMetrics.

All functions operate exclusively on SI-unit inputs and return
SI-unit outputs. Unit conversion is strictly the responsibility of
src.units.conversions -- this module must never contain a conversion
constant.
"""

from __future__ import annotations

from dataclasses import dataclass


class AerodynamicsError(ValueError):
    """Raised for physically invalid aerodynamic inputs."""


def dynamic_pressure(density_kg_m3: float, velocity_mps: float) -> float:
    """
    Dynamic pressure: q = 0.5 * rho * V^2  [Pa]

    density_kg_m3 : air density [kg/m^3]
    velocity_mps  : true airspeed [m/s]
    """
    if density_kg_m3 < 0:
        raise AerodynamicsError("Air density cannot be negative.")
    if velocity_mps < 0:
        raise AerodynamicsError("Airspeed cannot be negative.")
    return 0.5 * density_kg_m3 * velocity_mps ** 2


def lift(density_kg_m3: float, velocity_mps: float, wing_area_m2: float,
          cl: float) -> float:
    """
    Lift force: L = 0.5 * rho * V^2 * S * CL  [N]

    wing_area_m2 : wing reference area [m^2]
    cl           : coefficient of lift [-]
    """
    if wing_area_m2 <= 0:
        raise AerodynamicsError("Wing area must be greater than zero.")
    q = dynamic_pressure(density_kg_m3, velocity_mps)
    return q * wing_area_m2 * cl


def drag(density_kg_m3: float, velocity_mps: float, wing_area_m2: float,
          cd: float) -> float:
    """
    Drag force: D = 0.5 * rho * V^2 * S * CD  [N]

    wing_area_m2 : wing reference area [m^2]
    cd           : coefficient of drag [-]
    """
    if wing_area_m2 <= 0:
        raise AerodynamicsError("Wing area must be greater than zero.")
    q = dynamic_pressure(density_kg_m3, velocity_mps)
    return q * wing_area_m2 * cd


def lift_to_drag(lift_n: float, drag_n: float) -> float:
    """
    Lift-to-drag ratio: L/D = L / D  [-]

    Returns float('inf') when drag is exactly zero and lift is
    positive, 0.0 when both are zero, and raises for negative drag
    (non-physical). Division-by-zero is handled safely rather than
    raising ZeroDivisionError.
    """
    if drag_n < 0:
        raise AerodynamicsError("Drag cannot be negative.")
    if drag_n == 0:
        if lift_n == 0:
            return 0.0
        return float("inf")
    return lift_n / drag_n


@dataclass(frozen=True)
class AeroForces:
    """Bundled aerodynamic results, all SI units."""
    dynamic_pressure_pa: float
    lift_n: float
    drag_n: float
    l_over_d: float


def compute_aero_forces(
    density_kg_m3: float,
    velocity_mps: float,
    wing_area_m2: float,
    cl: float,
    cd: float,
) -> AeroForces:
    """Convenience wrapper computing q, L, D, and L/D together."""
    q = dynamic_pressure(density_kg_m3, velocity_mps)
    l = lift(density_kg_m3, velocity_mps, wing_area_m2, cl)
    d = drag(density_kg_m3, velocity_mps, wing_area_m2, cd)
    ld = lift_to_drag(l, d)
    return AeroForces(dynamic_pressure_pa=q, lift_n=l, drag_n=d, l_over_d=ld)

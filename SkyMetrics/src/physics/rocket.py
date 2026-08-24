"""
Rocket trajectory physics for SkyMetrics.

A separate physics domain from the fixed-wing aircraft engine in
aerodynamics.py / performance.py, but reuses the same SI-only
building blocks wherever the underlying physics is identical:
- Drag: D = 0.5*rho*V^2*S*CD is the same equation for a rocket's
  cross-sectional area/drag coefficient as for a wing -- reused
  directly from src.physics.aerodynamics rather than duplicated.
- Atmosphere: reuses src.physics.atmosphere's ISA model (0-20,000 m)
  for density-vs-altitude, with a documented exponential-decay
  approximation above that range (see get_density docstring).

New physics specific to rockets:
- Thrust-to-weight ratio.
- 1-D vertical trajectory integration (ascent + coast + descent)
  under constant thrust during burn, then gravity + drag only,
  with propellant mass burned off linearly over the burn time.

All functions/dataclasses operate in SI units only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from src.physics.aerodynamics import drag as aero_drag, AerodynamicsError
from src.physics.atmosphere import (
    G, R_AIR, isa_atmosphere, AtmosphereError,
    MIN_VALID_ALTITUDE_M, MAX_VALID_ALTITUDE_M, ISA_RHO0,
)

# Scale height used to extrapolate density above the ISA model's
# supported ceiling (20,000 m). This is an approximation (exponential
# atmosphere with a representative scale height of ~7 km), not a
# second ISA layer -- adequate for showing "thin air, low drag" at
# high-power-rocket altitudes, not for precision above 20 km.
EXTRAPOLATION_SCALE_HEIGHT_M = 7000.0


class RocketError(ValueError):
    """Raised for invalid rocket configuration or simulation inputs."""


@dataclass(frozen=True)
class RocketConfig:
    """Fully SI-unit rocket + motor configuration."""
    dry_mass_kg: float          # airframe + recovery + payload, no propellant
    propellant_mass_kg: float   # propellant mass burned during the motor burn
    thrust_n: float              # constant thrust during burn [N]
    burn_time_s: float           # motor burn duration [s]
    cd: float                    # drag coefficient [-]
    reference_area_m2: float     # cross-sectional reference area [m^2]
    launch_altitude_m: float = 0.0  # launch site altitude above sea level


@dataclass(frozen=True)
class TrajectoryResult:
    """Time-history arrays from a simulated flight, all SI units."""
    time_s: np.ndarray
    altitude_m: np.ndarray
    velocity_mps: np.ndarray
    acceleration_mps2: np.ndarray
    mass_kg: np.ndarray
    apogee_m: float
    apogee_time_s: float
    max_velocity_mps: float
    max_acceleration_mps2: float
    burnout_velocity_mps: float
    burnout_altitude_m: float
    landing_time_s: float | None  # None if simulation ended before landing


def thrust_to_weight(thrust_n: float, mass_kg: float, g: float = G) -> float:
    """
    Thrust-to-weight ratio: TWR = T / (m*g)  [-]

    A TWR < 1 means the rocket cannot lift off (thrust doesn't exceed
    weight); real launches typically want TWR >= ~5 at liftoff for a
    clean pad departure.
    """
    if mass_kg <= 0:
        raise RocketError("Mass must be greater than zero.")
    if thrust_n < 0:
        raise RocketError("Thrust cannot be negative.")
    return thrust_n / (mass_kg * g)


def get_density(altitude_m: float) -> float:
    """
    Air density [kg/m^3] at a given altitude, valid across a wider
    range than the raw ISA model by falling back to an exponential
    approximation above 20,000 m. Below 0 m is clamped to sea level.
    """
    if altitude_m <= MIN_VALID_ALTITUDE_M:
        return isa_atmosphere(MIN_VALID_ALTITUDE_M).density_kg_m3
    if altitude_m <= MAX_VALID_ALTITUDE_M:
        return isa_atmosphere(altitude_m).density_kg_m3
    # Exponential extrapolation anchored at the 20,000 m ISA density.
    rho_20km = isa_atmosphere(MAX_VALID_ALTITUDE_M).density_kg_m3
    delta_h = altitude_m - MAX_VALID_ALTITUDE_M
    return rho_20km * math.exp(-delta_h / EXTRAPOLATION_SCALE_HEIGHT_M)


def _mass_at(t: float, config: RocketConfig) -> float:
    """Instantaneous total mass: dry mass + remaining propellant."""
    if t >= config.burn_time_s or config.burn_time_s <= 0:
        return config.dry_mass_kg
    remaining_fraction = 1.0 - (t / config.burn_time_s)
    return config.dry_mass_kg + config.propellant_mass_kg * remaining_fraction


def _thrust_at(t: float, config: RocketConfig) -> float:
    """Instantaneous thrust: constant during burn, zero after burnout."""
    return config.thrust_n if t < config.burn_time_s else 0.0


def _acceleration(t: float, altitude_m: float, velocity_mps: float, config: RocketConfig) -> float:
    """
    Net vertical acceleration [m/s^2] at a given simulation state:
    a = (Thrust - Drag*sign(v) - Weight) / mass
    Drag always opposes the direction of motion.
    """
    mass = _mass_at(t, config)
    thrust = _thrust_at(t, config)
    weight_n = mass * G

    density = get_density(max(altitude_m, 0.0))
    try:
        drag_n = aero_drag(
            density_kg_m3=density, velocity_mps=abs(velocity_mps),
            wing_area_m2=config.reference_area_m2, cd=config.cd,
        )
    except AerodynamicsError as exc:
        raise RocketError(str(exc)) from exc
    drag_signed = -math.copysign(drag_n, velocity_mps) if velocity_mps != 0 else 0.0

    net_force = thrust - weight_n + drag_signed
    return net_force / mass


def simulate_trajectory(
    config: RocketConfig, dt: float = 0.02, max_time_s: float = 600.0
) -> TrajectoryResult:
    """
    Integrate the 1-D vertical trajectory (ascent, coast to apogee,
    descent) using 4th-order Runge-Kutta on state [altitude, velocity].

    Stops early once the rocket returns to launch altitude (landing)
    or when max_time_s is reached, whichever comes first.
    """
    if config.dry_mass_kg <= 0:
        raise RocketError("Dry mass must be greater than zero.")
    if config.propellant_mass_kg < 0:
        raise RocketError("Propellant mass cannot be negative.")
    if config.burn_time_s < 0:
        raise RocketError("Burn time cannot be negative.")
    if config.reference_area_m2 <= 0:
        raise RocketError("Reference area must be greater than zero.")
    if config.thrust_n < 0:
        raise RocketError("Thrust cannot be negative.")
    if dt <= 0:
        raise RocketError("Time step must be greater than zero.")

    t = 0.0
    h = 0.0  # altitude above launch point
    v = 0.0

    times = [t]
    altitudes = [h]
    velocities = [v]
    accelerations = [_acceleration(t, h, v, config)]
    masses = [_mass_at(t, config)]

    apogee_m = 0.0
    apogee_time_s = 0.0
    landing_time_s: float | None = None

    burnout_velocity_mps = None
    burnout_altitude_m = None

    steps = int(max_time_s / dt)
    for _ in range(steps):
        # RK4 on the 2-state ODE: dh/dt = v, dv/dt = a(t, h, v)
        k1_h = v
        k1_v = _acceleration(t, h, v, config)

        k2_h = v + 0.5 * dt * k1_v
        k2_v = _acceleration(t + 0.5 * dt, h + 0.5 * dt * k1_h, v + 0.5 * dt * k1_v, config)

        k3_h = v + 0.5 * dt * k2_v
        k3_v = _acceleration(t + 0.5 * dt, h + 0.5 * dt * k2_h, v + 0.5 * dt * k2_v, config)

        k4_h = v + dt * k3_v
        k4_v = _acceleration(t + dt, h + dt * k3_h, v + dt * k3_v, config)

        h_next = h + (dt / 6.0) * (k1_h + 2 * k2_h + 2 * k3_h + k4_h)
        v_next = v + (dt / 6.0) * (k1_v + 2 * k2_v + 2 * k3_v + k4_v)
        t_next = t + dt

        if burnout_velocity_mps is None and t_next >= config.burn_time_s:
            burnout_velocity_mps = v_next
            burnout_altitude_m = h_next

        # Ground impact: altitude crosses back to <= 0 after having left the pad
        if h_next <= 0.0 and h > 0.0:
            # Linear interpolation for a cleaner landing time estimate
            frac = h / (h - h_next) if (h - h_next) != 0 else 1.0
            landing_time_s = t + frac * dt
            t, h, v = t_next, max(h_next, 0.0), v_next
            times.append(t); altitudes.append(h); velocities.append(v)
            accelerations.append(_acceleration(t, h, v, config))
            masses.append(_mass_at(t, config))
            break

        t, h, v = t_next, h_next, v_next
        times.append(t)
        altitudes.append(h)
        velocities.append(v)
        accelerations.append(_acceleration(t, h, v, config))
        masses.append(_mass_at(t, config))

        if h > apogee_m:
            apogee_m = h
            apogee_time_s = t

    if burnout_velocity_mps is None:
        burnout_velocity_mps = velocities[-1]
        burnout_altitude_m = altitudes[-1]

    velocities_arr = np.array(velocities)
    accelerations_arr = np.array(accelerations)

    return TrajectoryResult(
        time_s=np.array(times),
        altitude_m=np.array(altitudes),
        velocity_mps=velocities_arr,
        acceleration_mps2=accelerations_arr,
        mass_kg=np.array(masses),
        apogee_m=apogee_m,
        apogee_time_s=apogee_time_s,
        max_velocity_mps=float(np.max(velocities_arr)),
        max_acceleration_mps2=float(np.max(accelerations_arr)),
        burnout_velocity_mps=burnout_velocity_mps,
        burnout_altitude_m=burnout_altitude_m,
        landing_time_s=landing_time_s,
    )

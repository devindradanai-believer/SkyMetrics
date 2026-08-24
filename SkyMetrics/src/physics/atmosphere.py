"""
Atmospheric model for SkyMetrics.

Implements the International Standard Atmosphere (ISA) for the
troposphere and lower stratosphere, plus the ideal-gas-law density
calculation used throughout the physics engine.

All functions here take and return SI units only:
    altitude    [m]
    temperature [K]
    pressure    [Pa]
    density     [kg/m^3]

Valid ISA altitude range
-------------------------
This module implements two ISA layers:
    1. Troposphere: 0 m to 11,000 m, linear lapse rate.
    2. Lower stratosphere: 11,000 m to 20,000 m, isothermal.

Altitudes outside 0-20,000 m are rejected by isa_atmosphere() since
the standard atmosphere model implemented here does not extend
further. This comfortably covers all conventional subsonic/transonic
aircraft operating altitudes.

Assumptions
-----------
- Dry air, no humidity correction.
- ISA mean sea level reference: T0 = 288.15 K, P0 = 101325 Pa.
- Gas is treated as ideal: rho = p / (R * T).
"""

from __future__ import annotations

from dataclasses import dataclass

# ISA sea-level reference conditions
ISA_T0 = 288.15          # K, standard temperature at sea level
ISA_P0 = 101325.0        # Pa, standard pressure at sea level
ISA_RHO0 = 1.225          # kg/m^3, standard density at sea level

# Physical constants
G = 9.80665               # m/s^2, standard gravity
R_AIR = 287.05            # J/(kg*K), specific gas constant for dry air

# ISA layer definitions
TROPOPAUSE_ALT = 11000.0   # m, top of troposphere
STRATOSPHERE_TOP = 20000.0  # m, top of the isothermal layer modeled here
LAPSE_RATE = 0.0065         # K/m, troposphere temperature lapse rate
ISA_T_TROPOPAUSE = ISA_T0 - LAPSE_RATE * TROPOPAUSE_ALT  # 216.65 K

MIN_VALID_ALTITUDE_M = 0.0
MAX_VALID_ALTITUDE_M = STRATOSPHERE_TOP


class AtmosphereError(ValueError):
    """Raised when an atmospheric input is outside the supported range."""


@dataclass(frozen=True)
class AtmosphericState:
    """Bundled atmospheric state at a point, all SI units."""
    altitude_m: float
    temperature_k: float
    pressure_pa: float
    density_kg_m3: float


def isa_temperature(altitude_m: float) -> float:
    """
    Return ISA standard temperature [K] at the given altitude [m].

    Uses a linear lapse rate in the troposphere (0-11,000 m) and a
    constant (isothermal) temperature in the lower stratosphere
    (11,000-20,000 m).
    """
    if altitude_m < MIN_VALID_ALTITUDE_M or altitude_m > MAX_VALID_ALTITUDE_M:
        raise AtmosphereError(
            f"Altitude {altitude_m:.1f} m is outside the supported ISA range "
            f"({MIN_VALID_ALTITUDE_M:.0f} to {MAX_VALID_ALTITUDE_M:.0f} m)."
        )
    if altitude_m <= TROPOPAUSE_ALT:
        return ISA_T0 - LAPSE_RATE * altitude_m
    return ISA_T_TROPOPAUSE


def isa_pressure(altitude_m: float) -> float:
    """
    Return ISA standard pressure [Pa] at the given altitude [m].

    Troposphere uses the standard barometric formula for a linear
    lapse rate; the isothermal stratospheric layer uses the
    exponential barometric formula referenced to the tropopause.
    """
    if altitude_m < MIN_VALID_ALTITUDE_M or altitude_m > MAX_VALID_ALTITUDE_M:
        raise AtmosphereError(
            f"Altitude {altitude_m:.1f} m is outside the supported ISA range "
            f"({MIN_VALID_ALTITUDE_M:.0f} to {MAX_VALID_ALTITUDE_M:.0f} m)."
        )
    if altitude_m <= TROPOPAUSE_ALT:
        base = 1.0 - (LAPSE_RATE * altitude_m) / ISA_T0
        exponent = G / (R_AIR * LAPSE_RATE)
        return ISA_P0 * base ** exponent

    # Isothermal layer: exponential decay referenced to tropopause conditions
    p_tropopause = isa_pressure(TROPOPAUSE_ALT)
    delta_h = altitude_m - TROPOPAUSE_ALT
    import math
    return p_tropopause * math.exp(-G * delta_h / (R_AIR * ISA_T_TROPOPAUSE))


def air_density(pressure_pa: float, temperature_k: float) -> float:
    """
    Compute air density [kg/m^3] from absolute pressure and temperature
    using the ideal gas law: rho = p / (R * T).

    Raises AtmosphereError for non-physical (<= 0) pressure or
    temperature.
    """
    if pressure_pa <= 0:
        raise AtmosphereError("Pressure must be a positive absolute value (Pa).")
    if temperature_k <= 0:
        raise AtmosphereError("Temperature must be a positive absolute value (K).")
    return pressure_pa / (R_AIR * temperature_k)


def isa_atmosphere(altitude_m: float) -> AtmosphericState:
    """
    Return full ISA standard-day atmospheric state at a given altitude.

    Convenience function combining isa_temperature, isa_pressure, and
    air_density for the standard (non-custom) atmosphere case.
    """
    temperature_k = isa_temperature(altitude_m)
    pressure_pa = isa_pressure(altitude_m)
    density = air_density(pressure_pa, temperature_k)
    return AtmosphericState(
        altitude_m=altitude_m,
        temperature_k=temperature_k,
        pressure_pa=pressure_pa,
        density_kg_m3=density,
    )


GAMMA_AIR = 1.4  # ratio of specific heats for dry air (dimensionless)


def speed_of_sound(temperature_k: float) -> float:
    """
    Local speed of sound [m/s] from temperature: a = sqrt(gamma * R * T).

    Used to compute Mach number (V / a) for display purposes; the core
    lift/drag physics in this tool is incompressible and does not
    itself depend on Mach number.
    """
    if temperature_k <= 0:
        raise AtmosphereError("Temperature must be a positive absolute value (K).")
    import math
    return math.sqrt(GAMMA_AIR * R_AIR * temperature_k)


def custom_atmosphere(
    altitude_m: float, temperature_k: float, pressure_pa: float
) -> AtmosphericState:
    """
    Build an AtmosphericState from user-supplied (possibly non-standard)
    temperature and pressure, rather than the ISA model. Density is
    always derived from the ideal gas law using the supplied T and p,
    regardless of whether they match the ISA prediction for the given
    altitude (i.e. this supports non-standard-day conditions).
    """
    density = air_density(pressure_pa, temperature_k)
    return AtmosphericState(
        altitude_m=altitude_m,
        temperature_k=temperature_k,
        pressure_pa=pressure_pa,
        density_kg_m3=density,
    )

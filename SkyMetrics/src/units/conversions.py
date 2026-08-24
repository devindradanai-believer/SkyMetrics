"""
Centralized unit conversion layer for SkyMetrics.

All conversion constants and functions live here. No other module
(GUI or physics) should hardcode a conversion factor. The physics
engine works exclusively in SI units; this module is the only bridge
between user-facing (Metric/Imperial/aviation) units and SI.

IMPORTANT: pounds (lb) as a *weight* input is treated as pounds-force
(lbf), not pounds-mass, unless explicitly noted. See
weight_lbf_to_mass_kg for the correct force -> mass path.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Conversion constants (exact or standard-accepted values)
# ---------------------------------------------------------------------------
FT_PER_M = 3.280839895013123
M_PER_FT = 1.0 / FT_PER_M

KT_PER_MPS = 1.9438444924406046
MPS_PER_KT = 1.0 / KT_PER_MPS

LB_PER_KG = 2.2046226218487757        # mass conversion
KG_PER_LB = 1.0 / LB_PER_KG

STANDARD_GRAVITY = 9.80665            # m/s^2
N_PER_LBF = 4.4482216152605
LBF_PER_N = 1.0 / N_PER_LBF

FT2_PER_M2 = FT_PER_M ** 2
M2_PER_FT2 = 1.0 / FT2_PER_M2

PA_PER_PSI = 6894.757293168361
PSI_PER_PA = 1.0 / PA_PER_PSI

PA_PER_INHG = 3386.389
INHG_PER_PA = 1.0 / PA_PER_INHG


# ---------------------------------------------------------------------------
# Length
# ---------------------------------------------------------------------------
def ft_to_m(value_ft: float) -> float:
    """Convert feet to meters."""
    return value_ft * M_PER_FT


def m_to_ft(value_m: float) -> float:
    """Convert meters to feet."""
    return value_m * FT_PER_M


# ---------------------------------------------------------------------------
# Speed
# ---------------------------------------------------------------------------
def kt_to_mps(value_kt: float) -> float:
    """Convert knots to meters/second."""
    return value_kt * MPS_PER_KT


def mps_to_kt(value_mps: float) -> float:
    """Convert meters/second to knots."""
    return value_mps * KT_PER_MPS


# ---------------------------------------------------------------------------
# Mass and force (weight)
# ---------------------------------------------------------------------------
def lb_to_kg(value_lb: float) -> float:
    """Convert pounds-mass (lbm) to kilograms."""
    return value_lb * KG_PER_LB


def kg_to_lb(value_kg: float) -> float:
    """Convert kilograms to pounds-mass (lbm)."""
    return value_kg * LB_PER_KG


def lbf_to_n(value_lbf: float) -> float:
    """Convert pounds-force (lbf) to newtons."""
    return value_lbf * N_PER_LBF


def n_to_lbf(value_n: float) -> float:
    """Convert newtons to pounds-force (lbf)."""
    return value_n * LBF_PER_N


def weight_lbf_to_mass_kg(weight_lbf: float, g: float = STANDARD_GRAVITY) -> float:
    """
    Convert a *weight* given in pounds-force to a mass in kilograms.

    Correct path for an Imperial "Weight [lb]" field: the value is a
    force (lbf). Convert to newtons, then divide by gravity to get
    mass. Do NOT call lb_to_kg on a weight-in-lbf value -- that would
    silently treat lbf as lbm, which is physically wrong.
    """
    weight_n = lbf_to_n(weight_lbf)
    return weight_n / g


def mass_kg_to_weight_lbf(mass_kg: float, g: float = STANDARD_GRAVITY) -> float:
    """Convert a mass in kilograms to a weight in pounds-force."""
    weight_n = mass_kg * g
    return n_to_lbf(weight_n)


# ---------------------------------------------------------------------------
# Area
# ---------------------------------------------------------------------------
def ft2_to_m2(value_ft2: float) -> float:
    """Convert square feet to square meters."""
    return value_ft2 * M2_PER_FT2


def m2_to_ft2(value_m2: float) -> float:
    """Convert square meters to square feet."""
    return value_m2 * FT2_PER_M2


# ---------------------------------------------------------------------------
# Temperature
# ---------------------------------------------------------------------------
def f_to_k(value_f: float) -> float:
    """Convert degrees Fahrenheit to kelvin."""
    celsius = (value_f - 32.0) * 5.0 / 9.0
    return celsius + 273.15


def k_to_f(value_k: float) -> float:
    """Convert kelvin to degrees Fahrenheit."""
    celsius = value_k - 273.15
    return celsius * 9.0 / 5.0 + 32.0


def c_to_k(value_c: float) -> float:
    """Convert degrees Celsius to kelvin."""
    return value_c + 273.15


def k_to_c(value_k: float) -> float:
    """Convert kelvin to degrees Celsius."""
    return value_k - 273.15


# ---------------------------------------------------------------------------
# Pressure
# ---------------------------------------------------------------------------
def psi_to_pa(value_psi: float) -> float:
    """Convert psi (absolute) to pascals."""
    return value_psi * PA_PER_PSI


def pa_to_psi(value_pa: float) -> float:
    """Convert pascals to psi."""
    return value_pa * PSI_PER_PA


def inhg_to_pa(value_inhg: float) -> float:
    """Convert inches of mercury to pascals."""
    return value_inhg * PA_PER_INHG


def pa_to_inhg(value_pa: float) -> float:
    """Convert pascals to inches of mercury."""
    return value_pa * INHG_PER_PA

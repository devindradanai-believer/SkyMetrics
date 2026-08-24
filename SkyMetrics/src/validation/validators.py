"""
Input validation layer for SkyMetrics.

The GUI passes raw string field values through this module before any
unit conversion or physics calculation happens. Nothing here performs
unit conversion; it only checks that values are numeric and
physically sane. All checks return a list of human-readable error
messages (empty list = valid) so the GUI can display every problem at
once rather than one at a time.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class ValidationError(ValueError):
    """Raised by callers that need a hard-stop on invalid input."""


@dataclass
class FieldSpec:
    """Describes one numeric input field for validation purposes."""
    name: str            # human-readable label, e.g. "Airspeed"
    raw_value: str        # what the user typed
    required: bool = True
    allow_negative: bool = False
    allow_zero: bool = True
    min_value: float | None = None
    max_value: float | None = None


def parse_numeric(field_name: str, raw_value: str, required: bool = True) -> tuple[float | None, list[str]]:
    """
    Attempt to parse raw_value as a float.

    Returns (value_or_None, errors). If the field is empty and not
    required, returns (None, []) with no error.
    """
    errors: list[str] = []
    text = (raw_value or "").strip()

    if not text:
        if required:
            errors.append(f"{field_name}: please enter a value.")
            return None, errors
        return None, errors

    try:
        value = float(text)
    except ValueError:
        errors.append(f"{field_name}: please enter a valid numeric value.")
        return None, errors

    if value != value:  # NaN check
        errors.append(f"{field_name}: value must be a real number.")
        return None, errors

    return value, errors


def validate_field(spec: FieldSpec) -> tuple[float | None, list[str]]:
    """Parse + range-check a single field against its FieldSpec."""
    value, errors = parse_numeric(spec.name, spec.raw_value, spec.required)
    if value is None or errors:
        return value, errors

    if not spec.allow_negative and value < 0:
        errors.append(f"{spec.name} must be greater than or equal to zero.")
    if not spec.allow_zero and value == 0:
        errors.append(f"{spec.name} must be greater than zero.")
    if spec.min_value is not None and value < spec.min_value:
        errors.append(f"{spec.name} must be at least {spec.min_value}.")
    if spec.max_value is not None and value > spec.max_value:
        errors.append(f"{spec.name} must be at most {spec.max_value}.")

    return value, errors


def validate_positive(field_name: str, value: float) -> list[str]:
    """Require value strictly greater than zero."""
    if value <= 0:
        return [f"{field_name} must be greater than zero."]
    return []


def validate_non_negative(field_name: str, value: float) -> list[str]:
    """Require value greater than or equal to zero."""
    if value < 0:
        return [f"{field_name} must be greater than or equal to zero."]
    return []


def validate_coefficient(field_name: str, value: float,
                          low: float = -5.0, high: float = 5.0) -> list[str]:
    """
    Sanity-range check for lift/drag coefficients. Real aircraft CL/CD
    values fall well within [-5, 5]; values outside that band are
    almost certainly a data-entry mistake rather than a valid (if
    extreme) aerodynamic condition, so they are rejected rather than
    silently accepted.
    """
    errors = []
    if value < low or value > high:
        errors.append(
            f"{field_name} = {value:g} is outside the physically plausible "
            f"range [{low}, {high}]."
        )
    return errors


def validate_drag_for_ld(cd: float, drag_n: float) -> list[str]:
    """
    Guard against computing L/D with zero drag. This is a physically
    valid (if degenerate) situation -- e.g. CD = 0 -- so it is not
    itself an error, but the caller must be warned so it can display
    'infinite' rather than crash on a ZeroDivisionError. This function
    is used by the GUI to decide whether to show a warning alongside
    the (safely computed) infinite L/D result.
    """
    warnings = []
    if drag_n == 0:
        warnings.append(
            "Drag is zero (CD = 0): L/D is undefined/infinite for this input."
        )
    return warnings


def validate_temperature_pressure(temperature_k: float, pressure_pa: float) -> list[str]:
    """
    Reject non-physical absolute temperature/pressure combinations
    before they reach the ideal-gas-law density calculation.
    """
    errors = []
    if temperature_k <= 0:
        errors.append("Temperature must be a positive absolute value (> 0 K).")
    if pressure_pa <= 0:
        errors.append("Pressure must be a positive absolute value (> 0 Pa).")
    # Loose sanity bounds: well beyond anything encountered in the
    # atmosphere, flagged as likely data-entry errors rather than
    # physically achievable inputs for this tool's intended envelope.
    if temperature_k and temperature_k > 400:
        errors.append("Temperature seems unrealistically high (> 400 K). Check units.")
    if pressure_pa and pressure_pa > 200000:
        errors.append("Pressure seems unrealistically high (> 200 kPa). Check units.")
    return errors


def validate_altitude(altitude_m: float, min_m: float = 0.0, max_m: float = 20000.0) -> list[str]:
    """Reject altitudes outside the ISA model's supported range."""
    errors = []
    if altitude_m < min_m or altitude_m > max_m:
        errors.append(
            f"Altitude must be between {min_m:.0f} m and {max_m:.0f} m "
            f"({min_m * 3.28084:.0f} ft to {max_m * 3.28084:.0f} ft)."
        )
    return errors

"""Tests for src.validation.validators."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.validation import validators as v


def test_parse_numeric_valid():
    value, errors = v.parse_numeric("Airspeed", "150.5")
    assert value == 150.5
    assert errors == []


def test_parse_numeric_empty_required():
    value, errors = v.parse_numeric("Airspeed", "", required=True)
    assert value is None
    assert len(errors) == 1
    assert "please enter a value" in errors[0]


def test_parse_numeric_empty_not_required():
    value, errors = v.parse_numeric("Pressure", "", required=False)
    assert value is None
    assert errors == []


def test_parse_numeric_non_numeric():
    value, errors = v.parse_numeric("Wing Area", "abc")
    assert value is None
    assert "valid numeric value" in errors[0]


def test_validate_field_negative_wing_area_rejected():
    spec = v.FieldSpec(name="Wing Area", raw_value="-50", allow_negative=False, allow_zero=False)
    value, errors = v.validate_field(spec)
    assert value == -50.0
    assert len(errors) >= 1


def test_validate_field_negative_airspeed_rejected():
    spec = v.FieldSpec(name="Airspeed", raw_value="-10", allow_negative=False)
    value, errors = v.validate_field(spec)
    assert any("greater than or equal to zero" in e for e in errors)


def test_validate_field_zero_not_allowed():
    spec = v.FieldSpec(name="Wing Area", raw_value="0", allow_zero=False)
    _, errors = v.validate_field(spec)
    assert any("greater than zero" in e for e in errors)


def test_validate_positive():
    assert v.validate_positive("Mass", 10.0) == []
    assert len(v.validate_positive("Mass", 0.0)) == 1
    assert len(v.validate_positive("Mass", -1.0)) == 1


def test_validate_non_negative():
    assert v.validate_non_negative("Airspeed", 0.0) == []
    assert len(v.validate_non_negative("Airspeed", -1.0)) == 1


def test_validate_coefficient_in_range():
    assert v.validate_coefficient("CL", 1.2) == []


def test_validate_coefficient_out_of_range():
    errors = v.validate_coefficient("CL", 50.0)
    assert len(errors) == 1


def test_validate_drag_for_ld_zero_drag_warns():
    warnings = v.validate_drag_for_ld(cd=0.0, drag_n=0.0)
    assert len(warnings) == 1


def test_validate_drag_for_ld_nonzero_ok():
    assert v.validate_drag_for_ld(cd=0.05, drag_n=100.0) == []


def test_validate_temperature_pressure_rejects_non_positive():
    errors = v.validate_temperature_pressure(temperature_k=-1.0, pressure_pa=-1.0)
    assert len(errors) >= 2


def test_validate_temperature_pressure_accepts_isa_sea_level():
    errors = v.validate_temperature_pressure(temperature_k=288.15, pressure_pa=101325.0)
    assert errors == []


def test_validate_altitude_within_range():
    assert v.validate_altitude(5000.0) == []


def test_validate_altitude_out_of_range():
    assert len(v.validate_altitude(-100.0)) == 1
    assert len(v.validate_altitude(25000.0)) == 1

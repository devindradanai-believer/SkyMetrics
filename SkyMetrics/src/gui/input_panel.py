"""
Input panel widget for SkyMetrics.

Owns every raw user-entry field (Altitude, Airspeed, Temperature,
Pressure, Wing Area, Mass/Weight, CL, CD), the Metric/Imperial unit
selector, and the "fill ISA standard atmosphere" helper. It performs
NO physics itself: its job is to (a) render fields with correct
aviation-style unit labels for the selected system, (b) preserve
values across a unit-system switch by converting them, and
(c) hand back a validated, fully-SI AircraftState (or a list of
error messages) when asked.
"""

from __future__ import annotations

from dataclasses import dataclass

import customtkinter as ctk

from src.physics.atmosphere import isa_temperature, isa_pressure, AtmosphereError
from src.physics.performance import AircraftState
from src.units import conversions as u
from src.validation import validators as v

METRIC = "Metric"
IMPERIAL = "Imperial"

# Demo/sample values (clearly hypothetical -- not a real aircraft's
# published data). Roughly a small single-engine GA aircraft.
DEMO_VALUES_METRIC = {
    "altitude": "1500",
    "airspeed": "45",
    "temperature": "8.5",
    "pressure": "84.6",
    "wing_area": "16.2",
    "mass_weight": "1050",
    "cl": "0.55",
    "cd": "0.045",
}


@dataclass
class FieldRow:
    """A labeled entry field with a dynamic unit-suffix label."""
    key: str
    entry: ctk.CTkEntry
    unit_label: ctk.CTkLabel
    label: ctk.CTkLabel


class InputPanel(ctk.CTkFrame):
    """Left-hand INPUTS panel: unit selector, fields, Calculate/Reset."""

    def __init__(self, master, on_calculate, on_reset, **kwargs):
        super().__init__(master, **kwargs)
        self.on_calculate = on_calculate
        self.on_reset = on_reset
        self.unit_system = ctk.StringVar(value=METRIC)

        self.grid_columnconfigure(0, weight=1)
        self._build()

    # ------------------------------------------------------------------
    def _build(self) -> None:
        row = 0
        ctk.CTkLabel(
            self, text="INPUTS", font=ctk.CTkFont(size=15, weight="bold")
        ).grid(row=row, column=0, sticky="w", padx=12, pady=(12, 4))
        row += 1

        unit_frame = ctk.CTkFrame(self, fg_color="transparent")
        unit_frame.grid(row=row, column=0, sticky="ew", padx=12, pady=(0, 8))
        unit_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(unit_frame, text="Unit System").grid(row=0, column=0, sticky="w")
        self.unit_switch = ctk.CTkSegmentedButton(
            unit_frame, values=[METRIC, IMPERIAL], variable=self.unit_system,
            command=self._on_unit_system_changed,
        )
        self.unit_switch.grid(row=1, column=0, sticky="ew", pady=(2, 0))
        row += 1

        self.fields: dict[str, FieldRow] = {}
        self._add_field(row, "altitude", "Altitude"); row += 1
        self._add_field(row, "airspeed", "Airspeed"); row += 1
        self._add_field(row, "temperature", "Temperature"); row += 1
        self._add_field(row, "pressure", "Pressure"); row += 1

        isa_frame = ctk.CTkFrame(self, fg_color="transparent")
        isa_frame.grid(row=row, column=0, sticky="ew", padx=12, pady=(0, 6))
        isa_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(
            isa_frame, text="Fill ISA Standard Atmosphere for Altitude",
            command=self._fill_isa, height=26, fg_color="transparent",
            border_width=1, text_color=("gray10", "gray90"),
        ).grid(row=0, column=0, sticky="ew")
        row += 1

        self._add_field(row, "wing_area", "Wing Area"); row += 1
        self._add_field(row, "mass_weight", "Mass/Weight"); row += 1
        self._add_field(row, "cl", "CL (Lift Coefficient)", is_coefficient=True); row += 1
        self._add_field(row, "cd", "CD (Drag Coefficient)", is_coefficient=True); row += 1

        self.error_label = ctk.CTkLabel(
            self, text="", text_color="#E5572C", justify="left",
            wraplength=260, font=ctk.CTkFont(size=11),
        )
        self.error_label.grid(row=row, column=0, sticky="ew", padx=12, pady=(4, 4))
        row += 1

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=row, column=0, sticky="ew", padx=12, pady=(8, 12))
        btn_frame.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(btn_frame, text="Calculate", command=self._handle_calculate).grid(
            row=0, column=0, sticky="ew", padx=(0, 4)
        )
        ctk.CTkButton(
            btn_frame, text="Reset", command=self._handle_reset,
            fg_color="transparent", border_width=1, text_color=("gray10", "gray90"),
        ).grid(row=0, column=1, sticky="ew", padx=(4, 0))
        row += 1

        ctk.CTkButton(
            self, text="Load Demo Values (hypothetical)", command=self._load_demo,
            height=26, fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"),
        ).grid(row=row, column=0, sticky="ew", padx=12, pady=(0, 12))

        self._refresh_unit_labels()

    def _add_field(self, row: int, key: str, label_text: str, is_coefficient: bool = False) -> None:
        wrapper = ctk.CTkFrame(self, fg_color="transparent")
        wrapper.grid(row=row, column=0, sticky="ew", padx=12, pady=3)
        wrapper.grid_columnconfigure(0, weight=1)

        label = ctk.CTkLabel(wrapper, text=label_text, anchor="w")
        label.grid(row=0, column=0, sticky="w")

        entry_row = ctk.CTkFrame(wrapper, fg_color="transparent")
        entry_row.grid(row=1, column=0, sticky="ew")
        entry_row.grid_columnconfigure(0, weight=1)

        entry = ctk.CTkEntry(entry_row, placeholder_text="0" if is_coefficient else "")
        entry.grid(row=0, column=0, sticky="ew")

        unit_label = ctk.CTkLabel(entry_row, text="", width=42, anchor="e")
        unit_label.grid(row=0, column=1, sticky="e", padx=(6, 0))

        self.fields[key] = FieldRow(key=key, entry=entry, unit_label=unit_label, label=label)

    # ------------------------------------------------------------------
    def _unit_suffix(self, key: str) -> str:
        imperial = self.unit_system.get() == IMPERIAL
        return {
            "altitude": "ft" if imperial else "m",
            "airspeed": "kt" if imperial else "m/s",
            "temperature": "\u00b0F" if imperial else "\u00b0C",
            "pressure": "psi" if imperial else "kPa",
            "wing_area": "ft\u00b2" if imperial else "m\u00b2",
            "mass_weight": "lb" if imperial else "kg",
            "cl": "-",
            "cd": "-",
        }[key]

    def _field_label_text(self, key: str) -> str:
        imperial = self.unit_system.get() == IMPERIAL
        base = {
            "altitude": "Altitude",
            "airspeed": "Airspeed",
            "temperature": "Temperature",
            "pressure": "Pressure (absolute)",
            "wing_area": "Wing Area",
            "cl": "CL (Lift Coefficient)",
            "cd": "CD (Drag Coefficient)",
        }
        if key == "mass_weight":
            return "Weight (force)" if imperial else "Mass"
        return base[key]

    def _refresh_unit_labels(self) -> None:
        for key, row in self.fields.items():
            row.unit_label.configure(text=self._unit_suffix(key))
            row.label.configure(text=self._field_label_text(key))

    # ------------------------------------------------------------------
    def _on_unit_system_changed(self, _choice: str) -> None:
        """
        Convert every currently-entered value from the old system to the
        new one, in place, so switching units never corrupts data.
        """
        new_system = self.unit_system.get()
        old_system = IMPERIAL if new_system == METRIC else METRIC
        self._convert_fields(old_system, new_system)
        self._refresh_unit_labels()
        self.error_label.configure(text="")

    def _convert_fields(self, old_system: str, new_system: str) -> None:
        to_imperial = new_system == IMPERIAL

        def convert(key: str, value: float) -> float:
            if key == "altitude":
                return u.m_to_ft(value) if to_imperial else u.ft_to_m(value)
            if key == "airspeed":
                return u.mps_to_kt(value) if to_imperial else u.kt_to_mps(value)
            if key == "temperature":
                # stored value is in the OLD system's unit; convert via K
                kelvin = u.f_to_k(value) if old_system == IMPERIAL else u.c_to_k(value)
                return u.k_to_f(kelvin) if to_imperial else u.k_to_c(kelvin)
            if key == "pressure":
                pa = u.psi_to_pa(value) if old_system == IMPERIAL else value * 1000.0
                return u.pa_to_psi(pa) if to_imperial else pa / 1000.0
            if key == "wing_area":
                return u.m2_to_ft2(value) if to_imperial else u.ft2_to_m2(value)
            if key == "mass_weight":
                if old_system == METRIC and to_imperial:
                    # kg (mass) -> lb (weight force)
                    return u.mass_kg_to_weight_lbf(value)
                if old_system == IMPERIAL and not to_imperial:
                    # lb (weight force) -> kg (mass)
                    return u.weight_lbf_to_mass_kg(value)
                return value
            return value  # cl, cd are dimensionless

        for key, row in self.fields.items():
            text = row.entry.get().strip()
            if not text:
                continue
            try:
                value = float(text)
            except ValueError:
                continue
            new_value = convert(key, value)
            row.entry.delete(0, "end")
            row.entry.insert(0, f"{new_value:.4g}")

    def _fill_isa(self) -> None:
        alt_text = self.fields["altitude"].entry.get().strip()
        if not alt_text:
            self.error_label.configure(text="Enter an altitude first to fill ISA values.")
            return
        try:
            alt_value = float(alt_text)
        except ValueError:
            self.error_label.configure(text="Altitude must be numeric to fill ISA values.")
            return

        imperial = self.unit_system.get() == IMPERIAL
        altitude_m = u.ft_to_m(alt_value) if imperial else alt_value
        try:
            t_k = isa_temperature(altitude_m)
            p_pa = isa_pressure(altitude_m)
        except AtmosphereError as exc:
            self.error_label.configure(text=str(exc))
            return

        temp_row = self.fields["temperature"].entry
        pres_row = self.fields["pressure"].entry
        temp_row.delete(0, "end")
        pres_row.delete(0, "end")
        if imperial:
            temp_row.insert(0, f"{u.k_to_f(t_k):.2f}")
            pres_row.insert(0, f"{u.pa_to_psi(p_pa):.3f}")
        else:
            temp_row.insert(0, f"{u.k_to_c(t_k):.2f}")
            pres_row.insert(0, f"{p_pa / 1000.0:.3f}")
        self.error_label.configure(text="")

    def _load_demo(self) -> None:
        self.unit_system.set(METRIC)
        self._refresh_unit_labels()
        for key, value in DEMO_VALUES_METRIC.items():
            entry = self.fields[key].entry
            entry.delete(0, "end")
            entry.insert(0, value)
        self.error_label.configure(text="")

    def _handle_reset(self) -> None:
        for row in self.fields.values():
            row.entry.delete(0, "end")
        self.error_label.configure(text="")
        self.on_reset()

    def _handle_calculate(self) -> None:
        state, errors = self.build_aircraft_state()
        if errors:
            self.error_label.configure(text="\n".join(errors))
            self.on_calculate(None, self.unit_system.get())
            return
        self.error_label.configure(text="")
        self.on_calculate(state, self.unit_system.get())

    # ------------------------------------------------------------------
    def build_aircraft_state(self) -> tuple[AircraftState | None, list[str]]:
        """Validate all fields and return (AircraftState, errors)."""
        imperial = self.unit_system.get() == IMPERIAL
        errors: list[str] = []
        raw: dict[str, float] = {}

        specs = {
            "altitude": v.FieldSpec("Altitude", self.fields["altitude"].entry.get(), allow_negative=True),
            "airspeed": v.FieldSpec("Airspeed", self.fields["airspeed"].entry.get(), allow_negative=False, allow_zero=False),
            "temperature": v.FieldSpec("Temperature", self.fields["temperature"].entry.get(), allow_negative=True),
            "pressure": v.FieldSpec("Pressure", self.fields["pressure"].entry.get(), allow_negative=False, allow_zero=False),
            "wing_area": v.FieldSpec("Wing Area", self.fields["wing_area"].entry.get(), allow_negative=False, allow_zero=False),
            "mass_weight": v.FieldSpec("Mass/Weight", self.fields["mass_weight"].entry.get(), allow_negative=False, allow_zero=True),
            "cl": v.FieldSpec("CL", self.fields["cl"].entry.get(), allow_negative=True),
            "cd": v.FieldSpec("CD", self.fields["cd"].entry.get(), allow_negative=False),
        }

        for key, spec in specs.items():
            value, field_errors = v.validate_field(spec)
            errors.extend(field_errors)
            if value is not None:
                raw[key] = value

        if errors:
            return None, errors

        errors.extend(v.validate_coefficient("CL", raw["cl"]))
        errors.extend(v.validate_coefficient("CD", raw["cd"], low=0.0, high=5.0))
        if errors:
            return None, errors

        # Convert to SI.
        altitude_m = u.ft_to_m(raw["altitude"]) if imperial else raw["altitude"]
        velocity_mps = u.kt_to_mps(raw["airspeed"]) if imperial else raw["airspeed"]
        temperature_k = u.f_to_k(raw["temperature"]) if imperial else u.c_to_k(raw["temperature"])
        pressure_pa = u.psi_to_pa(raw["pressure"]) if imperial else raw["pressure"] * 1000.0
        wing_area_m2 = u.ft2_to_m2(raw["wing_area"]) if imperial else raw["wing_area"]
        mass_kg = (
            u.weight_lbf_to_mass_kg(raw["mass_weight"]) if imperial else raw["mass_weight"]
        )

        errors.extend(v.validate_altitude(altitude_m))
        errors.extend(v.validate_temperature_pressure(temperature_k, pressure_pa))
        if errors:
            return None, errors

        state = AircraftState(
            altitude_m=altitude_m,
            temperature_k=temperature_k,
            pressure_pa=pressure_pa,
            velocity_mps=velocity_mps,
            wing_area_m2=wing_area_m2,
            mass_kg=mass_kg,
            cl=raw["cl"],
            cd=raw["cd"],
        )
        return state, []

"""
Results panel widget for SkyMetrics.

Displays Air Density, Dynamic Pressure, Lift, Drag, Weight, and L/D
for the most recent successful calculation, formatted in whichever
unit system (Metric/Imperial) is currently selected. Contains no
physics -- it only formats an already-computed PerformanceResult.
"""

from __future__ import annotations

import customtkinter as ctk

from src.physics.performance import PerformanceResult
from src.units import conversions as u

RESULT_ROWS = [
    ("density", "Air Density"),
    ("dynamic_pressure", "Dynamic Pressure"),
    ("lift", "Lift"),
    ("drag", "Drag"),
    ("weight", "Weight"),
    ("ld", "L/D"),
]


class ResultsPanel(ctk.CTkFrame):
    """Right-hand RESULTS panel."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.value_labels: dict[str, ctk.CTkLabel] = {}
        self.unit_labels: dict[str, ctk.CTkLabel] = {}
        self._build()

    def _build(self) -> None:
        row = 0
        ctk.CTkLabel(
            self, text="RESULTS", font=ctk.CTkFont(size=15, weight="bold")
        ).grid(row=row, column=0, sticky="w", padx=12, pady=(12, 8))
        row += 1

        for key, label_text in RESULT_ROWS:
            card = ctk.CTkFrame(self, corner_radius=8)
            card.grid(row=row, column=0, sticky="ew", padx=12, pady=4)
            card.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                card, text=label_text.upper(), font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("gray30", "gray70"),
            ).grid(row=0, column=0, sticky="w", padx=10, pady=(6, 0))

            value_row = ctk.CTkFrame(card, fg_color="transparent")
            value_row.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))
            value_row.grid_columnconfigure(0, weight=1)

            value_label = ctk.CTkLabel(
                value_row, text="\u2014", font=ctk.CTkFont(size=20, weight="bold"), anchor="w"
            )
            value_label.grid(row=0, column=0, sticky="w")
            unit_label = ctk.CTkLabel(
                value_row, text="", font=ctk.CTkFont(size=13), anchor="e",
                text_color=("gray30", "gray70"),
            )
            unit_label.grid(row=0, column=1, sticky="e")

            self.value_labels[key] = value_label
            self.unit_labels[key] = unit_label
            row += 1

        self.warning_label = ctk.CTkLabel(
            self, text="", text_color="#D9A400", justify="left", wraplength=260,
            font=ctk.CTkFont(size=11),
        )
        self.warning_label.grid(row=row, column=0, sticky="ew", padx=12, pady=(4, 12))

    # ------------------------------------------------------------------
    def clear(self) -> None:
        for key, _ in RESULT_ROWS:
            self.value_labels[key].configure(text="\u2014")
            self.unit_labels[key].configure(text="")
        self.warning_label.configure(text="")

    def display(self, result: PerformanceResult, unit_system: str) -> None:
        imperial = unit_system == "Imperial"

        if imperial:
            density = result.atmosphere.density_kg_m3  # slugs/ft^3 rarely used by GA pilots;
            density_txt = f"{density:,.4f}"             # keep kg/m^3 for density even in Imperial
            density_unit = "kg/m\u00b3"

            q_lbf_ft2 = u.n_to_lbf(result.aero.dynamic_pressure_pa) / u.m2_to_ft2(1.0)
            q_txt = f"{q_lbf_ft2:,.3f}"
            q_unit = "lbf/ft\u00b2"

            lift_txt = f"{u.n_to_lbf(result.aero.lift_n):,.1f}"
            lift_unit = "lbf"

            drag_txt = f"{u.n_to_lbf(result.aero.drag_n):,.1f}"
            drag_unit = "lbf"

            weight_txt = f"{u.n_to_lbf(result.weight_n):,.1f}"
            weight_unit = "lbf"
        else:
            density_txt = f"{result.atmosphere.density_kg_m3:,.4f}"
            density_unit = "kg/m\u00b3"

            q_txt = f"{result.aero.dynamic_pressure_pa:,.1f}"
            q_unit = "Pa"

            lift_txt = f"{result.aero.lift_n:,.1f}"
            lift_unit = "N"

            drag_txt = f"{result.aero.drag_n:,.1f}"
            drag_unit = "N"

            weight_txt = f"{result.weight_n:,.1f}"
            weight_unit = "N"

        ld = result.aero.l_over_d
        ld_txt = "\u221e (undefined)" if ld == float("inf") else f"{ld:,.2f}"

        values = {
            "density": (density_txt, density_unit),
            "dynamic_pressure": (q_txt, q_unit),
            "lift": (lift_txt, lift_unit),
            "drag": (drag_txt, drag_unit),
            "weight": (weight_txt, weight_unit),
            "ld": (ld_txt, ""),
        }
        for key, (text, unit) in values.items():
            self.value_labels[key].configure(text=text)
            self.unit_labels[key].configure(text=unit)

        if ld == float("inf"):
            self.warning_label.configure(
                text="Drag is zero: L/D is undefined/infinite for this input."
            )
        else:
            self.warning_label.configure(text="")

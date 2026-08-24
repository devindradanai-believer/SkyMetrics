"""
Matplotlib visualization panel for SkyMetrics.

Owns a single Matplotlib Figure embedded in the CustomTkinter window
via FigureCanvasTkAgg, and knows how to plot Lift, Drag, and L/D as
functions of airspeed for the current aircraft/environment inputs.

This module has no knowledge of raw GUI string fields or Imperial
units -- it is driven by a fully-SI src.physics.performance.AircraftState
plus a "display unit system" flag purely for axis labeling.
"""

from __future__ import annotations

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from src.physics.performance import AircraftState, velocity_sweep
from src.units import conversions as u

PLOT_KIND_LIFT = "Lift vs Airspeed"
PLOT_KIND_DRAG = "Drag vs Airspeed"
PLOT_KIND_LD = "L/D vs Airspeed"
PLOT_KINDS = [PLOT_KIND_LIFT, PLOT_KIND_DRAG, PLOT_KIND_LD]


class PlotPanel(ctk.CTkFrame):
    """Frame containing the plot-kind selector and the Matplotlib canvas."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header, text="Performance Visualization",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        self.plot_kind_var = ctk.StringVar(value=PLOT_KIND_LIFT)
        self.plot_selector = ctk.CTkOptionMenu(
            header, values=PLOT_KINDS, variable=self.plot_kind_var,
            command=lambda _choice: self.refresh(),
        )
        self.plot_selector.grid(row=0, column=2, sticky="e")

        self.figure = Figure(figsize=(7.5, 3.2), dpi=100)
        self.axes = self.figure.add_subplot(111)
        self.figure.subplots_adjust(left=0.11, right=0.97, top=0.90, bottom=0.18)

        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        self._last_state: AircraftState | None = None
        self._last_unit_system: str = "Metric"
        self._show_placeholder("Enter inputs and press Calculate to see plots.")

    # ------------------------------------------------------------------
    def _show_placeholder(self, message: str) -> None:
        self.axes.clear()
        self.axes.text(
            0.5, 0.5, message, ha="center", va="center",
            transform=self.axes.transAxes, fontsize=11, color="gray",
        )
        self.axes.set_xticks([])
        self.axes.set_yticks([])
        for spine in self.axes.spines.values():
            spine.set_visible(False)
        self.canvas.draw_idle()

    def update_state(self, state: AircraftState | None, unit_system: str) -> None:
        """Store the latest valid AircraftState and redraw the active plot."""
        self._last_state = state
        self._last_unit_system = unit_system
        self.refresh()

    def refresh(self) -> None:
        """Redraw whichever plot kind is currently selected."""
        state = self._last_state
        if state is None:
            self._show_placeholder("Enter inputs and press Calculate to see plots.")
            return
        if state.wing_area_m2 <= 0:
            self._show_placeholder("Wing area must be > 0 to plot performance.")
            return

        kind = self.plot_kind_var.get()
        imperial = self._last_unit_system == "Imperial"

        v_center = max(state.velocity_mps, 1.0)
        v_min = max(v_center * 0.2, 0.5)
        v_max = v_center * 2.0
        velocities, lift_arr, drag_arr, ld_arr = velocity_sweep(
            state, v_min_mps=v_min, v_max_mps=v_max, num_points=120
        )

        self.axes.clear()

        if imperial:
            x = [u.mps_to_kt(v) for v in velocities]
            x_label = "Airspeed [kt]"
        else:
            x = velocities
            x_label = "Airspeed [m/s]"

        if kind == PLOT_KIND_LIFT:
            y = [u.n_to_lbf(val) for val in lift_arr] if imperial else lift_arr
            y_label = "Lift [lbf]" if imperial else "Lift [N]"
            title = "Lift vs Airspeed"
            self.axes.plot(x, y, color="#2C7BE5", linewidth=2, label="Lift")
        elif kind == PLOT_KIND_DRAG:
            y = [u.n_to_lbf(val) for val in drag_arr] if imperial else drag_arr
            y_label = "Drag [lbf]" if imperial else "Drag [N]"
            title = "Drag vs Airspeed"
            self.axes.plot(x, y, color="#E5572C", linewidth=2, label="Drag")
        else:
            y = ld_arr
            y_label = "L/D [-]"
            title = "Lift-to-Drag Ratio vs Airspeed"
            self.axes.plot(x, y, color="#2CA02C", linewidth=2, label="L/D")

        # Mark current operating point
        current_v = u.mps_to_kt(state.velocity_mps) if imperial else state.velocity_mps
        self.axes.axvline(current_v, color="gray", linestyle="--", linewidth=1, alpha=0.7)

        self.axes.set_xlabel(x_label)
        self.axes.set_ylabel(y_label)
        self.axes.set_title(title, fontsize=11)
        self.axes.grid(True, alpha=0.3)
        self.axes.legend(loc="upper left", fontsize=8)

        self.canvas.draw_idle()

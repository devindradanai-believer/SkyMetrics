"""
Top-level CustomTkinter application window for SkyMetrics.

Wires the InputPanel, ResultsPanel, and PlotPanel together. This
module contains no physics or unit-conversion logic of its own; it
only orchestrates: (input_panel.build_aircraft_state) ->
(physics.performance.compute_performance) -> (results_panel.display,
plots.update_state).
"""

from __future__ import annotations

import logging

import customtkinter as ctk

from src.gui.input_panel import InputPanel
from src.gui.plots import PlotPanel
from src.gui.results_panel import ResultsPanel
from src.physics.performance import PerformanceError, compute_performance

logger = logging.getLogger("aeroscope")

ctk.set_default_color_theme("blue")


class SkyMetricsApp(ctk.CTk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()

        self.title("SkyMetrics \u2014 Aircraft Performance Analysis")
        self.geometry("1180x760")
        self.minsize(980, 640)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_body()

    # ------------------------------------------------------------------
    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, corner_radius=0, height=64)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.grid(row=0, column=0, sticky="w", padx=16, pady=10)
        ctk.CTkLabel(
            title_box, text="SkyMetrics", font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            title_box, text="Aircraft Performance Analysis",
            font=ctk.CTkFont(size=12), text_color=("gray30", "gray70"),
        ).grid(row=1, column=0, sticky="w")

        self.appearance_switch = ctk.CTkSegmentedButton(
            header, values=["Light", "Dark", "System"],
            command=self._on_appearance_changed,
        )
        self.appearance_switch.set("System")
        self.appearance_switch.grid(row=0, column=1, sticky="e", padx=16, pady=10)

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=12, pady=(4, 6))
        body.grid_columnconfigure(0, weight=0, minsize=300)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self.input_panel = InputPanel(
            body, on_calculate=self._on_calculate, on_reset=self._on_reset,
            corner_radius=10,
        )
        self.input_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.results_panel = ResultsPanel(body, corner_radius=10)
        self.results_panel.grid(row=0, column=1, sticky="nsew")

        self.plot_panel = PlotPanel(self, corner_radius=10)
        self.plot_panel.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))

    # ------------------------------------------------------------------
    def _on_appearance_changed(self, choice: str) -> None:
        ctk.set_appearance_mode(choice)

    def _on_calculate(self, state, unit_system: str) -> None:
        if state is None:
            # Validation failed; input_panel already displayed the errors.
            self.results_panel.clear()
            self.plot_panel.update_state(None, unit_system)
            return
        try:
            result = compute_performance(state)
        except PerformanceError as exc:
            logger.warning("Performance calculation failed: %s", exc)
            self.input_panel.error_label.configure(text=str(exc))
            self.results_panel.clear()
            self.plot_panel.update_state(None, unit_system)
            return
        except Exception:
            logger.exception("Unexpected error during performance calculation.")
            self.input_panel.error_label.configure(
                text="An unexpected error occurred. Please check your inputs."
            )
            self.results_panel.clear()
            self.plot_panel.update_state(None, unit_system)
            return

        self.results_panel.display(result, unit_system)
        self.plot_panel.update_state(state, unit_system)

    def _on_reset(self) -> None:
        self.results_panel.clear()
        self.plot_panel.update_state(None, self.input_panel.unit_system.get())


def run() -> None:
    """Configure logging and launch the SkyMetrics application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    ctk.set_appearance_mode("System")
    app = SkyMetricsApp()
    app.mainloop()

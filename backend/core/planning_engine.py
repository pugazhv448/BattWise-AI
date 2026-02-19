"""
Planning engine (agentic core): generates 24h energy plan from stress result.
Values are derived dynamically from actual simulation telemetry so that
changing the simulation inputs (capacity, initial SoC, days) flows through
to Min SoC Reserve, Daily Energy Budget, Heavy Appliance Window.
"""
from typing import List, Optional

from backend.models.battery_models import (
    EnergyPlan,
    EnergyPlanItem,
    SimulationResult,
    StressFactor,
    StressResult,
    TelemetryPoint,
)


class PlanningEngine:
    """
    Produces a 24-hour energy plan and recommendations from stress evaluation.
    When a SimulationResult is provided, values are derived from actual telemetry.
    """

    DEFAULT_MIN_SOC     = 20.0   # % – fallback when no telemetry
    DEFAULT_HEAVY_START = 10.0   # 10:00 – solar high
    DEFAULT_HEAVY_END   = 15.0   # 15:00
    DEFAULT_BUDGET_KWH  = 8.0    # kWh – fallback

    # ── Public entry point ─────────────────────────────────────────────────

    def generate(
        self,
        stress_result: StressResult,
        simulation: Optional[SimulationResult] = None,
    ) -> EnergyPlan:
        """
        Build 24h plan: time windows, min SoC, heavy-appliance window, budget, mitigations.
        All numeric outputs are derived directly from simulation telemetry when available.
        """
        mitigations: List[str] = []

        # ── 1. Min SoC Reserve ────────────────────────────────────────────
        # Strictly observed minimum SoC + 3% buffer.
        # e.g. if simulation drops to 12%, suggest 15%. If it drops to 48%, suggest 51%.
        if simulation and simulation.telemetry:
            observed_min = min(p.soc_percent for p in simulation.telemetry)
            min_soc = round(observed_min + 3.0)
            # Ensure at least 10% absolute floor for safety
            min_soc = max(10.0, min_soc)
        else:
            min_soc = self.DEFAULT_MIN_SOC

        # Override up if deep discharge is a real problem
        if any(f.name == "Deep discharge" and f.contribution > 0.3
               for f in stress_result.stress_factors):
            min_soc = max(min_soc, 25.0)
            mitigations.append(
                f"Raise minimum SoC to {min_soc:.0f}% to avoid deep discharge."
            )
        else:
            mitigations.append(
                "Avoid holding SoC above 90% for long; discharge to 80–85% after peak sun."
            )

        # ── 2. Heavy Appliance Window ─────────────────────────────────────
        # Find the best 4-hour window for heavy loads based on average SoC
        if simulation and simulation.telemetry:
            heavy_start, heavy_end = self._best_load_window(simulation.telemetry, window_hours=4)
        else:
            heavy_start = self.DEFAULT_HEAVY_START
            heavy_end   = self.DEFAULT_HEAVY_END

        if any(f.name == "Rapid discharge" and f.contribution > 0.3
               for f in stress_result.stress_factors):
            mitigations.append(
                f"Run heavy appliances between {int(heavy_start):02d}:00 and "
                f"{int(heavy_end):02d}:00 when solar is high."
            )
        else:
            mitigations.append(
                f"Prefer {int(heavy_start):02d}:00–{int(heavy_end):02d}:00 for heavy loads."
            )

        # ── 3. Daily Energy Budget ────────────────────────────────────────
        # Strictly (Capacity * Usable% / Days)
        # e.g. 10kWh * 50% usable / 5 days = 1.0 kWh/day
        if simulation:
            usable_percent = max(0.0, simulation.initial_soc_percent - min_soc)
            total_usable_kwh = (simulation.capacity_kwh * usable_percent) / 100.0
            num_days = max(1, simulation.num_days)
            budget = round(total_usable_kwh / num_days, 1)
        else:
            budget = self.DEFAULT_BUDGET_KWH

        # ── 4. Remaining mitigations from stress factors ──────────────────
        for f in stress_result.stress_factors:
            if f.mitigation_action and f.mitigation_action not in mitigations:
                mitigations.append(f.mitigation_action)

        # ── 5. 24h plan windows ───────────────────────────────────────────
        items = [
            EnergyPlanItem(0.0, 6.0, "Night reserve",
                           recommended_soc_min=min_soc,
                           recommended_action="Keep above reserve."),
            EnergyPlanItem(6.0, heavy_start, "Morning charge",
                           recommended_soc_min=None,
                           recommended_action="Let solar charge."),
            EnergyPlanItem(heavy_start, heavy_end, "Heavy appliance window",
                           recommended_soc_min=None,
                           recommended_action="Run washer, dryer, etc."),
            EnergyPlanItem(heavy_end, 18.0, "Afternoon charge",
                           recommended_soc_min=None,
                           recommended_action="Top up if needed."),
            EnergyPlanItem(18.0, 24.0, "Evening use",
                           recommended_soc_min=min_soc,
                           recommended_action="Minimize discharge rate."),
        ]

        return EnergyPlan(
            items=items,
            min_soc_threshold_percent=min_soc,
            heavy_appliance_window_start=heavy_start,
            heavy_appliance_window_end=heavy_end,
            daily_energy_budget_kwh=budget,
            mitigations=list(dict.fromkeys(mitigations)),  # dedupe, preserve order
        )

    # ── Helpers ────────────────────────────────────────────────────────────

    def _best_load_window(
        self,
        telemetry: List[TelemetryPoint],
        window_hours: int = 4,
    ) -> tuple:
        """
        Find the consecutive `window_hours`-wide block of hours (0–23) that has
        the highest average SoC across all simulation days.
        """
        if not telemetry:
            return self.DEFAULT_HEAVY_START, self.DEFAULT_HEAVY_END

        # Aggregate mean SoC per hour-of-day
        hour_soc: dict = {}
        hour_count: dict = {}
        for p in telemetry:
            h = int(p.hour) % 24
            hour_soc[h]   = hour_soc.get(h, 0.0)   + p.soc_percent
            hour_count[h] = hour_count.get(h, 0)    + 1

        mean_by_hour = {
            h: hour_soc[h] / hour_count[h]
            for h in hour_soc
        }

        # Slide window; pick best start (clamp end to ≤ 22)
        best_start = int(self.DEFAULT_HEAVY_START)
        best_score = -1.0
        # Check hours 6..18 (sunlight)
        for start in range(6, 19):
            end = start + window_hours
            if end > 22:
                break
            score = sum(mean_by_hour.get(h, 0.0) for h in range(start, end))
            if score > best_score:
                best_score = score
                best_start = start

        return float(best_start), float(best_start + window_hours)

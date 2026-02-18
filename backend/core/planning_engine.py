"""
Planning engine (agentic core): generates 24h energy plan from stress result.
Maps each stress factor to a mitigation; suggests min SoC, heavy-appliance window, budget.
"""
from typing import List

from backend.models.battery_models import (
    EnergyPlan,
    EnergyPlanItem,
    StressFactor,
    StressResult,
)


class PlanningEngine:
    """
    Produces a 24-hour energy plan and recommendations from stress evaluation.
    Each stress factor maps to at least one mitigation action.
    """

    DEFAULT_MIN_SOC = 20.0
    DEFAULT_HEAVY_START = 10.0   # 10:00 – solar high
    DEFAULT_HEAVY_END = 15.0     # 15:00
    DEFAULT_BUDGET_KWH = 8.0     # Daily budget example

    def generate(self, stress_result: StressResult) -> EnergyPlan:
        """
        Build 24h plan: time windows, min SoC, heavy-appliance window, budget, mitigations.
        """
        items: List[EnergyPlanItem] = []
        mitigations: List[str] = []

        # Base recommendations from stress
        min_soc = self.DEFAULT_MIN_SOC
        if any(f.name == "Deep discharge" and f.contribution > 0.3 for f in stress_result.stress_factors):
            min_soc = 25.0
            mitigations.append("Raise minimum SoC to 25% to avoid deep discharge.")
        if any(f.name == "Idle high SoC" and f.contribution > 0.3 for f in stress_result.stress_factors):
            mitigations.append("Avoid holding SoC above 90% for long; discharge to 80–85% after peak sun.")

        # Heavy appliance window: suggest when solar is high
        heavy_start = self.DEFAULT_HEAVY_START
        heavy_end = self.DEFAULT_HEAVY_END
        if any(f.name == "Rapid discharge" and f.contribution > 0.3 for f in stress_result.stress_factors):
            mitigations.append("Run heavy appliances between 10:00 and 15:00 when solar is high.")
        else:
            mitigations.append("Prefer 10:00–15:00 for heavy loads to use solar.")

        for f in stress_result.stress_factors:
            if f.mitigation_action and f.mitigation_action not in mitigations:
                mitigations.append(f.mitigation_action)

        # 24h plan windows (simplified: night, morning, solar peak, evening)
        items = [
            EnergyPlanItem(0.0, 6.0, "Night reserve", recommended_soc_min=min_soc, recommended_action="Keep above reserve."),
            EnergyPlanItem(6.0, 10.0, "Morning charge", recommended_soc_min=None, recommended_action="Let solar charge."),
            EnergyPlanItem(10.0, 15.0, "Heavy appliance window", recommended_soc_min=None, recommended_action="Run washer, dryer, etc."),
            EnergyPlanItem(15.0, 18.0, "Afternoon charge", recommended_soc_min=None, recommended_action="Top up if needed."),
            EnergyPlanItem(18.0, 24.0, "Evening use", recommended_soc_min=min_soc, recommended_action="Minimize discharge rate."),
        ]
        budget = self.DEFAULT_BUDGET_KWH
        if stress_result.risk_level.value == "Critical":
            budget = 6.0  # Suggest lower budget when critical
        elif stress_result.risk_level.value == "Warning":
            budget = 7.0

        return EnergyPlan(
            items=items,
            min_soc_threshold_percent=min_soc,
            heavy_appliance_window_start=heavy_start,
            heavy_appliance_window_end=heavy_end,
            daily_energy_budget_kwh=budget,
            mitigations=list(dict.fromkeys(mitigations)),  # dedupe
        )

"""
Verification engine: compares pre-nudge vs post-nudge discharge pattern
and updates stress score delta. Used to validate impact of recommendations.
"""
from typing import List, Optional

from backend.models.battery_models import TelemetryPoint

from backend.core.stress_engine import StressEngine


class VerificationEngine:
    """
    Compares two simulation/telemetry runs (e.g. before and after applying plan)
    and computes stress score delta.
    """

    def __init__(self, stress_engine: Optional[StressEngine] = None):
        self._stress_engine = stress_engine or StressEngine()

    def compare(
        self,
        pre_telemetry: List[TelemetryPoint],
        post_telemetry: List[TelemetryPoint],
        pre_initial_soc: float,
        post_initial_soc: float,
        pre_cloudy_days: Optional[List[int]] = None,
        post_cloudy_days: Optional[List[int]] = None,
    ) -> dict:
        """
        Returns dict with pre_stress_score, post_stress_score, delta, improved (bool).
        """
        self._stress_engine.set_anomaly(False)
        pre_result = self._stress_engine.evaluate(pre_telemetry, pre_initial_soc, pre_cloudy_days)
        post_result = self._stress_engine.evaluate(post_telemetry, post_initial_soc, post_cloudy_days)
        delta = post_result.stress_score - pre_result.stress_score
        return {
            "pre_stress_score": pre_result.stress_score,
            "post_stress_score": post_result.stress_score,
            "delta": round(delta, 1),
            "improved": delta < 0,
            "pre_risk_level": pre_result.risk_level.value,
            "post_risk_level": post_result.risk_level.value,
        }

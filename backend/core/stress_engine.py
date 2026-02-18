"""
Stress engine: computes Battery Stress Score (0–100) from telemetry.
Factors: deep discharge, rapid discharge, idle high SoC, consecutive cloudy deficit.
Returns risk_level and stress_factors with mitigation mappings.
"""
from typing import List, Optional

from backend.models.battery_models import (
    RiskLevel,
    StressFactor,
    StressResult,
    TelemetryPoint,
)


class StressEngine:
    """
    Evaluates battery stress from telemetry. All logic is deterministic and offline.
    ML anomaly flag can be set externally (e.g. from anomaly_model).
    """

    DEEP_DISCHARGE_THRESHOLD = 20.0  # % SoC below this counts as deep discharge
    HIGH_SOC_IDLE_THRESHOLD = 90.0   # % SoC above this when idle is stressful
    RAPID_DISCHARGE_C_PER_HOUR = 0.15  # ~C-rate equivalent: 15% per hour is "rapid"
    CLOUDY_DEFICIT_WEIGHT = 1.0      # Consecutive low SoC days

    def __init__(self, anomaly_detected: bool = False):
        self.anomaly_detected = anomaly_detected

    def set_anomaly(self, detected: bool) -> None:
        """Allow ML layer to set anomaly flag."""
        self.anomaly_detected = detected

    def evaluate(
        self,
        telemetry: List[TelemetryPoint],
        initial_soc: float,
        cloudy_days: Optional[List[int]] = None,
    ) -> StressResult:
        """
        Compute stress score and factors from telemetry.
        Time complexity O(n) with n = len(telemetry).
        """
        factors: List[StressFactor] = []
        cloudy = cloudy_days or []

        # 1) Deep discharge: minutes or proportion below 20%
        deep_score, deep_contrib = self._score_deep_discharge(telemetry)
        factors.append(
            StressFactor(
                name="Deep discharge",
                description=f"SoC below {self.DEEP_DISCHARGE_THRESHOLD}% increases wear.",
                contribution=deep_contrib,
                mitigation_action="Raise minimum SoC reserve; avoid discharging below 20%.",
            )
        )

        # 2) Rapid discharge rate
        rapid_score, rapid_contrib = self._score_rapid_discharge(telemetry)
        factors.append(
            StressFactor(
                name="Rapid discharge",
                description="High discharge rate (C-rate) accelerates degradation.",
                contribution=rapid_contrib,
                mitigation_action="Spread heavy loads; use suggested appliance window.",
            )
        )

        # 3) Idle high SoC (calendar aging)
        idle_score, idle_contrib = self._score_idle_high_soc(telemetry)
        factors.append(
            StressFactor(
                name="Idle high SoC",
                description=f"SoC held above {self.HIGH_SOC_IDLE_THRESHOLD}% when not cycling.",
                contribution=idle_contrib,
                mitigation_action="Allow discharge to 80–85% after full charge when possible.",
            )
        )

        # 4) Consecutive cloudy-day deficit
        cloudy_score, cloudy_contrib = self._score_cloudy_deficit(telemetry, cloudy)
        factors.append(
            StressFactor(
                name="Cloudy-day deficit",
                description="Repeated low SoC days increase stress.",
                contribution=cloudy_contrib,
                mitigation_action="Increase reserve on clear days; reduce non-essential load on cloudy days.",
            )
        )

        # 5) Anomaly (from ML)
        anomaly_contrib = 0.2 if self.anomaly_detected else 0.0
        if self.anomaly_detected:
            factors.append(
                StressFactor(
                    name="Anomalous discharge",
                    description="Unusual discharge pattern detected.",
                    contribution=anomaly_contrib,
                    mitigation_action="Review load patterns; check for unexpected consumption.",
                )
            )

        # Weighted sum of contributions (each 0–1), scaled to 0–100. Cap at 100.
        sum_contrib = deep_contrib + rapid_contrib + idle_contrib + cloudy_contrib + anomaly_contrib
        # Scale so that 4 factors at 0.5 each ≈ 50; allow anomaly to add up to 20
        stress_score = min(100.0, sum_contrib * 25.0)

        risk_level = self._risk_level(stress_score)
        return StressResult(
            stress_score=round(stress_score, 1),
            risk_level=risk_level,
            stress_factors=factors,
            anomaly_detected=self.anomaly_detected,
        )

    def _score_deep_discharge(self, telemetry: List[TelemetryPoint]) -> tuple:
        """Return (raw score 0–1, contribution 0–1)."""
        if not telemetry:
            return 0.0, 0.0
        below = sum(1 for p in telemetry if p.soc_percent < self.DEEP_DISCHARGE_THRESHOLD)
        ratio = below / len(telemetry)
        # Severity: how low did we go?
        min_soc = min(p.soc_percent for p in telemetry)
        severity = 1.0 - (min_soc / self.DEEP_DISCHARGE_THRESHOLD) if min_soc < self.DEEP_DISCHARGE_THRESHOLD else 0.0
        severity = max(0, severity)
        contrib = min(1.0, (ratio * 0.5 + severity * 0.5))
        return ratio, contrib

    def _score_rapid_discharge(self, telemetry: List[TelemetryPoint]) -> tuple:
        """Rate of discharge per hour; high rate -> high contribution."""
        if len(telemetry) < 2:
            return 0.0, 0.0
        max_drop = 0.0
        for i in range(1, len(telemetry)):
            dt = telemetry[i].hour - telemetry[i - 1].hour
            if dt <= 0:
                dt = 1.0  # same hour next day or step
            delta = telemetry[i - 1].soc_percent - telemetry[i].soc_percent
            if delta > 0:  # discharge
                rate_per_hour = delta / dt
                max_drop = max(max_drop, rate_per_hour)
        # 15% per hour = 1.0
        contrib = min(1.0, max_drop / (self.RAPID_DISCHARGE_C_PER_HOUR * 100))
        return max_drop / 100.0, contrib

    def _score_idle_high_soc(self, telemetry: List[TelemetryPoint]) -> tuple:
        """Proportion of time at high SoC with little net discharge (idle)."""
        if not telemetry:
            return 0.0, 0.0
        high_idle = 0
        for p in telemetry:
            if p.soc_percent >= self.HIGH_SOC_IDLE_THRESHOLD and p.net_power_kw >= -0.1:
                high_idle += 1
        ratio = high_idle / len(telemetry)
        return ratio, min(1.0, ratio * 1.5)

    def _score_cloudy_deficit(self, telemetry: List[TelemetryPoint], cloudy_days: List[int]) -> tuple:
        """Stress from consecutive cloudy days (low end-of-day SoC)."""
        if not cloudy_days or not telemetry:
            return 0.0, 0.0
        # End-of-day SoC for each day (assume 24 points per day)
        points_per_day = 24
        num_days = (len(telemetry) + points_per_day - 1) // points_per_day
        low_soc_days = 0
        for d in range(num_days):
            if d not in cloudy_days:
                continue
            idx = min((d + 1) * points_per_day - 1, len(telemetry) - 1)
            if telemetry[idx].soc_percent < 40:
                low_soc_days += 1
        contrib = min(1.0, low_soc_days / max(len(cloudy_days), 1))
        return low_soc_days / max(num_days, 1), contrib

    def _risk_level(self, score: float) -> RiskLevel:
        """Map stress score to risk level."""
        if score < 35:
            return RiskLevel.SAFE
        if score < 65:
            return RiskLevel.WARNING
        return RiskLevel.CRITICAL

"""
Minimal sanity tests: stress score range, SoC bounds, plan generation.
Run from project root: pytest tests/ -v
"""
import pytest

from backend.core import PlanningEngine, SimulationEngine, StressEngine
from backend.models.battery_models import RiskLevel, StressResult


def test_stress_score_range() -> None:
    """Stress score must be in [0, 100]."""
    engine = StressEngine()
    sim_engine = SimulationEngine(capacity_kwh=10.0)
    result = sim_engine.run(num_days=1, initial_soc_percent=80.0)
    stress = engine.evaluate(result.telemetry, result.initial_soc_percent, [])
    assert 0 <= stress.stress_score <= 100
    assert stress.risk_level in (RiskLevel.SAFE, RiskLevel.WARNING, RiskLevel.CRITICAL)


def test_soc_not_exceeding_bounds() -> None:
    """Simulated SoC must stay within [min_soc, max_soc]."""
    sim = SimulationEngine(capacity_kwh=10.0, min_soc_percent=20.0, max_soc_percent=95.0)
    result = sim.run(num_days=3, initial_soc_percent=50.0, cloudy_day_indices={1})
    for p in result.telemetry:
        assert 20.0 <= p.soc_percent <= 95.0


def test_plan_generation_logic() -> None:
    """Planning engine must return plan with items and mitigations from stress."""
    stress = StressResult(
        stress_score=45.0,
        risk_level=RiskLevel.WARNING,
        stress_factors=[],
        anomaly_detected=False,
    )
    plan_engine = PlanningEngine()
    plan = plan_engine.generate(stress)
    assert len(plan.items) >= 1
    assert plan.min_soc_threshold_percent >= 20.0
    assert plan.heavy_appliance_window_start < plan.heavy_appliance_window_end
    assert plan.daily_energy_budget_kwh > 0

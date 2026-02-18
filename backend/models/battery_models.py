"""
Domain models for battery state, telemetry, and simulation.
Pure data structures; no I/O or external dependencies.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class RiskLevel(str, Enum):
    """Battery stress risk classification."""

    SAFE = "Safe"
    WARNING = "Warning"
    CRITICAL = "Critical"


@dataclass
class StressFactor:
    """Single contributing factor to battery stress."""

    name: str
    description: str
    contribution: float  # 0.0–1.0 weight toward total score
    mitigation_action: str


@dataclass
class TelemetryPoint:
    """Single time-slice of simulated inverter/battery telemetry."""

    hour: float  # 0–24 or continuous for multi-day
    day_index: int  # 0 = today
    solar_kw: float
    load_kw: float
    soc_percent: float
    net_power_kw: float  # solar - load; positive = charging
    is_cloudy: bool = False


@dataclass
class SimulationResult:
    """Output of a full simulation run."""

    telemetry: List[TelemetryPoint] = field(default_factory=list)
    initial_soc_percent: float = 0.0
    final_soc_percent: float = 0.0
    capacity_kwh: float = 0.0
    num_days: int = 1
    cloudy_days: List[int] = field(default_factory=list)  # day indices that were cloudy


@dataclass
class StressResult:
    """Output of stress engine evaluation."""

    stress_score: float  # 0–100
    risk_level: RiskLevel
    stress_factors: List[StressFactor] = field(default_factory=list)
    anomaly_detected: bool = False  # From ML layer


@dataclass
class EnergyPlanItem:
    """Single time window in the 24h energy plan."""

    start_hour: float
    end_hour: float
    label: str
    recommended_soc_min: Optional[float] = None
    recommended_action: str = ""


@dataclass
class EnergyPlan:
    """24-hour energy plan from planning engine."""

    items: List[EnergyPlanItem] = field(default_factory=list)
    min_soc_threshold_percent: float = 20.0
    heavy_appliance_window_start: float = 0.0
    heavy_appliance_window_end: float = 0.0
    daily_energy_budget_kwh: float = 0.0
    mitigations: List[str] = field(default_factory=list)  # Actions tied to stress factors

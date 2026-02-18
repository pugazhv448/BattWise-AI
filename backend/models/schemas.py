"""
Pydantic schemas for API request/response serialization.
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# --- Simulation ---
class SimulateParams(BaseModel):
    """Query params for GET /simulate."""

    days: int = Field(default=1, ge=1, le=14, description="Number of days to simulate")
    initial_soc: float = Field(default=80.0, ge=0.0, le=100.0)
    cloudy_day_indices: Optional[str] = Field(
        default=None,
        description="Comma-separated day indices (0-based) to simulate as cloudy, e.g. '0,2'",
    )
    capacity_kwh: float = Field(default=10.0, ge=0.1, le=100.0)


class TelemetryPointSchema(BaseModel):
    """Single telemetry point for API response."""

    hour: float
    day_index: int
    solar_kw: float
    load_kw: float
    soc_percent: float
    net_power_kw: float
    is_cloudy: bool = False


class SimulateResponse(BaseModel):
    """Response for GET /simulate."""

    telemetry: List[TelemetryPointSchema]
    initial_soc_percent: float
    final_soc_percent: float
    capacity_kwh: float
    num_days: int
    cloudy_days: List[int]


# --- Status (stress) ---
class StressFactorSchema(BaseModel):
    """Single stress factor for API."""

    name: str
    description: str
    contribution: float
    mitigation_action: str


class StatusResponse(BaseModel):
    """Response for GET /status (stress evaluation)."""

    stress_score: float
    risk_level: str  # RiskLevel value
    stress_factors: List[StressFactorSchema]
    anomaly_detected: bool = False


# --- Plan ---
class EnergyPlanItemSchema(BaseModel):
    """Single plan window for API."""

    start_hour: float
    end_hour: float
    label: str
    recommended_soc_min: Optional[float] = None
    recommended_action: str = ""


class PlanResponse(BaseModel):
    """Response for GET /plan."""

    items: List[EnergyPlanItemSchema]
    min_soc_threshold_percent: float
    heavy_appliance_window_start: float
    heavy_appliance_window_end: float
    daily_energy_budget_kwh: float
    mitigations: List[str]


# --- Chat ---
class ChatRequest(BaseModel):
    """Body for POST /chat."""

    message: str = Field(..., min_length=1, max_length=2000)
    context: Optional[Dict[str, Any]] = Field(default=None)


class ChatResponse(BaseModel):
    """Response for POST /chat."""

    reply: str
    from_llm: bool = True
    fallback_message: Optional[str] = None  # Set when LLM failed and we used fallback

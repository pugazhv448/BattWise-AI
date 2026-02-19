"""
BattWise AI FastAPI application.
Exposes /simulate, /status, /plan, POST /chat with structured JSON.
"""
import threading
from typing import List, Optional, Set

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.core import PlanningEngine, SimulationEngine, StressEngine, VerificationEngine
from backend.ml import AnomalyModel
from backend.models.battery_models import (
    RiskLevel,
    SimulationResult,
    StressResult,
    TelemetryPoint,
)
from backend.models.schemas import (
    ChatRequest,
    ChatResponse,
    EnergyPlanItemSchema,
    PlanResponse,
    SimulateResponse,
    StatusResponse,
    StressFactorSchema,
    TelemetryPointSchema,
)
from backend.services import LLMService


def _parse_cloudy_days(s: Optional[str]) -> Set[int]:
    if not s or not s.strip():
        return set()
    out = set()
    for part in s.split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return out


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="BattWise AI",
        description="Battery longevity for LiFePO4 solar households",
        version="1.0.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Shared state (in-memory; replace with DB/cache in production)
    last_simulation: Optional[SimulationResult] = None
    last_stress: Optional[StressResult] = None
    last_plan = None  # EnergyPlan
    anomaly_model = AnomalyModel()
    # Bootstrap anomaly model with one default simulation
    sim_engine = SimulationEngine(
        capacity_kwh=settings.battery_capacity_kwh,
        min_soc_percent=settings.min_soc_percent,
        max_soc_percent=settings.max_soc_percent,
    )
    bootstrap_sims = [
        sim_engine.run(num_days=1, initial_soc_percent=80).telemetry,
        sim_engine.run(num_days=2, initial_soc_percent=70, cloudy_day_indices={1}).telemetry,
    ]
    anomaly_model.fit(bootstrap_sims)

    stress_engine = StressEngine()
    planning_engine = PlanningEngine()
    llm_service = LLMService()

    @app.on_event("startup")
    async def _warmup_llm():
        """Pre-load the Ollama model in a background thread so the first
        user chat message is fast instead of waiting for a cold start."""
        def _ping():
            try:
                import requests as _r
                _r.post(
                    f"{settings.ollama_base_url}/api/generate",
                    json={
                        "model":      settings.ollama_model,
                        "prompt":     "hi",
                        "stream":     False,
                        "keep_alive": 600,
                        "options":    {"num_predict": 1},
                    },
                    timeout=40,
                )
            except Exception:
                pass  # Ollama not running — silently skip
        threading.Thread(target=_ping, daemon=True).start()

    @app.get("/simulate", response_model=SimulateResponse)
    def simulate(
        days: int = Query(1, ge=1, le=14),
        initial_soc: float = Query(80.0, ge=0.0, le=100.0),
        cloudy_day_indices: Optional[str] = Query(None),
        capacity_kwh: float = Query(10.0, ge=0.1, le=100.0),
    ):
        """Run multi-day simulation; returns telemetry and summary."""
        nonlocal last_simulation
        cloudy = _parse_cloudy_days(cloudy_day_indices)
        engine = SimulationEngine(
            capacity_kwh=capacity_kwh,
            min_soc_percent=settings.min_soc_percent,
            max_soc_percent=settings.max_soc_percent,
        )
        result = engine.run(
            num_days=days,
            initial_soc_percent=initial_soc,
            cloudy_day_indices=cloudy,
        )
        last_simulation = result
        return SimulateResponse(
            telemetry=[TelemetryPointSchema(**vars(p)) for p in result.telemetry],
            initial_soc_percent=result.initial_soc_percent,
            final_soc_percent=result.final_soc_percent,
            capacity_kwh=result.capacity_kwh,
            num_days=result.num_days,
            cloudy_days=result.cloudy_days,
        )

    @app.get("/status", response_model=StatusResponse)
    def status():
        """
        Return current stress score, risk level, and factors.
        Uses last simulation if available; otherwise runs a default 1-day simulation.
        """
        nonlocal last_simulation, last_stress
        if last_simulation is None:
            engine = SimulationEngine(
                capacity_kwh=settings.battery_capacity_kwh,
                min_soc_percent=settings.min_soc_percent,
                max_soc_percent=settings.max_soc_percent,
            )
            last_simulation = engine.run(num_days=1, initial_soc_percent=settings.initial_soc_percent)
        stress_engine.set_anomaly(anomaly_model.predict(last_simulation.telemetry))
        stress_result = stress_engine.evaluate(
            last_simulation.telemetry,
            last_simulation.initial_soc_percent,
            last_simulation.cloudy_days,
        )
        last_stress = stress_result
        return StatusResponse(
            stress_score=stress_result.stress_score,
            risk_level=stress_result.risk_level.value,
            stress_factors=[
                StressFactorSchema(
                    name=f.name,
                    description=f.description,
                    contribution=f.contribution,
                    mitigation_action=f.mitigation_action,
                )
                for f in stress_result.stress_factors
            ],
            anomaly_detected=stress_result.anomaly_detected,
        )

    @app.get("/plan", response_model=PlanResponse)
    def plan():
        """
        Return 24h energy plan (min SoC, appliance window, budget, mitigations).
        Uses last stress result; if none, calls /status logic first.
        """
        nonlocal last_stress, last_plan
        if last_stress is None:
            status()  # populate last_stress
        plan_result = planning_engine.generate(last_stress)
        last_plan = plan_result
        return PlanResponse(
            items=[
                EnergyPlanItemSchema(
                    start_hour=it.start_hour,
                    end_hour=it.end_hour,
                    label=it.label,
                    recommended_soc_min=it.recommended_soc_min,
                    recommended_action=it.recommended_action,
                )
                for it in plan_result.items
            ],
            min_soc_threshold_percent=plan_result.min_soc_threshold_percent,
            heavy_appliance_window_start=plan_result.heavy_appliance_window_start,
            heavy_appliance_window_end=plan_result.heavy_appliance_window_end,
            daily_energy_budget_kwh=plan_result.daily_energy_budget_kwh,
            mitigations=plan_result.mitigations,
        )

    @app.post("/chat", response_model=ChatResponse)
    def chat(body: ChatRequest):
        """
        Send user message and optional context to LLM for explanation.
        Falls back to offline message if Gemini unavailable or on failure.
        """
        context = body.context or {}
        if last_stress is not None:
            context["stress_score"] = last_stress.stress_score
            context["risk_level"] = last_stress.risk_level.value
            context["stress_factors"] = [
                {"name": f.name, "mitigation_action": f.mitigation_action}
                for f in last_stress.stress_factors
            ]
        if last_plan is not None:
            context["plan"] = {
                "min_soc_threshold_percent": last_plan.min_soc_threshold_percent,
                "heavy_appliance_window": [
                    last_plan.heavy_appliance_window_start,
                    last_plan.heavy_appliance_window_end,
                ],
                "daily_energy_budget_kwh": last_plan.daily_energy_budget_kwh,
                "mitigations": last_plan.mitigations,
            }
        reply = llm_service.explain(context, body.message)
        from_llm = llm_service.available
        fallback = None
        if not from_llm:
            fallback = "LLM unavailable; using offline message."
        return ChatResponse(reply=reply, from_llm=from_llm, fallback_message=fallback)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )

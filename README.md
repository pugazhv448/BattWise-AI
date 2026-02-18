# BattWise AI

**Production-grade, modular AI system for LiFePO4 battery longevity in solar households.**

Hackathon-ready MVP: fully software-based, simulated inverter telemetry, optional Gemini explanation layer, offline-capable core.

---

## System architecture (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BattWise AI                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  FRONTEND (Streamlit)                                                        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │ SoC chart    │ │ Stress gauge │ │ Risk level   │ │ Plan + Chat panel    │ │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────────┬───────────┘ │
│         │                │                │                     │             │
│         └────────────────┴────────────────┴─────────────────────┘             │
│                                    │ HTTP (GET/POST)                           │
├────────────────────────────────────┼─────────────────────────────────────────┤
│  BACKEND (FastAPI)                  ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  GET /simulate   GET /status   GET /plan   POST /chat                     │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│         │                │                │                │                  │
│         ▼                ▼                ▼                ▼                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Simulation  │  │ Stress      │  │ Planning    │  │ LLM Service         │  │
│  │ Engine      │──│ Engine     │──│ Engine      │  │ (Gemini, optional)  │  │
│  └─────────────┘  └──────┬──────┘  └─────────────┘  └─────────────────────┘  │
│                          │                                                     │
│                          ▼                                                     │
│                   ┌─────────────┐  ┌─────────────────────┐                    │
│                   │ ML Anomaly  │  │ Verification Engine  │                    │
│                   │ (Isolation  │  │ (pre/post nudge)     │                    │
│                   │  Forest)    │  └─────────────────────┘                    │
│                   └─────────────┘                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Workflow

1. **Simulate** – Simulation engine generates 24h solar curve + household load, updates SoC over one or more days; supports cloudy-day indices.
2. **Stress** – Stress engine computes a 0–100 Battery Stress Score from deep discharge, rapid discharge, idle high SoC, consecutive cloudy deficit; ML layer flags anomalous discharge.
3. **Plan** – Planning engine produces a 24h energy plan (min SoC, heavy-appliance window, budget) and maps each stress factor to mitigation actions.
4. **Verify** – Verification engine compares pre- vs post-nudge discharge and stress delta (for validating recommendations).
5. **Explain** – Optional LLM service (Gemini) turns structured output into natural language; degrades gracefully when offline or key missing.

---

## How to run

### 1. Create virtual environment

```bash
cd battwise-ai
python -m venv .venv
```

**Windows (PowerShell):**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Windows (cmd):**
```cmd
.venv\Scripts\activate.bat
```

**Linux/macOS:**
```bash
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create .env file (optional)

```bash
copy .env.example .env
# Edit .env and set GEMINI_API_KEY=your_key_here for chat explanations
```

### 4. Run backend

From project root `battwise-ai`:

```bash
# Windows
set PYTHONPATH=.
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Linux/macOS
PYTHONPATH=. uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs: http://127.0.0.1:8000/docs

### 5. Run frontend

In a second terminal (with venv activated):

```bash
cd battwise-ai
streamlit run frontend/app.py
```

If `streamlit` is not recognized, use the module form:

```powershell
cd battwise-ai
python -m streamlit run frontend/app.py
```

Frontend: http://localhost:8501  
Set `BACKEND_URL=http://127.0.0.1:8000` if the API runs on a different host/port.

### 6. Run tests

From project root `battwise-ai` (with venv activated):

```bash
# Windows (PowerShell)
$env:PYTHONPATH="."; python -m pytest tests/ -v

# Linux/macOS
PYTHONPATH=. python -m pytest tests/ -v
```

---

## API documentation

| Method | Endpoint   | Description |
|--------|------------|-------------|
| GET    | `/simulate` | Run multi-day simulation. Query: `days`, `initial_soc`, `cloudy_day_indices`, `capacity_kwh`. Returns telemetry + summary. |
| GET    | `/status`   | Current stress score (0–100), risk level (Safe/Warning/Critical), stress factors, anomaly flag. Uses last simulation. |
| GET    | `/plan`     | 24h energy plan: windows, min SoC, heavy-appliance window, daily budget, mitigations. Uses last stress result. |
| POST   | `/chat`     | Body: `{"message": "...", "context": {...}}`. Returns LLM explanation or offline fallback. |

All responses are JSON.

---

## Hackathon pitch summary

**BattWise AI** helps solar households with LiFePO4 batteries maximize longevity and avoid stress:

- **Simulated telemetry** – No hardware required; realistic solar + load curves and SoC evolution.
- **Stress score (0–100)** – Deep discharge, rapid discharge, idle high SoC, cloudy-day deficit, plus ML anomaly detection.
- **Actionable plan** – 24h plan with min SoC, heavy-appliance window, energy budget, and per-factor mitigations.
- **Verification** – Compare before/after stress when following recommendations.
- **Optional AI explainer** – Gemini turns numbers into plain-language advice; works offline without the key.

Clean architecture, modular backend, Streamlit UI, FastAPI JSON API—ready to extend with real inverters or more ML.

---

## Project structure

```
battwise-ai/
├── backend/
│   ├── main.py           # FastAPI app, routes
│   ├── config.py         # Settings from env
│   ├── models/
│   │   ├── battery_models.py
│   │   └── schemas.py
│   ├── core/
│   │   ├── stress_engine.py
│   │   ├── planning_engine.py
│   │   ├── simulation_engine.py
│   │   └── verification_engine.py
│   ├── ml/
│   │   └── anomaly_model.py
│   ├── services/
│   │   └── llm_service.py
│   └── utils/
│       └── smoothing.py
├── frontend/
│   └── app.py            # Streamlit UI
├── tests/
│   └── test_sanity.py
├── requirements.txt
├── .env.example
└── README.md
```

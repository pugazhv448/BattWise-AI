"""
BattWise AI Streamlit frontend.
Displays SoC time-series, stress gauge, risk level, energy plan, stress factors, chat.
Fetches from backend APIs.
"""
import os
from typing import Any, Dict, Optional

import requests
import streamlit as st

# Backend base URL; override with env BACKEND_URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")


def api_get(path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict]:
    """GET from backend; returns JSON or None on failure."""
    try:
        r = requests.get(f"{BACKEND_URL}{path}", params=params or {}, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.warning(f"Backend request failed: {e}. Is the API running at {BACKEND_URL}?")
        return None


def api_post(path: str, json_body: Dict[str, Any]) -> Optional[Dict]:
    """POST to backend; returns JSON or None on failure."""
    try:
        r = requests.post(f"{BACKEND_URL}{path}", json=json_body, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.warning(f"Backend request failed: {e}")
        return None


def main() -> None:
    st.set_page_config(page_title="BattWise AI", page_icon="🔋", layout="wide")
    st.title("🔋 BattWise AI")
    st.caption("Battery longevity for LiFePO4 solar households")

    # Sidebar: simulation controls
    with st.sidebar:
        st.header("Simulation")
        days = st.slider("Days", 1, 14, 1)
        initial_soc = st.slider("Initial SoC %", 0.0, 100.0, 80.0, 5.0)
        capacity_kwh = st.number_input("Capacity (kWh)", min_value=0.1, value=10.0, step=0.5)
        cloudy_input = st.text_input("Cloudy day indices (0-based, comma-separated)", "")
        if st.button("Run simulation"):
            params = {
                "days": days,
                "initial_soc": initial_soc,
                "capacity_kwh": capacity_kwh,
            }
            if cloudy_input.strip():
                params["cloudy_day_indices"] = cloudy_input.strip()
            data = api_get("/simulate", params)
            if data:
                st.session_state["simulate"] = data
                st.session_state["status"] = None
                st.session_state["plan"] = None
                st.success("Simulation done. Refresh status/plan below.")

    # Ensure we have data: trigger /simulate if needed
    if "simulate" not in st.session_state:
        data = api_get("/simulate", {"days": 1, "initial_soc": 80.0, "capacity_kwh": 10.0})
        if data:
            st.session_state["simulate"] = data
        else:
            st.info("Start the backend (uvicorn) then refresh. Using placeholder data for layout.")
            st.session_state["simulate"] = _placeholder_simulate()

    sim = st.session_state["simulate"]
    telemetry = sim.get("telemetry", [])

    # SoC time-series graph
    st.subheader("SoC time-series")
    if telemetry:
        try:
            import pandas as pd
            df = pd.DataFrame(telemetry)
            df["time"] = df["day_index"] * 24 + df["hour"]
            import plotly.express as px
            fig = px.line(df, x="time", y="soc_percent", title="State of Charge (%)")
            fig.update_layout(xaxis_title="Hours", yaxis_title="SoC %", height=300)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.line_chart(
                {p["day_index"] * 24 + p["hour"]: p["soc_percent"] for p in telemetry}
                if telemetry else {}
            )
    else:
        st.write("No telemetry yet. Run a simulation from the sidebar.")

    # Fetch status (stress) if not cached
    if "status" not in st.session_state or st.session_state.get("status") is None:
        st.session_state["status"] = api_get("/status")
    if "plan" not in st.session_state or st.session_state.get("plan") is None:
        st.session_state["plan"] = api_get("/plan")

    status_data = st.session_state.get("status")
    plan_data = st.session_state.get("plan")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Stress score")
        if status_data:
            score = status_data.get("stress_score", 0)
            risk = status_data.get("risk_level", "Safe")
            st.metric("Score (0–100)", f"{score:.1f}")
            color = "🟢" if risk == "Safe" else "🟡" if risk == "Warning" else "🔴"
            st.write(f"{color} **{risk}**")
            # Gauge-like progress bar
            st.progress(min(1.0, score / 100.0))
        else:
            st.write("Run simulation and ensure backend is up for stress data.")

    with col2:
        st.subheader("Risk level")
        if status_data:
            st.write(status_data.get("risk_level", "—"))
            if status_data.get("anomaly_detected"):
                st.warning("Anomalous discharge pattern detected.")
        else:
            st.write("—")

    with col3:
        st.subheader("Today's energy plan")
        if plan_data:
            st.write(f"Min SoC: **{plan_data.get('min_soc_threshold_percent', '—')}%**")
            st.write(
                f"Heavy appliances: **{plan_data.get('heavy_appliance_window_start', 0):.0f}:00 – "
                f"{plan_data.get('heavy_appliance_window_end', 0):.0f}:00**"
            )
            st.write(f"Daily budget: **{plan_data.get('daily_energy_budget_kwh', 0):.1f} kWh**")
        else:
            st.write("—")

    st.subheader("Stress factors")
    if status_data and status_data.get("stress_factors"):
        for f in status_data["stress_factors"]:
            with st.expander(f"{f.get('name', '')} (impact: {f.get('contribution', 0):.0%})"):
                st.write(f.get("description", ""))
                st.caption(f"**Mitigation:** {f.get('mitigation_action', '')}")
    else:
        st.write("No stress factors. Run simulation and /status.")

    st.subheader("Plan breakdown")
    if plan_data and plan_data.get("items"):
        for it in plan_data["items"]:
            st.write(
                f"**{it.get('start_hour', 0):.0f}:00 – {it.get('end_hour', 0):.0f}:00** "
                f"{it.get('label', '')}: {it.get('recommended_action', '')}"
            )
        if plan_data.get("mitigations"):
            st.write("**Mitigations:**")
            for m in plan_data["mitigations"]:
                st.write(f"- {m}")
    else:
        st.write("No plan data.")

    st.subheader("Chat assistant")
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
        if msg.get("caption"):
            st.caption(msg["caption"])
    user_msg = st.chat_input("Ask about your battery or plan...")
    if user_msg:
        st.session_state["chat_history"].append({"role": "user", "content": user_msg})
        reply_data = api_post("/chat", {"message": user_msg, "context": None})
        reply = reply_data.get("reply", "No reply.") if reply_data else "Backend unavailable."
        caption = reply_data.get("fallback_message") if reply_data else None
        st.session_state["chat_history"].append({"role": "assistant", "content": reply, "caption": caption})
        st.rerun()


def _placeholder_simulate() -> Dict[str, Any]:
    """Minimal placeholder when backend is down."""
    return {
        "telemetry": [{"hour": h, "day_index": 0, "solar_kw": 0, "load_kw": 0.5, "soc_percent": 80 - h * 0.5, "net_power_kw": -0.5, "is_cloudy": False} for h in range(24)],
        "initial_soc_percent": 80.0,
        "final_soc_percent": 68.0,
        "capacity_kwh": 10.0,
        "num_days": 1,
        "cloudy_days": [],
    }


if __name__ == "__main__":
    main()

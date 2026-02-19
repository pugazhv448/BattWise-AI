"""
BattWise AI – Dark Glassmorphism Dashboard
Apple Vision Pro / macOS Control Center aesthetic.
Deep navy base · Frosted glass cards · Neon green accents · Soft glow borders
"""
import os
from typing import Any, Dict, Optional

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

# ─── Design System: Dark Glassmorphism ─────────────────────────────────────
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Reset & base ───────────────────────────────────────────────────── */
*, *::before, *::after {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  box-sizing: border-box;
}

/* ── CSS Variables ──────────────────────────────────────────────────── */
:root {
  --bg-1:          #050d1a;
  --bg-2:          #0a1628;
  --bg-3:          #0d1f36;

  --glass-bg:      rgba(255, 255, 255, 0.05);
  --glass-bg-hover:rgba(255, 255, 255, 0.09);
  --glass-border:  rgba(255, 255, 255, 0.10);
  --glass-border-h:rgba(255, 255, 255, 0.20);
  --glass-shadow:  0 8px 32px rgba(0, 0, 0, 0.45),
                   inset 0 1px 0 rgba(255,255,255,0.07);
  --blur:          blur(18px) saturate(160%);

  --accent:        #39ff9f;
  --accent-dim:    rgba(57, 255, 159, 0.18);
  --accent-glow:   0 0 24px rgba(57, 255, 159, 0.35);

  --text:          #e2f0ff;
  --text-dim:      rgba(226, 240, 255, 0.55);
  --text-faint:    rgba(226, 240, 255, 0.32);

  --safe:          #39ff9f;
  --safe-glow:     0 0 18px rgba(57,255,159,0.4);
  --warning:       #f59e0b;
  --warning-glow:  0 0 18px rgba(245,158,11,0.4);
  --critical:      #ff4d6d;
  --critical-glow: 0 0 18px rgba(255,77,109,0.5);

  --radius:        14px;
  --radius-sm:     10px;
  --transition:    all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ── Full-page dark gradient ────────────────────────────────────────── */
.stApp {
  background: linear-gradient(135deg, #050d1a 0%, #0a1832 40%, #071424 100%) !important;
  min-height: 100vh;
}

/* Kill every white/light remnant Streamlit injects */
.main, .block-container,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"],
[data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"] {
  background: transparent !important;
}

.main .block-container {
  padding-top: 1.75rem !important;
  padding-bottom: 3rem !important;
  max-width: 90% !important; /* Made responsive */
}

/* ── Glass mixin (applied to every card component) ──────────────────── */
.glass {
  background: var(--glass-bg);
  backdrop-filter: var(--blur);
  -webkit-backdrop-filter: var(--blur);
  border: 1px solid var(--glass-border);
  box-shadow: var(--glass-shadow);
  border-radius: var(--radius);
  transition: var(--transition);
}
.glass:hover {
  background: var(--glass-bg-hover);
  border-color: var(--glass-border-h);
  transform: translateY(-2px);
  box-shadow: 0 12px 40px rgba(0,0,0,0.55),
              inset 0 1px 0 rgba(255,255,255,0.10);
}

/* ── Dashboard hero header ──────────────────────────────────────────── */
.dash-header {
  background: linear-gradient(135deg,
    rgba(57,255,159,0.08) 0%,
    rgba(255,255,255,0.04) 60%,
    rgba(57,255,159,0.04) 100%);
  backdrop-filter: var(--blur);
  -webkit-backdrop-filter: var(--blur);
  border: 1px solid rgba(57,255,159,0.18);
  border-radius: 18px;
  padding: 1.5rem 2rem;
  margin-bottom: 1.75rem;
  box-shadow: 0 0 40px rgba(57,255,159,0.08),
              0 8px 32px rgba(0,0,0,0.5);
  position: relative;
  overflow: hidden;
}
.dash-header::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -20%;
  width: 60%;
  height: 200%;
  background: radial-gradient(ellipse, rgba(57,255,159,0.06) 0%, transparent 70%);
  pointer-events: none;
}
.dash-header h1 {
  font-weight: 800 !important;
  font-size: 1.9rem !important;
  background: linear-gradient(135deg, #39ff9f 0%, #a8ffdc 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.03em;
  margin: 0 0 0.2rem 0 !important;
  line-height: 1.2 !important;
}
.dash-header .subtitle {
  color: var(--text-dim);
  font-size: 0.9rem;
  font-weight: 400;
  margin: 0;
  letter-spacing: 0.01em;
}

/* ── Section titles ─────────────────────────────────────────────────── */
.section-title {
  font-weight: 600 !important;
  font-size: 0.78rem !important;
  color: var(--accent) !important;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  margin: 2rem 0 0.9rem 0 !important;
  padding-left: 0.75rem;
  border-left: 2px solid var(--accent);
  text-shadow: var(--accent-glow);
  display: block;
}

/* ── Metric glass cards ─────────────────────────────────────────────── */
.metric-card {
  background: var(--glass-bg);
  backdrop-filter: var(--blur);
  -webkit-backdrop-filter: var(--blur);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius);
  padding: 1.25rem 1.4rem;
  margin-bottom: 0.875rem;
  box-shadow: var(--glass-shadow);
  transition: var(--transition);
  position: relative;
  overflow: hidden;
}
.metric-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(57,255,159,0.4), transparent);
}
.metric-card:hover {
  background: var(--glass-bg-hover);
  border-color: rgba(57,255,159,0.25);
  transform: translateY(-3px);
  box-shadow: 0 16px 48px rgba(0,0,0,0.5),
              0 0 0 1px rgba(57,255,159,0.08),
              inset 0 1px 0 rgba(255,255,255,0.1);
}
.metric-card .mc-label {
  font-size: 0.72rem;
  font-weight: 500;
  color: var(--text-faint);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 0.45rem;
}
.metric-card .mc-value {
  font-size: 1.9rem;
  font-weight: 700;
  color: var(--text);
  line-height: 1;
  letter-spacing: -0.02em;
}
.metric-card .mc-value.accent  { color: var(--accent);   text-shadow: var(--accent-glow); }
.metric-card .mc-value.safe    { color: var(--safe);     text-shadow: var(--safe-glow); }
.metric-card .mc-value.warn    { color: var(--warning);  text-shadow: var(--warning-glow); }
.metric-card .mc-value.danger  { color: var(--critical); text-shadow: var(--critical-glow); }

/* ── Mobile Tweaks ──────────────────────────────────────────────────── */
@media (max-width: 768px) {
  .main .block-container {
    max-width: 100% !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
  }
  .metric-card .mc-value { font-size: 1.6rem; }
  .dash-header { padding: 1rem 1.25rem; }
  .dash-header h1 { font-size: 1.5rem !important; }
}

/* ── Progress bar ───────────────────────────────────────────────────── */
@keyframes fillBar { from { width: 0%; } }
.progress-wrap {
  background: rgba(255,255,255,0.08);
  border-radius: 8px;
  height: 6px;
  overflow: hidden;
  margin-top: 0.65rem;
}
.progress-fill {
  height: 100%;
  border-radius: 8px;
  animation: fillBar 0.9s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

/* ── Risk badges ────────────────────────────────────────────────────── */
@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 8px rgba(255,77,109,0.4); }
  50%       { box-shadow: 0 0 22px rgba(255,77,109,0.8); }
}
.risk-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.3rem 0.9rem;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  transition: var(--transition);
}
.risk-badge::before { content: '●'; font-size: 0.55rem; }
.risk-badge.safe {
  background: rgba(57,255,159,0.12);
  border: 1px solid rgba(57,255,159,0.30);
  color: var(--safe);
  box-shadow: 0 0 12px rgba(57,255,159,0.2);
}
.risk-badge.warn {
  background: rgba(245,158,11,0.12);
  border: 1px solid rgba(245,158,11,0.30);
  color: var(--warning);
  box-shadow: 0 0 12px rgba(245,158,11,0.2);
}
.risk-badge.danger {
  background: rgba(255,77,109,0.12);
  border: 1px solid rgba(255,77,109,0.30);
  color: var(--critical);
  animation: pulse-glow 1.4s ease-in-out infinite;
}

/* ── Stress factor rows ─────────────────────────────────────────────── */
.factor-row {
  background: var(--glass-bg);
  backdrop-filter: var(--blur);
  -webkit-backdrop-filter: var(--blur);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-sm);
  padding: 1rem 1.2rem;
  margin-bottom: 0.6rem;
  transition: var(--transition);
  position: relative;
  overflow: hidden;
}
.factor-row::after {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  background: linear-gradient(180deg, var(--warning), var(--accent));
  border-radius: 0 2px 2px 0;
}
.factor-row:hover {
  background: var(--glass-bg-hover);
  border-color: var(--glass-border-h);
  transform: translateX(2px);
}
.factor-name {
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--text);
  margin-bottom: 0.2rem;
}
.factor-impact {
  font-size: 0.78rem;
  font-weight: 500;
  color: var(--warning);
  float: right;
  background: rgba(245,158,11,0.12);
  padding: 0.1rem 0.5rem;
  border-radius: 20px;
  border: 1px solid rgba(245,158,11,0.2);
}
.factor-desc {
  font-size: 0.82rem;
  color: var(--text-dim);
  margin: 0.15rem 0;
  line-height: 1.5;
}
.factor-action {
  font-size: 0.78rem;
  color: var(--accent);
  margin-top: 0.35rem;
  opacity: 0.85;
}
.factor-action::before { content: '→ '; }

/* ── Plan timeline blocks ───────────────────────────────────────────── */
.plan-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 0.75rem;
  margin-top: 0.75rem;
}
.plan-block {
  background: var(--glass-bg);
  backdrop-filter: var(--blur);
  -webkit-backdrop-filter: var(--blur);
  border: 1px solid var(--glass-border);
  border-top: 2px solid var(--accent);
  border-radius: var(--radius-sm);
  padding: 0.85rem 1rem;
  box-shadow: var(--glass-shadow);
  transition: var(--transition);
  position: relative;
}
.plan-block:hover {
  background: var(--glass-bg-hover);
  border-color: rgba(57,255,159,0.25);
  border-top-color: var(--accent);
  transform: translateY(-3px);
  box-shadow: 0 0 20px rgba(57,255,159,0.12), var(--glass-shadow);
}
.plan-block .pb-time {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 0.35rem;
  opacity: 0.85;
}
.plan-block .pb-label {
  font-weight: 600;
  color: var(--text);
  font-size: 0.88rem;
  margin-bottom: 0.25rem;
  line-height: 1.3;
}
.plan-block .pb-action {
  font-size: 0.77rem;
  color: var(--text-dim);
  line-height: 1.4;
}

/* ── Sidebar ────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg,
    rgba(5,13,26,0.95) 0%,
    rgba(10,22,40,0.92) 100%) !important;
  backdrop-filter: var(--blur) !important;
  -webkit-backdrop-filter: var(--blur) !important;
  border-right: 1px solid var(--glass-border) !important;
  box-shadow: 4px 0 24px rgba(0,0,0,0.4) !important;
}
[data-testid="stSidebar"] > div:first-child {
  background: transparent !important;
}
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span {
  color: var(--text) !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
  color: var(--accent) !important;
  text-shadow: var(--accent-glow);
}
[data-testid="stSidebar"] hr {
  border-color: var(--glass-border) !important;
}

/* Sidebar widgets */
[data-testid="stSidebar"] .stSlider > div > div > div {
  background: var(--accent) !important;
}
[data-testid="stSidebar"] input {
  background: rgba(255,255,255,0.07) !important;
  border-color: var(--glass-border) !important;
  color: var(--text) !important;
  border-radius: 8px !important;
}

/* Primary button → neon glow */
[data-testid="stSidebar"] button[kind="primary"],
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #39ff9f 0%, #00cc77 100%) !important;
  color: #050d1a !important;
  border: none !important;
  font-weight: 700 !important;
  border-radius: 10px !important;
  box-shadow: 0 0 20px rgba(57,255,159,0.4) !important;
  transition: var(--transition) !important;
}
[data-testid="stSidebar"] button[kind="primary"]:hover,
.stButton > button[kind="primary"]:hover {
  box-shadow: 0 0 32px rgba(57,255,159,0.6) !important;
  transform: translateY(-1px);
}

/* ── Expander ───────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
  background: var(--glass-bg) !important;
  border: 1px solid var(--glass-border) !important;
  border-radius: var(--radius-sm) !important;
  backdrop-filter: var(--blur) !important;
  -webkit-backdrop-filter: var(--blur) !important;
  margin-bottom: 0.5rem;
}
[data-testid="stExpander"] summary {
  padding: 0.75rem 1rem !important;
  color: var(--text) !important;
}
[data-testid="stExpander"] .stExpanderExpandIcon { display: none !important; }
[data-testid="stExpander"] summary::before {
  content: '▶';
  margin-right: 0.5rem;
  font-size: 0.6rem;
  color: var(--accent);
  transition: transform 0.2s ease;
  display: inline-block;
}
[data-testid="stExpander"] details[open] summary::before {
  transform: rotate(90deg);
}

/* ── Chat messages ──────────────────────────────────────────────────── */
[data-testid="stChatMessage"] {
  background: var(--glass-bg) !important;
  backdrop-filter: var(--blur) !important;
  -webkit-backdrop-filter: var(--blur) !important;
  border: 1px solid var(--glass-border) !important;
  border-radius: var(--radius-sm) !important;
  margin-bottom: 0.5rem;
}
[data-testid="stChatInput"] {
  background: rgba(255,255,255,0.07) !important;
  border: 1px solid var(--glass-border) !important;
  border-radius: 14px !important;
  backdrop-filter: blur(12px) !important;
}
[data-testid="stChatInput"]:focus-within {
  border-color: rgba(57,255,159,0.4) !important;
  box-shadow: 0 0 0 2px rgba(57,255,159,0.12) !important;
}
[data-testid="stChatInput"] textarea {
  color: var(--text) !important;
  background: transparent !important;
}

/* ── Generic inputs / selects ───────────────────────────────────────── */
.stTextInput input, .stNumberInput input, .stSelectbox select {
  background: rgba(255,255,255,0.07) !important;
  border: 1px solid var(--glass-border) !important;
  color: var(--text) !important;
  border-radius: 8px !important;
}
.stTextInput input:focus, .stNumberInput input:focus {
  border-color: rgba(57,255,159,0.4) !important;
  box-shadow: 0 0 0 2px rgba(57,255,159,0.12) !important;
}

/* ── Alert / info boxes ─────────────────────────────────────────────── */
.stAlert {
  background: var(--glass-bg) !important;
  border: 1px solid var(--glass-border) !important;
  backdrop-filter: blur(10px) !important;
  border-radius: var(--radius-sm) !important;
}

/* ── Divider override ───────────────────────────────────────────────── */
hr {
  border: none !important;
  height: 1px !important;
  background: linear-gradient(90deg, transparent, var(--glass-border), transparent) !important;
  margin: 0.75rem 0 !important;
}

/* ── Scrollbar ──────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: rgba(57,255,159,0.25);
  border-radius: 8px;
}
::-webkit-scrollbar-thumb:hover {
  background: rgba(57,255,159,0.45);
}
</style>
"""


# ─── API helpers ───────────────────────────────────────────────────────────
def api_get(path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict]:
    try:
        r = requests.get(f"{BACKEND_URL}{path}", params=params or {}, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.warning(f"Backend unavailable: {e}")
        return None


def api_post(path: str, json_body: Dict[str, Any], timeout: int = 15) -> Optional[Dict]:
    try:
        r = requests.post(f"{BACKEND_URL}{path}", json=json_body, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.warning(f"Backend unavailable: {e}")
        return None


def api_chat(message: str, context: Any = None) -> Optional[Dict]:
    """POST to /chat with a long timeout (Ollama cold-start can take ~25s)."""
    with st.spinner("🤖 Thinking…"):
        return api_post("/chat", {"message": message, "context": context}, timeout=60)


def api_chat_stream(message: str, context: Any = None):
    """Generator for streaming chat responses."""
    try:
        r = requests.post(
            f"{BACKEND_URL}/chat/stream",
            json={"message": message, "context": context},
            stream=True,
            timeout=40
        )
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
            if chunk:
                yield chunk
    except Exception as e:
        yield f"⚠️ Stream error: {e}"


# ─── Plotly dark theme helper ───────────────────────────────────────────────
def dark_layout(height: int = 320, **kwargs) -> dict:
    return dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.025)",
        height=height,
        margin=dict(l=48, r=24, t=20, b=48),
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.06)",
            zerolinecolor="rgba(255,255,255,0.08)",
            tickfont=dict(color="rgba(226,240,255,0.5)", size=10, family="Inter"),
        ),
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.06)",
            zerolinecolor="rgba(255,255,255,0.08)",
            tickfont=dict(color="rgba(226,240,255,0.5)", size=10, family="Inter"),
        ),
        font=dict(family="Inter, sans-serif", color="#e2f0ff", size=11),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="rgba(5,13,26,0.9)",
            bordercolor="rgba(57,255,159,0.3)",
            font=dict(family="Inter", color="#e2f0ff", size=11),
        ),
        **kwargs,
    )


# ─── Main ──────────────────────────────────────────────────────────────────
def main() -> None:
    st.set_page_config(
        page_title="BattWise AI",
        page_icon="🔋",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # ── Hero header ──────────────────────────────────────────────────────
    st.markdown(
        '<div class="dash-header">'
        "<h1>🔋 BattWise AI</h1>"
        '<p class="subtitle">Battery longevity intelligence for LiFePO₄ solar households</p>'
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Sidebar ───────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### ⚡ Simulation")
        days = st.slider("Days", 1, 14, 1)
        initial_soc = st.slider("Initial SoC %", 0.0, 100.0, 80.0, 5.0)
        capacity_kwh = st.number_input("Capacity (kWh)", min_value=0.1, value=10.0, step=0.5)
        cloudy_input = st.text_input("Cloudy day indices (0-based, comma-separated)", "")
        if st.button("▶  Run Simulation", type="primary"):
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
                # Immediately re-fetch status + plan so metric cards
                # reflect the NEW simulation (not cached stale values)
                st.session_state["status"] = api_get("/status")
                st.session_state["plan"]   = api_get("/plan")
                st.success("✅ Simulation complete.")

    # ── Seed data ─────────────────────────────────────────────────────────
    if "simulate" not in st.session_state:
        data = api_get("/simulate", {"days": 1, "initial_soc": 80.0, "capacity_kwh": 10.0})
        if data:
            st.session_state["simulate"] = data
        else:
            st.info("⚡ Start the backend then refresh. Using placeholder data.")
            st.session_state["simulate"] = _placeholder_simulate()

    sim = st.session_state["simulate"]
    telemetry = sim.get("telemetry", [])

    if "status" not in st.session_state or st.session_state.get("status") is None:
        st.session_state["status"] = api_get("/status")
    if "plan" not in st.session_state or st.session_state.get("plan") is None:
        st.session_state["plan"] = api_get("/plan")

    status_data = st.session_state.get("status")
    plan_data = st.session_state.get("plan")

    # ── SoC time-series chart ─────────────────────────────────────────────
    st.markdown('<span class="section-title">📈 State of Charge · Time Series</span>', unsafe_allow_html=True)
    if telemetry:
        try:
            import pandas as pd
            import plotly.graph_objects as go

            df = __import__("pandas").DataFrame(telemetry)
            df["time"] = df["day_index"] * 24 + df["hour"]

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["time"],
                y=df["soc_percent"],
                mode="lines",
                name="SoC %",
                line=dict(color="#39ff9f", width=2.5, shape="spline", smoothing=0.8),
                fill="tozeroy",
                fillcolor="rgba(57,255,159,0.06)",
                hovertemplate="Hour %{x} · <b>%{y:.1f}%</b><extra></extra>",
            ))
            # Safe threshold band
            fig.add_hrect(y0=0, y1=20,
                          fillcolor="rgba(255,77,109,0.06)",
                          line_width=0,
                          annotation_text="Deep discharge zone",
                          annotation_font=dict(color="rgba(255,77,109,0.5)", size=10))
            fig.update_layout(**dark_layout(height=300, yaxis_range=[0, 105]))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True, "displaylogo": False})
        except Exception:
            st.line_chart({p["day_index"] * 24 + p["hour"]: p["soc_percent"] for p in telemetry} if telemetry else {})
    else:
        st.write("No telemetry yet. Run a simulation from the sidebar.")

    # ── Metric row ────────────────────────────────────────────────────────
    score = status_data.get("stress_score", 0) if status_data else 0
    risk  = (status_data.get("risk_level") or "Safe") if status_data else "Safe"
    score_pct = min(100, max(0, score))

    risk_class = "safe" if risk == "Safe" else ("warn" if risk == "Warning" else "danger")
    gauge_color = "#39ff9f" if risk == "Safe" else ("#f59e0b" if risk == "Warning" else "#ff4d6d")

    col1, col2, col3 = st.columns(3)

    with col1:
        try:
            import plotly.graph_objects as go
            steps = [
                {"range": [0, 35],  "color": "rgba(57,255,159,0.10)"},
                {"range": [35, 65], "color": "rgba(245,158,11,0.10)"},
                {"range": [65, 100],"color": "rgba(255,77,109,0.10)"},
            ]
            fig_g = go.Figure(go.Indicator(
                mode="gauge+number",
                value=score,
                number={"suffix": " ", "font": {"size": 30, "color": "#e2f0ff", "family": "Inter"}},
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 1,
                             "tickcolor": "rgba(226,240,255,0.3)",
                             "tickfont": {"color": "rgba(226,240,255,0.4)", "size": 9}},
                    "bar": {"color": gauge_color, "thickness": 0.72},
                    "bgcolor": "rgba(255,255,255,0.04)",
                    "borderwidth": 1,
                    "bordercolor": "rgba(255,255,255,0.12)",
                    "steps": steps,
                    "threshold": {"line": {"color": gauge_color, "width": 2},
                                  "thickness": 0.78, "value": score},
                },
                title={"text": "Stress Score", "font": {"size": 13, "color": "rgba(226,240,255,0.5)", "family": "Inter"}},
            ))
            fig_g.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter"),
                margin=dict(l=20, r=20, t=55, b=10),
                height=230,
            )
            st.plotly_chart(fig_g, use_container_width=True, config={"displayModeBar": False})
        except Exception:
            bar_color = gauge_color
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="mc-label">Stress Score</div>'
                f'<div class="mc-value {risk_class}">{score:.1f}</div>'
                f'<div class="progress-wrap"><div class="progress-fill" style="width:{score_pct}%;background:{bar_color};"></div></div>'
                f"</div>",
                unsafe_allow_html=True,
            )
        st.markdown(f'<span class="risk-badge {risk_class}">{risk}</span>', unsafe_allow_html=True)
        if status_data and status_data.get("anomaly_detected"):
            st.warning("⚠️ Anomalous discharge pattern detected.")

    with col2:
        min_soc   = plan_data.get("min_soc_threshold_percent", 20) if plan_data else 20
        heavy_s   = plan_data.get("heavy_appliance_window_start", 10) if plan_data else 10
        heavy_e   = plan_data.get("heavy_appliance_window_end", 15) if plan_data else 15
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="mc-label">Min SoC Reserve</div>'
            f'<div class="mc-value accent">{min_soc:.0f}<span style="font-size:1rem;opacity:.7">%</span></div>'
            f"</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="mc-label">Heavy Appliance Window</div>'
            f'<div class="mc-value" style="font-size:1.35rem;">{heavy_s:.0f}:00 – {heavy_e:.0f}:00</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

    with col3:
        budget    = plan_data.get("daily_energy_budget_kwh", 0) if plan_data else 0
        init_soc  = sim.get("initial_soc_percent", 0)
        final_soc = sim.get("final_soc_percent", 0)
        drift_cls = "safe" if final_soc >= 40 else ("warn" if final_soc >= 20 else "danger")
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="mc-label">Daily Energy Budget</div>'
            f'<div class="mc-value accent">{budget:.1f}<span style="font-size:1rem;opacity:.7"> kWh</span></div>'
            f"</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="mc-label">Simulation Result</div>'
            f'<div class="mc-value {drift_cls}" style="font-size:1.35rem;">{init_soc:.0f}% → {final_soc:.0f}%</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── Stress factors ────────────────────────────────────────────────────
    st.markdown('<span class="section-title">⚠️  Stress Factors & Mitigations</span>', unsafe_allow_html=True)
    default_factors = [
        {"name": "Deep discharge",    "description": "SoC below 20% increases electrode wear.",               "contribution": 0, "mitigation_action": "Raise minimum SoC reserve; avoid below 20%."},
        {"name": "Rapid discharge",   "description": "High C-rate accelerates active material degradation.",  "contribution": 0, "mitigation_action": "Spread heavy loads; use suggested appliance window."},
        {"name": "Idle high SoC",     "description": "SoC held above 90% when not cycling stresses cells.",   "contribution": 0, "mitigation_action": "Allow discharge to 80–85% post charge when possible."},
        {"name": "Cloudy-day deficit","description": "Repeated low-SoC days accumulate wear.",                "contribution": 0, "mitigation_action": "Increase reserve on clear days; cut non-essential loads on cloudy days."},
        {"name": "Anomalous pattern", "description": "Unusual discharge detected by ML classifier.",          "contribution": 0, "mitigation_action": "Review load schedule; check for unexpected consumers."},
    ]
    factors = (status_data.get("stress_factors") if status_data else None) or default_factors
    for f in factors:
        contrib = f.get("contribution", 0)
        impact_pct = f"{contrib:.0%}" if isinstance(contrib, float) and contrib < 1 else f"{contrib:.0f}"
        st.markdown(
            f'<div class="factor-row">'
            f'<span class="factor-impact">Impact {impact_pct}</span>'
            f'<div class="factor-name">{f.get("name","")}</div>'
            f'<div class="factor-desc">{f.get("description","")}</div>'
            f'<div class="factor-action">{f.get("mitigation_action","")}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── Energy plan timeline ──────────────────────────────────────────────
    st.markdown('<span class="section-title">🕐  Today\'s Energy Plan</span>', unsafe_allow_html=True)
    default_items = [
        {"start_hour": 0,  "end_hour": 6,  "label": "Night Reserve",          "recommended_action": "Maintain charge above reserve threshold."},
        {"start_hour": 6,  "end_hour": 10, "label": "Morning Charge",          "recommended_action": "Solar charging phase — minimal discharge."},
        {"start_hour": 10, "end_hour": 15, "label": "Heavy Appliance Window",  "recommended_action": "Run washer, dryer, EV charger now."},
        {"start_hour": 15, "end_hour": 18, "label": "Afternoon Top-up",        "recommended_action": "Secondary solar window — top up if needed."},
        {"start_hour": 18, "end_hour": 24, "label": "Evening Use",             "recommended_action": "Minimise discharge rate; defer heavy loads."},
    ]
    items = (plan_data.get("items") if plan_data else None) or default_items
    blocks_html = '<div class="plan-grid">'
    for it in items:
        s = it.get("start_hour", 0)
        e = it.get("end_hour", 0)
        blocks_html += (
            f'<div class="plan-block">'
            f'<div class="pb-time">{s:.0f}:00 – {e:.0f}:00</div>'
            f'<div class="pb-label">{it.get("label","")}</div>'
            f'<div class="pb-action">{it.get("recommended_action","")}</div>'
            f"</div>"
        )
    blocks_html += "</div>"
    st.markdown(blocks_html, unsafe_allow_html=True)

    if plan_data and plan_data.get("mitigations"):
        st.markdown('<span class="section-title">🛡️  Active Mitigations</span>', unsafe_allow_html=True)
        for m in plan_data["mitigations"]:
            st.markdown(f"- {m}")

    # ── Chat assistant ────────────────────────────────────────────────────
    st.markdown('<span class="section-title">💬  AI Chat Assistant</span>', unsafe_allow_html=True)
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    
    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
        if msg.get("caption"):
            st.caption(msg["caption"])

    user_msg = st.chat_input("Ask about your battery health, usage plan, or status…")
    if user_msg:
        st.session_state["chat_history"].append({"role": "user", "content": user_msg})
        with st.chat_message("user"):
            st.write(user_msg)
            
        with st.chat_message("assistant"):
            # Use streaming
            full_reply = st.write_stream(api_chat_stream(user_msg))
            st.session_state["chat_history"].append({"role": "assistant", "content": full_reply})
        st.rerun()


# ─── Placeholder data ──────────────────────────────────────────────────────
def _placeholder_simulate() -> Dict[str, Any]:
    return {
        "telemetry": [
            {
                "hour": h,
                "day_index": 0,
                "solar_kw": max(0, 2.5 * ((h - 6) / 6) * (1 - abs((h - 12) / 8))) if 6 <= h <= 18 else 0,
                "load_kw": 0.45,
                "soc_percent": max(20, 80 - h * 0.6 + (max(0, 2.5 * ((h-6)/6) * (1-abs((h-12)/8))) * 0.5)),
                "net_power_kw": -0.5,
                "is_cloudy": False,
            }
            for h in range(24)
        ],
        "initial_soc_percent": 80.0,
        "final_soc_percent":   62.0,
        "capacity_kwh":        10.0,
        "num_days":            1,
        "cloudy_days":         [],
    }


if __name__ == "__main__":
    main()

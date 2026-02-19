"""
LLM service: multi-provider chat backend for BattWise AI.

Provider priority (set via LLM_PROVIDER in .env):
  "ollama"  → local Ollama server (default, free, no API key)
  "gemini"  → Google Gemini cloud API (requires GEMINI_API_KEY)

Retry policy (both providers):
  - Up to 3 attempts with exponential back-off (1s → 2s → 4s)
  - Retries on HTTP 429, 500, 503
  - Friendly human-readable fallback on every failure path
  - Core logic is NEVER blocked or raised upon
"""
import json
import logging
import time
from typing import Any, Dict, Optional

import requests as _requests

from backend.config import get_settings

logger = logging.getLogger(__name__)

# ── Retry constants ────────────────────────────────────────────────────────
MAX_RETRIES        = 3
BASE_DELAY_S       = 1.0
BACKOFF_FACTOR     = 2.0
COOLDOWN_AFTER_429 = 30.0  # seconds to pause after Gemini quota burst
_RETRYABLE_STATUS  = {429, 500, 503}


class LLMService:
    """
    Multi-provider LLM service.
    Routes to Ollama (local) or Gemini (cloud) based on LLM_PROVIDER env var.
    Always returns a string — never raises to callers.
    """

    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self._provider   = settings.llm_provider          # "ollama" or "gemini"
        # Ollama
        self._ollama_url = settings.ollama_base_url.rstrip("/")
        self._ollama_model = settings.ollama_model
        self._ollama_timeout = settings.ollama_timeout_seconds
        # Gemini
        self._gemini_key   = api_key or settings.gemini_api_key
        self._gemini_model = settings.gemini_model
        self._gemini_timeout = settings.gemini_timeout_seconds
        # State
        self._quota_cooldown_until: float = 0.0
        self._available = True  # always optimistic; errors degrade gracefully

    @property
    def available(self) -> bool:
        return self._available

    # ── Public API ───────────────────────────────────────────────────────────

    def explain(
        self,
        context: Dict[str, Any],
        user_message: Optional[str] = None,
    ) -> str:
        """Send context + user message to LLM; always returns a safe string."""
        prompt = self._build_prompt(context, user_message)

        if self._provider == "ollama":
            return self._explain_ollama(prompt)
        elif self._provider == "gemini":
            return self._explain_gemini(prompt)
        else:
            return f"Unknown LLM_PROVIDER '{self._provider}'. Set to 'ollama' or 'gemini' in .env."

    # ── Ollama path ──────────────────────────────────────────────────────────

    def _explain_ollama(self, prompt: str) -> str:
        """Call local Ollama API with retry. Fast, free, no quota."""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = _requests.post(
                    f"{self._ollama_url}/api/generate",
                    json={
                        "model":      self._ollama_model,
                        "prompt":     prompt,
                        "stream":     False,
                        "keep_alive": 600,   # keep model hot in RAM for 10 min
                        "options": {
                            "temperature": 0.3,
                            "num_predict": 150,   # shorter replies = faster
                            "num_ctx":     512,   # smaller context window = faster
                            "stop":        ["\n\n\n"],
                        },
                    },
                    timeout=self._ollama_timeout,
                )
                resp.raise_for_status()
                data  = resp.json()
                reply = data.get("response", "").strip()
                if reply:
                    return reply
                return "Ollama returned an empty response. Try rephrasing."

            except _requests.exceptions.ConnectionError:
                return (
                    "⚠️ Cannot reach Ollama at http://localhost:11434. "
                    "Make sure the Ollama app is running (check the system tray), "
                    "then try again."
                )
            except _requests.exceptions.Timeout:
                if attempt < MAX_RETRIES:
                    logger.warning("Ollama timeout (attempt %d/%d), retrying…", attempt, MAX_RETRIES)
                    time.sleep(BASE_DELAY_S * (BACKOFF_FACTOR ** (attempt - 1)))
                    continue
                return (
                    f"⏳ Ollama timed out after {self._ollama_timeout:.0f}s. "
                    "The model may still be loading — try again in a few seconds."
                )
            except Exception as exc:
                status = _extract_status_code(exc)
                if status in _RETRYABLE_STATUS and attempt < MAX_RETRIES:
                    delay = BASE_DELAY_S * (BACKOFF_FACTOR ** (attempt - 1))
                    logger.warning("Ollama HTTP %s (attempt %d/%d), retrying in %.1fs…",
                                   status, attempt, MAX_RETRIES, delay)
                    time.sleep(delay)
                    continue
                logger.error("Ollama error: %s", exc)
                return (
                    f"Ollama error: {str(exc)[:180]}. "
                    "Check that Ollama is running and the model is downloaded."
                )

        return "Ollama did not respond after all retries. Please check the Ollama service."

    # ── Gemini path ──────────────────────────────────────────────────────────

    def _explain_gemini(self, prompt: str) -> str:
        """Call Gemini API with retry + quota cooldown."""
        if not self._gemini_key:
            return (
                "Gemini provider selected but GEMINI_API_KEY is not set. "
                "Set LLM_PROVIDER=ollama in .env to use local Ollama instead."
            )
        remaining = self._quota_cooldown_until - time.monotonic()
        if remaining > 0:
            return (
                f"⏳ Gemini quota exceeded — cooling off for ~{int(remaining)}s more. "
                "Or switch LLM_PROVIDER=ollama in .env for unlimited free usage."
            )

        delay = BASE_DELAY_S
        last_exc: Optional[Exception] = None
        is_quota = False

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return self._call_gemini(prompt)
            except Exception as exc:
                last_exc = exc
                status = _extract_status_code(exc)
                is_quota = (status == 429)
                if status in _RETRYABLE_STATUS and attempt < MAX_RETRIES:
                    logger.warning("Gemini attempt %d/%d (HTTP %s) → retry in %.1fs",
                                   attempt, MAX_RETRIES, status, delay)
                    time.sleep(delay)
                    delay *= BACKOFF_FACTOR
                else:
                    break

        if is_quota:
            self._quota_cooldown_until = time.monotonic() + COOLDOWN_AFTER_429
            return (
                "⚠️ Gemini quota exceeded (HTTP 429). Free-tier limit reached. "
                "Tip: switch LLM_PROVIDER=ollama in .env for unlimited free usage."
            )
        return (
            f"Gemini error: {str(last_exc)[:180]}. "
            "Check API key and quota at aistudio.google.com."
        )

    def _call_gemini(self, prompt: str) -> str:
        """Low-level Gemini SDK call."""
        try:
            import google.generativeai as genai
        except ImportError:
            return "Install google-generativeai to use Gemini."
        genai.configure(api_key=self._gemini_key)
        model    = genai.GenerativeModel(self._gemini_model)
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=256,
                temperature=0.3,
            ),
        )
        if not response:
            return "No response from Gemini."
        try:
            if response.text:
                return response.text.strip()
        except Exception:
            pass
        try:
            for c in getattr(response, "candidates", []):
                for part in getattr(getattr(c, "content", None), "parts", []):
                    text = getattr(part, "text", None)
                    if text and text.strip():
                        return text.strip()
        except Exception:
            pass
        return "Gemini returned a blocked or empty response. Try rephrasing."

    # ── Casual pattern detection ─────────────────────────────────────────────
    _CASUAL_PATTERNS = {
        "hi", "hello", "hey", "hii", "hiii", "heya", "howdy",
        "good morning", "good afternoon", "good evening", "good night",
        "thanks", "thank you", "ty", "thx", "ok", "okay", "sure",
        "bye", "goodbye", "see you", "later", "great", "awesome", "cool",
        "who are you", "what are you", "what can you do", "help",
        "what is battwise", "tell me about yourself", "introduce yourself",
    }

    # All solar/battery domain keywords — used to detect technical questions
    _SOLAR_KEYWORDS = {
        # Battery chemistry & specs
        "battery", "lifepo4", "lithium", "lead acid", "agm", "gel", "nickel",
        "soc", "state of charge", "dod", "depth of discharge", "capacity",
        "ah", "amp hour", "kwh", "kilowatt", "wh", "watt hour", "cell",
        "bms", "battery management", "balancing", "internal resistance",
        "cycle", "lifespan", "degradation", "calendar aging", "c-rate",
        # Solar panels & generation
        "solar", "panel", "pv", "photovoltaic", "monocrystalline", "polycrystalline",
        "thin film", "bifacial", "watt peak", "wp", "irradiance", "insolation",
        "peak sun hours", "shading", "tilt angle", "orientation", "azimuth",
        "bypass diode", "hotspot", "soiling", "efficiency", "generation",
        # Inverters & charge controllers
        "inverter", "mppt", "pwm", "charge controller", "buck converter",
        "grid-tie", "off-grid", "hybrid", "pure sine", "modified sine",
        "ac coupling", "dc coupling", "micro inverter", "string inverter",
        "power factor", "frequency", "voltage", "volt", "ampere", "current",
        # System & storage
        "charge", "discharge", "charging", "discharging", "overcharge",
        "over discharge", "deep discharge", "shallow discharge",
        "self-discharge", "float charge", "bulk charge", "absorption",
        "equalization", "stress", "health", "risk", "status",
        "storage", "reserve", "backup", "off peak", "peak",
        # Energy management
        "energy", "load", "appliance", "consumption", "demand",
        "plan", "schedule", "usage", "budget", "forecast",
        "grid", "utility", "net metering", "feed-in tariff", "export",
        "import", "autarky", "self-consumption", "self-sufficiency",
        # Maintenance & troubleshooting
        "temperature", "thermal", "heat", "cold", "moisture", "humidity",
        "fuse", "breaker", "wiring", "cable", "connector", "terminal",
        "grounding", "earthing", "arc fault", "ground fault",
        "maintenance", "cleaning", "inspection", "warranty",
        # Monitoring & data
        "monitor", "dashboard", "alert", "alarm", "anomaly", "data",
        "telemetry", "log", "history", "trend", "forecast",
        "wifi", "modbus", "can bus", "rs485", "bluetooth", "app",
        # Economic
        "cost", "roi", "payback", "savings", "tariff", "price",
        "subsidy", "incentive", "installation", "system size",
    }

    def _is_casual(self, message: str) -> bool:
        """Return True if the message is a casual/conversational phrase."""
        if not message:
            return False
        clean = message.strip().lower().rstrip("!?. ")
        if clean in self._CASUAL_PATTERNS:
            return True
        # Short message with no solar/battery keywords → treat as casual
        if len(clean.split()) <= 3 and not any(kw in clean for kw in self._SOLAR_KEYWORDS):
            return True
        return False

    def _is_solar_topic(self, message: str) -> bool:
        """Return True if the message touches any solar/battery domain topic."""
        if not message:
            return False
        clean = message.strip().lower()
        return any(kw in clean for kw in self._SOLAR_KEYWORDS)

    # ── Master system persona ────────────────────────────────────────────────
    _SYSTEM_PERSONA = (
        "You are BattWise AI, a friendly and knowledgeable expert on:\n"
        "  • LiFePO4 and all types of solar batteries (chemistry, cycles, BMS, aging)\n"
        "  • Solar PV systems (panels, inverters, MPPT/PWM controllers, wiring, sizing)\n"
        "  • Off-grid, hybrid, and grid-tie solar setups\n"
        "  • Energy management (load planning, peak/off-peak, net metering)\n"
        "  • Battery health monitoring, stress analysis, and maintenance\n"
        "  • Troubleshooting common solar + battery issues\n"
        "  • Costs, ROI, subsidies, and installation best practices\n\n"
        "Rules:\n"
        "  - Answer in 2-4 concise sentences. Be specific and actionable.\n"
        "  - If you don't have exact data, give a helpful general answer based on your expertise.\n"
        "  - Never say 'I don't know' — always provide something useful and relevant.\n"
        "  - If the question is completely unrelated to solar/batteries, politely say you specialise "
        "in solar and battery systems and redirect them to ask about that.\n"
        "  - Reply ONLY with the explanation — no code, no JSON, no bullet formatting.\n"
    )

    def _build_prompt(self, context: Dict[str, Any], user_message: Optional[str]) -> str:
        """Build an appropriate prompt: casual / solar-technical / off-topic redirect."""
        msg = user_message or ""

        # 1. Casual greeting / small talk
        if self._is_casual(msg):
            return (
                "You are BattWise AI, a warm and helpful assistant for solar + battery users.\n"
                "Reply warmly in 1-2 sentences. If the user greets you, introduce yourself and "
                "mention you can help with battery health, solar panels, energy plans, charging, "
                "inverters, maintenance, costs, and more.\n\n"
                f"User: {msg}\nBattWise AI:"
            )

        # 2. Solar / battery technical question
        parts = [self._SYSTEM_PERSONA]

        if context:
            parts.append("\nLive battery system data (use this for specific answers):\n")
            parts.append(json.dumps(context, indent=2))
            parts.append("\n")

        if msg:
            parts.append(f"\nUser question: {msg}")

        parts.append("\n\nBattWise AI:")
        return "".join(parts)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_status_code(exc: Exception) -> Optional[int]:
    """Best-effort HTTP status code extraction from any exception type."""
    for attr in ("code", "status_code"):
        val = getattr(exc, attr, None)
        if isinstance(val, int):
            return val
    # gRPC RESOURCE_EXHAUSTED (8) → HTTP 429
    code = getattr(exc, "code", None)
    grpc_val = getattr(code, "value", None)
    if isinstance(grpc_val, tuple) and len(grpc_val) >= 1 and grpc_val[0] == 8:
        return 429
    msg = str(exc).lower()
    if "429" in msg or "resource_exhausted" in msg or "quota" in msg:
        return 429
    if "500" in msg:
        return 500
    if "503" in msg:
        return 503
    return None

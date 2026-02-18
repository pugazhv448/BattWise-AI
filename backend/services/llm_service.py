"""
LLM service: calls Gemini API to convert structured system output to human explanation.
Environment-based key; graceful fallback when key missing or API fails.
Must not block core logic.
"""
import json
from typing import Any, Dict, Optional

from backend.config import get_settings


class LLMService:
    """
    Optional explanation layer via Gemini. If key missing or request fails,
    returns fallback text without raising. Core logic never depends on this.
    """

    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self.model = settings.gemini_model
        self.timeout = settings.gemini_timeout_seconds
        self._available = bool(self.api_key and self.api_key.strip())

    @property
    def available(self) -> bool:
        return self._available

    def explain(
        self,
        context: Dict[str, Any],
        user_message: Optional[str] = None,
    ) -> str:
        """
        Send context + optional user message to Gemini; return explanation text.
        On failure or if unavailable, return fallback string (no exception).
        """
        fallback = (
            "BattWise AI is running in offline mode. "
            "Add GEMINI_API_KEY to .env for natural language explanations."
        )
        if not self._available:
            return fallback
        prompt = self._build_prompt(context, user_message)
        try:
            return self._call_gemini(prompt) or fallback
        except Exception as e:
            return f"Gemini API error: {str(e)[:200]}. Check your API key and quota at aistudio.google.com."

    def _build_prompt(self, context: Dict[str, Any], user_message: Optional[str]) -> str:
        """Build prompt for Gemini from structured context."""
        parts = [
            "You are BattWise AI, a friendly assistant for LiFePO4 battery and solar household users. "
            "Explain the following system output in 2–4 short sentences. Be concise and actionable.\n\n",
            "System context (JSON):\n",
            json.dumps(context, indent=2),
        ]
        if user_message:
            parts.append("\n\nUser question: " + user_message)
        parts.append("\n\nReply with only the explanation, no code or JSON.")
        return "".join(parts)

    def _call_gemini(self, prompt: str) -> str:
        """Call Gemini API. Raises on network/API errors. Handles blocked/empty responses."""
        try:
            import google.generativeai as genai
        except ImportError:
            return "Install google-generativeai for Gemini support."
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model)
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=256,
                temperature=0.3,
            ),
        )
        if not response:
            return "No response from Gemini."
        # response.text can raise if content blocked or no valid Part (see Gemini API issue #461)
        try:
            if response.text:
                return response.text.strip()
        except Exception:
            pass
        # Fallback: extract text from candidates/parts so we don't crash on blocked reply
        try:
            if getattr(response, "candidates", None):
                for c in response.candidates:
                    content = getattr(c, "content", None)
                    parts = getattr(content, "parts", []) if content else []
                    for part in parts:
                        text = getattr(part, "text", None)
                        if text and text.strip():
                            return text.strip()
        except Exception:
            pass
        return "Gemini could not generate a reply (content filter or empty). Try rephrasing."

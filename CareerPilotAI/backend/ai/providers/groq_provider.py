"""
CareerPilot AI — Groq Provider
Production AI provider backed by the Groq API (cloud LLM inference).

Implements the BaseProvider interface using the official `groq` Python SDK.
Supports:
  - Single-turn generation (via chat completions)
  - Multi-turn chat completions
  - Streaming chat completions
  - JSON mode (response_format={"type": "json_object"})
  - Automatic retry with exponential backoff (configurable via AI_MAX_RETRIES)

Required environment variables:
    GROQ_API_KEY  — Your Groq API key (from console.groq.com)
    GROQ_MODEL    — Model ID, e.g. "llama-3.3-70b-versatile"
    GROQ_TIMEOUT  — Request timeout in seconds (default: 60)
    AI_MAX_RETRIES — Number of retry attempts on transient errors (default: 3)
"""

import time
from typing import Dict, Any, List, Generator

from backend.ai.providers.base_provider import BaseProvider
from backend.config import Config
from backend.utils.logger import ai_logger


class GroqProvider(BaseProvider):
    """
    AI provider backed by Groq cloud API.
    Uses the official groq Python SDK under the hood.
    """

    def __init__(self):
        # Lazy import so the groq package is optional at module load time.
        # If someone runs in "ollama" mode without groq installed, no ImportError.
        try:
            from groq import Groq, APIConnectionError, RateLimitError, APIStatusError
            self._Groq = Groq
            self._APIConnectionError = APIConnectionError
            self._RateLimitError = RateLimitError
            self._APIStatusError = APIStatusError
        except ImportError as exc:
            raise ImportError(
                "The 'groq' package is required for the Groq provider. "
                "Install it with: pip install groq"
            ) from exc

        self.api_key = Config.GROQ_API_KEY
        self.model   = Config.GROQ_MODEL
        self.timeout = Config.GROQ_TIMEOUT
        self.max_retries = Config.AI_MAX_RETRIES

        self._client = None
        if self.api_key:
            self._client = self._Groq(api_key=self.api_key, timeout=self.timeout)
            ai_logger.info(f"[GroqProvider] Initialized — model={self.model}")
        else:
            ai_logger.warning("[GroqProvider] GROQ_API_KEY is missing! API calls will fail.")
            
    def _ensure_client(self):
        """Raises a safe error string instead of crashing Flask if the key is missing."""
        if not self._client:
            raise ValueError("GROQ_API_KEY is missing. Please set it in your .env file.")

    # ── Health ────────────────────────────────────────────────────

    def health(self) -> bool:
        """Check Groq API reachability by listing available models."""
        try:
            self._client.models.list()
            return True
        except Exception as exc:
            ai_logger.warning(f"[GroqProvider] health() failed: {exc}")
            return False

    def check_connection(self) -> Dict[str, Any]:
        """Extended connection diagnostics for the admin panel / startup logs."""
        start = time.time()
        try:
            models_response = self._client.models.list()
            latency = (time.time() - start) * 1000
            model_ids = [m.id for m in models_response.data]
            model_found = self.model in model_ids
            return {
                "success":     True,
                "running":     True,
                "model_found": model_found,
                "model":       self.model,
                "latency_ms":  round(latency, 2),
                "provider":    "groq",
                "available_models": model_ids[:10],   # show first 10
            }
        except Exception as exc:
            return {
                "success":  False,
                "running":  False,
                "error":    str(exc),
                "provider": "groq",
            }

    # ── Core Methods ─────────────────────────────────────────────

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Single-turn generation.
        Groq doesn't have a raw /generate endpoint, so we wrap the prompt
        in a user message and call chat completions.
        """
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, temperature=temperature, json_mode=json_mode)

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Multi-turn chat completion via Groq API with automatic retry.
        """
        ai_logger.debug(
            f"[GroqProvider] chat() | model={self.model}, msgs={len(messages)}, "
            f"json_mode={json_mode}, temp={temperature}"
        )

        kwargs = {
            "model":       self.model,
            "messages":    messages,
            "temperature": temperature,
            "stream":      False,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        last_error: Exception = None

        for attempt in range(1, self.max_retries + 1):
            try:
                start = time.time()
                response = self._client.chat.completions.create(**kwargs)
                latency  = (time.time() - start) * 1000

                content = response.choices[0].message.content or ""
                usage   = response.usage

                ai_logger.debug(
                    f"[GroqProvider] chat() success | attempt={attempt}, "
                    f"latency={latency:.0f}ms, tokens={usage.total_tokens if usage else 'n/a'}"
                )

                return self._success_response(
                    content=content,
                    metrics={
                        "latency_ms":         round(latency, 2),
                        "prompt_tokens":      usage.prompt_tokens      if usage else 0,
                        "completion_tokens":  usage.completion_tokens  if usage else 0,
                        "total_tokens":       usage.total_tokens       if usage else 0,
                        "model":              response.model,
                        "finish_reason":      response.choices[0].finish_reason,
                    }
                )

            except self._RateLimitError as exc:
                last_error = exc
                wait = 2 ** attempt          # exponential backoff: 2, 4, 8 sec
                ai_logger.warning(
                    f"[GroqProvider] Rate limit hit (attempt {attempt}/{self.max_retries}). "
                    f"Retrying in {wait}s…"
                )
                time.sleep(wait)

            except self._APIConnectionError as exc:
                last_error = exc
                wait = 2 ** attempt
                ai_logger.warning(
                    f"[GroqProvider] Connection error (attempt {attempt}/{self.max_retries}): {exc}. "
                    f"Retrying in {wait}s…"
                )
                time.sleep(wait)

            except self._APIStatusError as exc:
                # 4xx errors (bad request, auth) — do NOT retry
                ai_logger.error(f"[GroqProvider] API status error: {exc.status_code} — {exc.message}")
                return self._error_response(f"Groq API error {exc.status_code}: {exc.message}")

            except Exception as exc:
                last_error = exc
                ai_logger.error(f"[GroqProvider] Unexpected error (attempt {attempt}): {exc}", exc_info=True)
                if attempt == self.max_retries:
                    break
                time.sleep(2 ** attempt)

        ai_logger.error(f"[GroqProvider] All {self.max_retries} attempts failed. Last error: {last_error}")
        return self._error_response("Groq API is temporarily unavailable. Please try again.")

    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7
    ) -> Generator[str, None, None]:
        """
        Streaming chat completion — yields text chunks as they arrive from Groq.
        Uses Groq's native streaming (stream=True).
        """
        ai_logger.debug(f"[GroqProvider] stream_chat() | model={self.model}, msgs={len(messages)}")

        try:
            self._ensure_client()
        except ValueError as e:
            yield f"\n\n⚠️ {str(e)}"
            return

        try:
            stream = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content

        except self._RateLimitError:
            ai_logger.error("[GroqProvider] Rate limit hit during streaming.")
            yield "\n\n⚠️ Rate limit reached. Please wait a moment and try again."

        except self._APIConnectionError as exc:
            ai_logger.error(f"[GroqProvider] Connection error during streaming: {exc}")
            yield "\n\n⚠️ Unable to connect to the AI service. Please check your connection."

        except self._APIStatusError as exc:
            ai_logger.error(f"[GroqProvider] API status error during streaming: {exc.status_code}")
            yield f"\n\n⚠️ AI service error ({exc.status_code}). Please try again."

        except Exception as exc:
            ai_logger.error(f"[GroqProvider] Unexpected stream error: {exc}", exc_info=True)
            yield "\n\n⚠️ An unexpected error occurred. Please try again."

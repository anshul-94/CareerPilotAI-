"""
CareerPilot AI — AI Provider Factory
Resolves the correct provider at startup and exposes a module-level singleton.

Usage anywhere in the codebase:
    from backend.ai.providers import ai_gateway

    result = ai_gateway.chat(messages, temperature=0.7)
    result = ai_gateway.generate(prompt, json_mode=True)

    for chunk in ai_gateway.stream_chat(messages):
        yield chunk

The provider is chosen once at application startup via the AI_PROVIDER env var:
    AI_PROVIDER=ollama   →  OllamaProvider  (local development)
    AI_PROVIDER=groq     →  GroqProvider    (production / Render)

To add a new provider (e.g. Gemini):
    1. Create backend/ai/providers/gemini_provider.py implementing BaseProvider
    2. Add an elif branch in get_provider() below
    3. Set AI_PROVIDER=gemini in .env — done, zero other changes needed
"""

import os
import logging

from backend.config import Config
from backend.ai.providers.base_provider import BaseProvider

logger = logging.getLogger("careerpilot.ai")


def get_provider() -> BaseProvider:
    """
    Factory function — reads AI_PROVIDER from environment and returns
    the appropriate provider instance.

    Returns:
        BaseProvider: Concrete provider ready for use.

    Raises:
        ValueError: If AI_PROVIDER contains an unrecognized value.
        ImportError: If a required package for the chosen provider is missing.
        ValueError: If required API keys for the chosen provider are missing.
    """
    provider_name = Config.AI_PROVIDER

    logger.info(f"[AIProvider] Initializing provider: '{provider_name}'")

    if provider_name == "ollama":
        from backend.ai.providers.ollama_provider import OllamaProvider
        return OllamaProvider()

    elif provider_name == "groq":
        from backend.ai.providers.groq_provider import GroqProvider
        return GroqProvider()

    # ── Future providers (uncomment when ready) ──────────────────
    # elif provider_name == "openai":
    #     from backend.ai.providers.openai_provider import OpenAIProvider
    #     return OpenAIProvider()
    #
    # elif provider_name == "gemini":
    #     from backend.ai.providers.gemini_provider import GeminiProvider
    #     return GeminiProvider()
    #
    # elif provider_name == "openrouter":
    #     from backend.ai.providers.openrouter_provider import OpenRouterProvider
    #     return OpenRouterProvider()

    else:
        supported = ["ollama", "groq"]
        raise ValueError(
            f"Unknown AI_PROVIDER='{provider_name}'. "
            f"Supported providers: {supported}. "
            f"Check your .env file."
        )


# ── Module-level Singleton ────────────────────────────────────────
# Resolved once at import time. All modules import this object directly.
# This is intentionally a module-level singleton to avoid repeated env
# lookups and provider re-initialization on every request.
ai_gateway: BaseProvider = get_provider()

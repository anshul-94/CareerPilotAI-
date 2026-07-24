"""
CareerPilot AI — Ollama Provider
Thin adapter that delegates all AI calls to the existing OllamaService.

This provider contains NO business logic — it maps OllamaService's
already-normalized responses to the BaseProvider contract.
"""

from typing import Dict, Any, List, Generator

from backend.ai.providers.base_provider import BaseProvider
from backend.ai.ollama_service import OllamaService
from backend.utils.logger import ai_logger


class OllamaProvider(BaseProvider):
    """
    AI provider backed by a local Ollama server.
    Uses OllamaService internally — zero logic duplication.
    """

    def __init__(self):
        # Instantiate the existing service (reads OLLAMA_HOST / OLLAMA_MODEL from Config)
        self._service = OllamaService()
        ai_logger.info(
            f"[OllamaProvider] Initialized — host={self._service.host}, "
            f"model={self._service.model}"
        )

    # ── Health ────────────────────────────────────────────────────

    def health(self) -> bool:
        return self._service.health()

    def check_connection(self) -> Dict[str, Any]:
        """Delegate to OllamaService's richer connection check."""
        result = self._service.check_connection()
        result["provider"] = "ollama"
        return result

    # ── Core Methods ─────────────────────────────────────────────

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> Dict[str, Any]:
        """Single-turn generation via Ollama /api/generate."""
        ai_logger.debug(f"[OllamaProvider] generate() | json_mode={json_mode}")
        result = self._service.generate(prompt, temperature=temperature, json_mode=json_mode)
        return self._normalize(result)

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> Dict[str, Any]:
        """Multi-turn chat via Ollama /api/chat."""
        ai_logger.debug(f"[OllamaProvider] chat() | msgs={len(messages)}, json_mode={json_mode}")
        result = self._service.chat(messages, temperature=temperature, json_mode=json_mode)
        return self._normalize(result)

    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7
    ) -> Generator[str, None, None]:
        """Streaming chat via Ollama /api/chat (stream=True)."""
        ai_logger.debug(f"[OllamaProvider] stream_chat() | msgs={len(messages)}")
        yield from self._service.stream_chat(messages, temperature=temperature)

    # ── Internal ──────────────────────────────────────────────────

    @staticmethod
    def _normalize(result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure the response always matches the BaseProvider normalized schema.
        OllamaService already returns {success, content, metrics/error}, so
        this is mostly a safety pass-through that fills any missing keys.
        """
        if result.get("success"):
            return {
                "success": True,
                "content": result.get("content", ""),
                "metrics": result.get("metrics", {}),
                "error":   None,
            }
        return {
            "success": False,
            "content": result.get("content", ""),
            "error":   result.get("error", "Unknown Ollama error"),
            "metrics": {},
        }

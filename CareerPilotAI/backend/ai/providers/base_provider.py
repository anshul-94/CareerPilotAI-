"""
CareerPilot AI — Base AI Provider
Abstract interface that every AI provider must implement.

All providers must return a normalized response dict:
    {
        "success":  bool,
        "content":  str,          # the model's text output
        "metrics":  dict,         # latency, token counts, etc. (provider-specific)
        "error":    str | None    # present only on failure
    }
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Generator


class BaseProvider(ABC):
    """Abstract base class for all AI providers."""

    # ── Core Generation Methods ───────────────────────────────────

    @abstractmethod
    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Single-turn text generation from a raw prompt string.

        Args:
            prompt:      The raw text prompt to send to the model.
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative).
            json_mode:   If True, instructs the model to respond with valid JSON only.

        Returns:
            Normalized response dict with keys: success, content, metrics, error.
        """
        raise NotImplementedError

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Multi-turn chat completion from a list of message dicts.

        Args:
            messages:    List of {"role": "user"|"assistant"|"system", "content": str}.
            temperature: Sampling temperature.
            json_mode:   If True, instructs the model to respond with valid JSON only.

        Returns:
            Normalized response dict with keys: success, content, metrics, error.
        """
        raise NotImplementedError

    @abstractmethod
    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7
    ) -> Generator[str, None, None]:
        """
        Streaming chat completion — yields text chunks as they arrive.

        Args:
            messages:    List of {"role": ..., "content": ...} dicts.
            temperature: Sampling temperature.

        Yields:
            str: Individual text chunks from the model stream.
        """
        raise NotImplementedError

    # ── Health & Diagnostics ─────────────────────────────────────

    @abstractmethod
    def health(self) -> bool:
        """
        Quick connectivity check for the underlying AI backend.

        Returns:
            True if the provider is reachable and operational, False otherwise.
        """
        raise NotImplementedError

    def check_connection(self) -> Dict[str, Any]:
        """
        Extended connection check with diagnostic information.
        Providers may override for richer status details.

        Returns:
            Dict with at minimum: {"success": bool, "running": bool}
        """
        is_healthy = self.health()
        return {
            "success": is_healthy,
            "running": is_healthy,
            "provider": self.__class__.__name__,
        }

    def _log_ai_request(self, provider: str, model: str, prompt: str, duration: float, success: bool, metrics: dict):
        from backend.utils.logger import ai_logger
        from flask import has_request_context, session
        
        user_id = session.get('user_id', 'Unknown') if has_request_context() else 'Background'
        
        # Infer a short prompt name from the content
        snippet = prompt[:40].replace('\n', ' ').strip() + "..." if prompt else "Unknown"
        status_str = "Success" if success else "Failed"
        tokens = metrics.get('prompt_tokens', 'N/A')
        
        log_msg = f"""
========== AI REQUEST ==========
User ID       : {user_id}
Provider      : {provider}
Model         : {model}
Prompt Name   : {snippet}
Prompt Tokens : {tokens}
Execution Time: {duration:.2f} sec
Success/Failed: {status_str}
================================"""
        ai_logger.info(log_msg)

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def _error_response(message: str) -> Dict[str, Any]:
        """Build a normalized error response dict."""
        return {
            "success": False,
            "content": message,
            "error":   message,
            "metrics": {}
        }

    @staticmethod
    def _success_response(content: str, metrics: Dict[str, Any] = None) -> Dict[str, Any]:
        """Build a normalized success response dict."""
        return {
            "success": True,
            "content": content,
            "metrics": metrics or {},
            "error":   None
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"

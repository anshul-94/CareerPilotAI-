import requests
import json
import time
from typing import Dict, Any, List, Generator
from backend.config import Config
from backend.utils.logger import ai_logger

class OllamaService:
    """Client for interacting with local Ollama API."""
    
    def __init__(self):
        self.host = Config.OLLAMA_HOST
        self.model = Config.OLLAMA_MODEL

    def health(self) -> bool:
        """Check if Ollama server is responsive."""
        try:
            response = requests.get(f"{self.host}/api/version", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def list_models(self) -> List[str]:
        """List all downloaded Ollama models."""
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            return []
        except requests.exceptions.RequestException:
            return []

    def check_connection(self) -> Dict[str, Any]:
        """Check Ollama status and verify if model is available."""
        start_time = time.time()
        
        if not self.health():
            return {
                "success": False,
                "error": "Ollama server is offline. Run `ollama serve`",
                "running": False
            }
            
        models = self.list_models()
        # Some users put tags, some don't. Check both.
        # e.g., if model is "qwen2.5:7b", it's usually returned as "qwen2.5:7b"
        # If it's "mistral", it might be returned as "mistral:latest"
        model_found = any(m == self.model or m == f"{self.model}:latest" for m in models)
        
        if not model_found:
            return {
                "success": False,
                "error": f"Model not found. Run `ollama pull {self.model}`",
                "running": True,
                "model_found": False
            }
            
        latency = (time.time() - start_time) * 1000 # ms
        
        try:
            version_res = requests.get(f"{self.host}/api/version", timeout=2)
            version = version_res.json().get("version", "unknown") if version_res.status_code == 200 else "unknown"
        except:
            version = "unknown"
            
        return {
            "success": True,
            "running": True,
            "model_found": True,
            "latency_ms": round(latency, 2),
            "version": version,
            "model": self.model,
            "host": self.host
        }

    def _format_error(self, message: str) -> Dict[str, Any]:
        return {
            "success": False,
            "error": message,
            "content": message
        }

    def generate(self, prompt: str, temperature: float = 0.7, json_mode: bool = False) -> Dict[str, Any]:
        """Generate completion using the /api/generate endpoint."""
        if not self.health():
            return self._format_error("Ollama server is offline. Run `ollama serve`")

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        
        if json_mode:
            payload["format"] = "json"

        try:
            start_time = time.time()
            response = requests.post(f"{self.host}/api/generate", json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            latency = (time.time() - start_time) * 1000
            return {
                "success": True,
                "content": data.get("response", ""),
                "metrics": {
                    "prompt_eval_count": data.get("prompt_eval_count", 0),
                    "eval_count": data.get("eval_count", 0),
                    "total_duration": data.get("total_duration", 0),
                    "latency_ms": latency
                }
            }
        except requests.exceptions.RequestException as e:
            ai_logger.error(f"Ollama API Error: {e}", exc_info=True)
            return self._format_error("Failed to communicate with Ollama.")

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, json_mode: bool = False) -> Dict[str, Any]:
        """Chat completion using the /api/chat endpoint."""
        if not self.health():
            return self._format_error("Ollama server is offline. Run `ollama serve`")

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }

        if json_mode:
            payload["format"] = "json"

        try:
            start_time = time.time()
            response = requests.post(f"{self.host}/api/chat", json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            latency = (time.time() - start_time) * 1000
            return {
                "success": True,
                "content": data["message"]["content"],
                "metrics": {
                    "prompt_eval_count": data.get("prompt_eval_count", 0),
                    "eval_count": data.get("eval_count", 0),
                    "total_duration": data.get("total_duration", 0),
                    "latency_ms": latency
                }
            }
        except requests.exceptions.RequestException as e:
            ai_logger.error(f"Ollama API Error: {e}", exc_info=True)
            return self._format_error("Failed to communicate with Ollama.")

    def stream_chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> Generator[str, None, None]:
        """Stream chat completion using the /api/chat endpoint."""
        if not self.health():
            yield "Ollama server is offline. Run `ollama serve`"
            return

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature
            }
        }

        try:
            with requests.post(f"{self.host}/api/chat", json=payload, stream=True, timeout=60) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line.decode('utf-8'))
                            if 'message' in data and 'content' in data['message']:
                                yield data['message']['content']
                        except json.JSONDecodeError:
                            continue
        except requests.exceptions.RequestException as e:
            ai_logger.error(f"Ollama Stream Error: {e}", exc_info=True)
            yield "Failed to communicate with Ollama during streaming."

ollama = OllamaService()

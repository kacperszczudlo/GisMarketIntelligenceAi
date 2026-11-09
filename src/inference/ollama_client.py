import logging
from typing import Any, Dict, List, Optional
import httpx
from src.config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """HTTP client for local Ollama daemon inference with strict grounding and automatic model resolution."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 300.0,
    ) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout

    async def check_health(self) -> bool:
        """Verifies if the Ollama daemon is reachable and responding."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception as e:
            logger.debug("Ollama healthcheck failed: %s", e)
            return False

    async def _resolve_available_model(self, client: httpx.AsyncClient) -> Optional[str]:
        """Queries /api/tags and returns the first installed Ollama model if configured model is absent."""
        try:
            res = await client.get(f"{self.base_url}/api/tags", timeout=5.0)
            if res.status_code == 200:
                models = res.json().get("models", [])
                if models:
                    fallback_name = models[0].get("name") or models[0].get("model")
                    if fallback_name:
                        logger.info(
                            "Model '%s' not found in Ollama; falling back to installed model '%s'",
                            self.model,
                            fallback_name,
                        )
                        self.model = fallback_name
                        return fallback_name
        except Exception as e:
            logger.debug("Could not resolve fallback Ollama model: %s", e)
        return None

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.0,
    ) -> str:
        """Executes non-streaming text completion via Ollama /api/generate."""
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": 0.9,
                "num_ctx": 8192,
            },
        }
        if system:
            payload["system"] = system

        url = f"{self.base_url}/api/generate"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 404:
                resolved = await self._resolve_available_model(client)
                if resolved:
                    payload["model"] = resolved
                    response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
    ) -> str:
        """Executes multi-turn or system-conditioned chat completion via Ollama /api/chat."""
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": 0.9,
                "num_ctx": 8192,
            },
        }

        url = f"{self.base_url}/api/chat"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 404:
                resolved = await self._resolve_available_model(client)
                if resolved:
                    payload["model"] = resolved
                    response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "").strip()

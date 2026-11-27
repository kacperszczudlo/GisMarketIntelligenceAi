import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional
import httpx
from src.config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """HTTP client for local Ollama daemon inference with strict grounding and automatic model resolution."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 180.0,
    ) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout

    def _http_timeout(self) -> httpx.Timeout:
        return httpx.Timeout(self.timeout, connect=5.0)

    async def check_health(self) -> bool:
        """Verifies if the Ollama daemon is reachable and responding."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception as e:
            logger.debug("Ollama healthcheck failed: %s", e)
            return False

    async def _resolve_available_model(self, client: httpx.AsyncClient) -> Optional[str]:
        """Queries /api/tags and returns the first installed Ollama model if configured model is absent."""
        try:
            res = await client.get(f"{self.base_url}/api/tags", timeout=3.0)
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
            "keep_alive": "30m",
            "options": {
                "temperature": temperature,
                "top_p": 0.9,
                "num_ctx": 3072,
                "num_predict": 450,
            },
        }
        if system:
            payload["system"] = system

        url = f"{self.base_url}/api/generate"
        async with httpx.AsyncClient(timeout=self._http_timeout()) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 404:
                resolved = await self._resolve_available_model(client)
                if resolved:
                    payload["model"] = resolved
                    response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()

    async def stream_generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.0,
    ) -> AsyncIterator[str]:
        """Streams completion tokens via Ollama /api/generate."""
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "keep_alive": "30m",
            "options": {
                "temperature": temperature,
                "top_p": 0.9,
                "num_ctx": 3072,
                "num_predict": 500,
            },
        }
        if system:
            payload["system"] = system

        url = f"{self.base_url}/api/generate"
        async with httpx.AsyncClient(timeout=self._http_timeout()) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code == 404:
                    resolved = await self._resolve_available_model(client)
                    if resolved:
                        payload["model"] = resolved
                        async with client.stream("POST", url, json=payload) as retry_resp:
                            retry_resp.raise_for_status()
                            async for line in retry_resp.aiter_lines():
                                if not line:
                                    continue
                                chunk = json.loads(line)
                                token = chunk.get("response", "")
                                if token:
                                    yield token
                            return
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    token = chunk.get("response", "")
                    if token:
                        yield token

    async def generate_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executes structured JSON output generation via Ollama /api/generate."""
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": schema,
            "options": {
                "temperature": 0.0,
                "num_ctx": 2048,
                "num_predict": 300,
            },
        }
        if system:
            payload["system"] = system

        url = f"{self.base_url}/api/generate"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 404:
                    resolved = await self._resolve_available_model(client)
                    if resolved:
                        payload["model"] = resolved
                        response = await client.post(url, json=payload)
                response.raise_for_status()
                raw = response.json().get("response", "").strip()
                parsed = json.loads(raw) if raw else {}
                return parsed if isinstance(parsed, dict) else {}
        except Exception as exc:
            logger.debug("Structured JSON generation skipped (%s)", exc)
            return {}

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
                "num_ctx": 2048,
                "num_predict": 350,
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

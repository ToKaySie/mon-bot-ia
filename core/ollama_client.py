"""
Ollama Cloud API client.
Uses the OpenAI-compatible API endpoint provided by Ollama Cloud.
"""

import logging
import httpx

from core.config import BotConfig

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with Ollama Cloud's OpenAI-compatible API."""

    def __init__(self, config: BotConfig):
        self.config = config
        self.base_url = config.ollama_api_url.rstrip("/")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.ollama_api_key}",
        }

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: list[dict] | None = None,
    ) -> dict:
        """
        Send a chat completion request to Ollama Cloud.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            model: Model to use (defaults to config model).
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in the response.

        Returns:
            The assistant's response text.
        """
        model = model or self.config.ollama_model

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        
        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()

                data = response.json()
                return data["choices"][0]["message"]

        except httpx.TimeoutException:
            logger.error("Ollama Cloud API timeout")
            raise OllamaError("⏳ Le serveur IA met trop de temps à répondre. Réessayez.")

        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama Cloud API HTTP error: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 401:
                raise OllamaError("🔑 Clé API Ollama invalide. Vérifiez votre configuration.")
            elif e.response.status_code == 429:
                raise OllamaError("⚠️ Trop de requêtes. Attendez un moment avant de réessayer.")
            elif e.response.status_code == 404:
                raise OllamaError(f"❌ Modèle '{model}' non trouvé sur Ollama Cloud.")
            else:
                raise OllamaError(f"❌ Erreur API ({e.response.status_code}). Réessayez plus tard.")

        except httpx.RequestError as e:
            logger.error(f"Ollama Cloud API request error: {e}")
            raise OllamaError("🌐 Impossible de contacter le serveur Ollama Cloud.")

        except (KeyError, IndexError) as e:
            logger.error(f"Unexpected API response format: {e}")
            raise OllamaError("❌ Réponse inattendue du serveur IA.")

    async def list_models(self) -> list[str]:
        """List available models from Ollama Cloud."""
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=self.headers,
                )
                response.raise_for_status()
                data = response.json()
                return [m["id"] for m in data.get("data", [])]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []


class OllamaError(Exception):
    """Custom exception for Ollama API errors."""

    pass

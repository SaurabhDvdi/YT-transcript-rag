"""Google Gemini LLM provider using REST API with streaming support."""

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from src.core.errors import AppError
from src.services.generation.types import (
    LLMGenerationRequest,
    LLMGenerationResponse,
    LLMStreamChunk,
)


class GeminiProvider:
    """Production Gemini LLM provider using Google Generative Language REST API."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-1.5-flash",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("Gemini API key is required")
        self.name: str = "gemini"
        self.api_key: str = api_key.strip()
        self.model: str = model
        self.base_url: str = base_url.rstrip("/")
        self._client = client

    def _sanitize(self, message: str) -> str:
        return message.replace(self.api_key, "[REDACTED_API_KEY]")

    def _build_payload(self, request: LLMGenerationRequest) -> dict[str, Any]:
        return {
            "system_instruction": {
                "parts": [{"text": request.system_prompt}],
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": request.user_prompt}],
                }
            ],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_output_tokens,
            },
        }

    async def generate(self, request: LLMGenerationRequest) -> LLMGenerationResponse:
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        payload = self._build_payload(request)

        client = self._client or httpx.AsyncClient(timeout=15.0)
        close_client = self._client is None

        try:
            resp = await client.post(url, json=payload)
        except httpx.TimeoutException:
            raise AppError("LLM_TIMEOUT", 504, "Gemini generation request timed out") from None
        except Exception as e:
            raise AppError(
                "LLM_PROVIDER_UNAVAILABLE",
                503,
                self._sanitize(f"Failed to connect to Gemini API: {e}"),
            ) from e
        finally:
            if close_client:
                await client.aclose()

        if resp.status_code != 200:
            err_detail = f"HTTP {resp.status_code}"
            try:
                err_json = resp.json()
                if "error" in err_json and "message" in err_json["error"]:
                    err_detail = err_json["error"]["message"]
            except Exception:
                pass

            sanitized = self._sanitize(err_detail)
            if resp.status_code in (429, 503):
                raise AppError(
                    "LLM_PROVIDER_UNAVAILABLE",
                    503,
                    f"Gemini API temporarily unavailable ({sanitized})",
                )
            raise AppError(
                "GENERATION_FAILED",
                500,
                f"Gemini API generation error: {sanitized}",
            )

        try:
            data = resp.json()
        except Exception as e:
            raise AppError(
                "LLM_OUTPUT_INVALID", 502, "Received malformed JSON response from Gemini API"
            ) from e

        candidates = data.get("candidates", [])
        if not candidates:
            raise AppError(
                "LLM_OUTPUT_INVALID", 502, "Gemini API returned an empty candidates array"
            )

        parts = candidates[0].get("content", {}).get("parts", [])
        text_part = parts[0].get("text") if parts else None
        if not isinstance(text_part, str):
            raise AppError(
                "LLM_OUTPUT_INVALID", 502, "Gemini API candidate contained no text content"
            )

        usage = data.get("usageMetadata", {})
        return LLMGenerationResponse(
            text=text_part.strip(),
            provider=self.name,
            model=self.model,
            input_tokens=usage.get("promptTokenCount"),
            output_tokens=usage.get("candidatesTokenCount"),
            finish_reason=candidates[0].get("finishReason"),
        )

    async def stream(self, request: LLMGenerationRequest) -> AsyncIterator[LLMStreamChunk]:
        url = (
            f"{self.base_url}/models/{self.model}:streamGenerateContent?alt=sse&key={self.api_key}"
        )
        payload = self._build_payload(request)

        client = self._client or httpx.AsyncClient(timeout=30.0)
        close_client = self._client is None

        try:
            async with client.stream("POST", url, json=payload) as resp:
                if resp.status_code != 200:
                    err_detail = f"HTTP {resp.status_code}"
                    sanitized = self._sanitize(err_detail)
                    if resp.status_code in (429, 503):
                        raise AppError(
                            "LLM_PROVIDER_UNAVAILABLE",
                            503,
                            f"Gemini API temporarily unavailable ({sanitized})",
                        )
                    raise AppError(
                        "GENERATION_FAILED",
                        500,
                        f"Gemini API generation error: {sanitized}",
                    )

                async for line in resp.aiter_lines():
                    trimmed = line.strip()
                    if trimmed.startswith("data:"):
                        data_str = trimmed[5:].strip()
                        if not data_str or data_str == "[DONE]":
                            continue

                        try:
                            item = json.loads(data_str)
                            candidates = item.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                text = parts[0].get("text") if parts else None
                                if text:
                                    is_finished = candidates[0].get("finishReason") == "STOP"
                                    yield LLMStreamChunk(text=text, is_finished=is_finished)
                        except Exception:
                            pass
        except (AppError, GeneratorExit):
            raise
        except httpx.TimeoutException:
            raise AppError("LLM_TIMEOUT", 504, "Gemini streaming timed out") from None
        except Exception as e:
            raise AppError(
                "LLM_PROVIDER_UNAVAILABLE",
                503,
                self._sanitize(f"Failed to connect to Gemini API: {e}"),
            ) from e
        finally:
            if close_client:
                await client.aclose()

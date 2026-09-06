"""Cloudflare Workers AI LLM provider using Workers AI binding."""

import json
from collections.abc import AsyncIterator
from typing import Any

from src.core.errors import AppError
from src.services.generation.types import (
    LLMGenerationRequest,
    LLMGenerationResponse,
    LLMStreamChunk,
)


class CloudflareWorkersAiLLMProvider:
    """Cloudflare Workers AI LLM provider using @cf/meta/llama-3.1-8b-instruct."""

    def __init__(
        self,
        ai_binding: Any,
        model: str = "@cf/meta/llama-3.1-8b-instruct",
    ) -> None:
        if not ai_binding:
            raise ValueError("CloudflareWorkersAi binding is required")
        self.name: str = "cloudflare-workers-ai"
        self.model: str = model
        self.ai_binding = ai_binding

    async def generate(self, request: LLMGenerationRequest) -> LLMGenerationResponse:
        try:
            result = await self.ai_binding.run(
                self.model,
                {
                    "messages": [
                        {"role": "system", "content": request.system_prompt},
                        {"role": "user", "content": request.user_prompt},
                    ],
                    "max_tokens": request.max_output_tokens,
                    "temperature": request.temperature,
                },
            )

            response_text: str | None = None
            if isinstance(result, dict) and "response" in result:
                response_text = str(result["response"])
            elif isinstance(result, str):
                response_text = result

            if not response_text:
                raise AppError(
                    "LLM_OUTPUT_INVALID",
                    502,
                    "Cloudflare Workers AI returned empty text response",
                )

            return LLMGenerationResponse(
                text=response_text.strip(),
                provider=self.name,
                model=self.model,
            )
        except AppError:
            raise
        except Exception as err:
            raise AppError(
                "LLM_PROVIDER_UNAVAILABLE",
                503,
                f"Cloudflare Workers AI generation failed: {err}",
            ) from err

    async def stream(self, request: LLMGenerationRequest) -> AsyncIterator[LLMStreamChunk]:
        try:
            result = await self.ai_binding.run(
                self.model,
                {
                    "messages": [
                        {"role": "system", "content": request.system_prompt},
                        {"role": "user", "content": request.user_prompt},
                    ],
                    "max_tokens": request.max_output_tokens,
                    "temperature": request.temperature,
                    "stream": True,
                },
            )

            if hasattr(result, "__aiter__"):
                async for item in result:
                    if isinstance(item, (bytes, bytearray)):
                        text = item.decode("utf-8")
                    else:
                        text = str(item)
                    for line in text.split("\n"):
                        trimmed = line.strip()
                        if trimmed.startswith("data:"):
                            data_str = trimmed[5:].strip()
                            if not data_str or data_str == "[DONE]":
                                continue
                            try:
                                data = json.loads(data_str)
                                if "response" in data:
                                    yield LLMStreamChunk(text=data["response"])
                            except Exception:
                                pass
            elif isinstance(result, dict) and "response" in result:
                yield LLMStreamChunk(text=str(result["response"]), is_finished=True)
            elif isinstance(result, str):
                yield LLMStreamChunk(text=result, is_finished=True)
            else:
                raise AppError(
                    "LLM_OUTPUT_INVALID",
                    502,
                    "Workers AI did not return a valid readable stream",
                )
        except (AppError, GeneratorExit):
            raise
        except Exception as err:
            raise AppError(
                "LLM_PROVIDER_UNAVAILABLE",
                503,
                f"Cloudflare Workers AI streaming failed: {err}",
            ) from err

from collections.abc import AsyncIterator

from openai import AsyncOpenAI, OpenAI

from app.shared.config import settings


class OpenAICompatibleClient:
    """Client for OpenAI-compatible chat completion providers."""

    def __init__(self) -> None:
        if not settings.llm_api_key:
            raise RuntimeError("LLM_API_KEY is required")

        self._client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=settings.llm_timeout_seconds,
        )
        self._async_client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=settings.llm_timeout_seconds,
        )

    @staticmethod
    def _thinking_extra_body(thinking_mode: str | None) -> dict | None:
        """把 thinking_mode 转成网关约定的 extra_body；None 表示不干预默认行为。"""
        if thinking_mode is None:
            return None
        return {"thinking": {"type": thinking_mode}}

    def chat(self, messages: list[dict[str, str]], thinking_mode: str | None = None) -> str:
        kwargs: dict = {}
        extra_body = self._thinking_extra_body(thinking_mode)
        if extra_body is not None:
            kwargs["extra_body"] = extra_body
        response = self._client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            temperature=settings.llm_temperature,
            **kwargs,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("LLM returned empty content")
        return content.strip()

    async def achat_stream(
        self,
        messages: list[dict[str, str]],
        thinking_mode: str | None = None,
    ) -> AsyncIterator[str]:
        """Async streaming chat completions, yielding content text chunks.

        断连时上游协程会被取消，`finally` 里的 `aclose` 负责释放底层 HTTP 连接。
        """
        kwargs: dict = {}
        extra_body = self._thinking_extra_body(thinking_mode)
        if extra_body is not None:
            kwargs["extra_body"] = extra_body
        stream = await self._async_client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            temperature=settings.llm_temperature,
            stream=True,
            **kwargs,
        )
        try:
            async for event in stream:
                if not event.choices:
                    continue
                content = event.choices[0].delta.content
                if content:
                    yield content
        finally:
            await stream.close()

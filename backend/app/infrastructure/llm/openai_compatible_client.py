from collections.abc import Iterator

from openai import OpenAI

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

    def chat(self, messages: list[dict[str, str]]) -> str:
        response = self._client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            temperature=settings.llm_temperature,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("LLM returned empty content")
        return content.strip()

    def chat_stream(self, messages: list[dict[str, str]]) -> Iterator[str]:
        """Stream chat completions, yielding content text chunks incrementally.

        The iterator is consumed lazily; closing it stops the underlying stream.
        """
        stream = self._client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            temperature=settings.llm_temperature,
            stream=True,
        )
        try:
            for event in stream:
                if not event.choices:
                    continue
                content = event.choices[0].delta.content
                if content:
                    yield content
        finally:
            stream.close()

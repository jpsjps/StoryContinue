from typing import AsyncIterator

from openai import AsyncOpenAI
import anthropic


class LLMAdapter:
    """
    Thin wrapper to unify OpenAI-compatible and Anthropic streaming calls.
    For now we only fully implement OpenAI; Anthropic can be added later.
    """

    def __init__(self, provider: str, api_key: str, api_base: str | None = None):
        self.provider = provider
        self.api_key = api_key
        self.api_base = api_base

        if provider == "openai":
            self._client = AsyncOpenAI(api_key=api_key, base_url=api_base)
        elif provider == "anthropic":
            self._client = anthropic.AsyncAnthropic(api_key=api_key)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    async def generate_stream(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        if self.provider == "openai":
            async for chunk in self._stream_openai(
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
            ):
                yield chunk
        elif self.provider == "anthropic":
            async for chunk in self._stream_anthropic(
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
            ):
                yield chunk

    async def generate_text(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = 0.2,
    ) -> str:
        """
        非流式文本生成，用于构建上下文摘要/长期记忆等场景。
        目前主要实现 OpenAI。
        """
        if self.provider != "openai":
            raise NotImplementedError("generate_text 目前只实现 OpenAI 版本。")

        resp = await self._client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        content = resp.choices[0].message.content if resp.choices else None
        return content or ""

    async def _stream_openai(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None,
    ) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    async def _stream_anthropic(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None,
    ) -> AsyncIterator[str]:
        # Simple Anthropic streaming scaffold; can be tuned later.
        client: anthropic.AsyncAnthropic = self._client
        with client.messages.stream(
            model=model,
            system=system_prompt,
            max_tokens=max_tokens or 2048,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            async for event in stream:
                if event.type == "content_block_delta":
                    text = getattr(event.delta, "text", None)
                    if text:
                        yield text


import asyncio
import os
from collections.abc import AsyncGenerator
from typing import Any

from dotenv import load_dotenv
from openai import APIConnectionError, APIError, AsyncOpenAI, RateLimitError

from client.response import StreamEvent, StreamEventType, TextDelta, TokenUsage

load_dotenv()

class LLMClient:
    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None
        self.api_key: str = os.getenv('OPENROUTER_API_KEY')
        self._max_retries: int = 3

    async def get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url="https://openrouter.ai/api/v1"
            )
            
        return self._client
    
    async def close(self):
        if self._client:
            await self._client.close()
            self._client = None
    

    async def chat_completion(
        self, 
        messages: list[dict[str, Any]], 
        stream: bool = True
    ) -> AsyncGenerator[StreamEvent, None]: 
        client = await self.get_client()
        
        kwargs = {
            "model": "inclusionai/ling-3.0-flash-fin:free",
            "stream": stream,
            "messages": messages    
        }
        for attempt in range(self._max_retries + 1):
            try:  
                if stream:
                    async for event in self._stream_response(client=client, kwargs=kwargs):
                        yield event
                else:
                    yield self._get_response(client=client, kwargs=kwargs)
                    
                return
            except RateLimitError as e:
                if attempt < self._max_retries:
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                else:   
                    yield StreamEvent(
                        type=StreamEventType.ERROR,
                        error=f"Rate limit exceeded: {e}"
                    )
                    return
                    
            except APIConnectionError as e:
                if attempt < self._max_retries:
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                else:
                    yield StreamEvent(
                        type=StreamEventType.ERROR,
                        error=f"API Connection error {e}"
                    )
                    return
                
            except APIError as e:
                yield StreamEvent(
                    type=StreamEventType.ERROR,
                    error=f"API Error: {e}"
                )
        return
        
    async def _get_response(
        self,
        client: AsyncOpenAI, 
        kwargs: dict[str, Any]
    ):
        response = await client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message
        
        text_delta = None
        if message.content:
            text_delta = TextDelta(content=message.content)
        
        usage = None
        if response.usage:
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                cached_tokens=response.usage.prompt_tokens_details.cached_tokens
            )
        
        return StreamEvent(
            type=StreamEventType.MESSAGE_COMPLETE,
            text_delta=text_delta,
            usage=usage,
            finish_reason=choice.finish_reason,
        )

        
    async def _stream_response(
        self, 
        client: AsyncOpenAI,
        kwargs: dict[str, Any]
    ) -> AsyncGenerator[StreamEvent, None]:

        usage: TokenUsage | None = None
        finish_reason: str | None = None
        
        chunks = await client.chat.completions.create(**kwargs)
        async for chunk in chunks:
            if hasattr(chunk, "usage") and chunk.usage:
                usage = TokenUsage(
                    prompt_tokens=chunk.usage.prompt_tokens,
                    completion_tokens=chunk.usage.completion_tokens,
                    total_tokens=chunk.usage.total_tokens,
                    cached_tokens=chunk.usage.prompt_tokens_details.cached_tokens,
                )
                
                finish_reason = chunk.choices[0].finish_reason
                
            if not chunk.choices:
                continue
            
            delta = chunk.choices[0].delta
            
            text_delta: TextDelta | None = None 
            if delta.content:
                text_delta = TextDelta(content=delta.content)
            
            yield StreamEvent(
                type=StreamEventType.TEXT_DELTA,
                text_delta=text_delta,
            )
            
        yield StreamEvent(
            type=StreamEventType.MESSAGE_COMPLETE,
            finish_reason=finish_reason,
            usage=usage
        )
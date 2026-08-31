import os
from collections.abc import AsyncGenerator
from typing import Any

from dotenv import load_dotenv
from openai import AsyncOpenAI

from client.response import EventType, StreamEvent, TextDelta, TokenUsage

load_dotenv()

class LLMClient:
    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None
        self.api_key: str = os.getenv('OPENROUTER_API_KEY')


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
        
        if stream:
            self._stream_response()
        else:
            yield self._get_response(client=client, kwargs=kwargs)
        
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
            type=EventType.MESSAGE_COMPLETE,
            text_delta=text_delta,
            usage=usage,
            finish_reason=choice.finish_reason,
        )

        
    async def _stream_response(self):
        pass

    
    
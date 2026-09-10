import asyncio
import os
from collections.abc import AsyncGenerator
from typing import Any

from dotenv import load_dotenv
from openai import APIConnectionError, APIError, AsyncOpenAI, RateLimitError

from client.response import (
    StreamEvent,
    StreamEventType,
    TextDelta,
    TokenUsage,
    parse_tool_call_arguments,
)

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
    
    def _build_tools(self, tools: list[dict[str, Any]]) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                    "parameters": tool.get(
                        "parameters",
                        {
                            "type": "object",
                            "properties": {}
                        }
                    )
                }
            }
            for tool in tools
        ]
    
    async def chat_completion(
        self, 
        messages: list[dict[str, Any]],
        tools: dict[str, Any],
        stream: bool = True
    ) -> AsyncGenerator[StreamEvent, None]: 
        client = await self.get_client()
        
        kwargs = {
            "model": "inclusionai/ling-3.0-flash-fin:free",
            "stream": stream,
            "messages": messages,
        }
        
        if tools:
            kwargs["tools"] = self._build_tools(tools)
            kwargs["tool_choice"] = "auto"
            
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
        tool_calls: dict[int, dict[str, Any]] = {}
    
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
            
            if delta.tool_calls:
                for tool_call in delta.tool_calls:
                    idx = tool_call.index
                    if idx not in tool_calls:
                        tool_calls[idx] = {
                            "id": tool_call.id,
                            "name": tool_call.function.name if tool_call.function else "",
                            "arguments": "",
                        }
                        yield StreamEvent.start_tool_call(
                            tool_call_id=tool_calls[idx]["id"],
                            tool_call_name=tool_calls[idx]["name"]
                        )
                    else:
                        if tool_call.function and tool_call.function.name:
                            tool_calls[idx]["name"] = tool_call.function.name
                        
                        if tool_call.function and tool_call.function.arguments:
                            tool_calls[idx]["arguments"] += tool_call.function.arguments
                            yield StreamEvent.tool_call_delta(
                                tool_call_id=tool_calls[idx]["id"],
                                tool_call_name=tool_calls[idx]["name"],
                                arguments_delta=tool_call.function.arguments
                            )
        
        for idx, tc in tool_calls.items():
            parsed_arguments = parse_tool_call_arguments(tc["arguments"])
                        
            yield StreamEvent.tool_call_complete(
                tool_call_id=tc["id"],
                tool_call_name=tc["name"],
                arguments=parsed_arguments
            )
            
        yield StreamEvent(
            type=StreamEventType.MESSAGE_COMPLETE,
            finish_reason=finish_reason,
            usage=usage
        )
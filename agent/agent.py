from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Self

from agent.events import AgentEvent, AgentEventType
from client.llm_client import LLMClient
from client.response import StreamEventType


class Agent:
    def __init__(self):
        self.client = LLMClient()
        
    async def run(self, message: str):
        final_response = ""
        yield AgentEvent.agent_start(message=message)
        
        async for event in self._agent_loop(messages=[{"role": "user", "content": message}]):
            if event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content", "")
            yield event

        yield AgentEvent.agent_end(response=final_response)

    async def _agent_loop(self, messages) -> AsyncGenerator[AgentEvent, None]:
        full_response = ""
        async for event in self.client.chat_completion(messages=messages):
            if event.type == StreamEventType.TEXT_DELTA and event.text_delta:
                content = event.text_delta.content
                full_response += content
                yield AgentEvent.text_delta(content=content)
            elif event.type == StreamEventType.ERROR:
                yield AgentEvent.agent_error(
                    error=event.error or "Unknown error occurred.",
                    details={}
                )
                
        if full_response:
            yield AgentEvent.text_complete(content=full_response)
                
    async def __aenter__(self) -> Self:
        return self
    
    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.client:
            await self.client.close()
            self.client = None
    
from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from agent.events import AgentEvent
from client.llm_client import LLMClient
from client.response import StreamEventType


class Agent:
    def __init__(self):
        self.client = LLMClient()
        
    async def run_agent(self, messages: dict[str, Any]):
        async for event in self._agent_loop(messages=messages):
            yield event
    
    async def _agent_loop(self, messages) -> AsyncGenerator[AgentEvent, None]:
        async for event in self.client.chat_completion(messages=messages):
            if event.type == StreamEventType.TEXT_DELTA and event.text_delta:
                yield AgentEvent.text_delta(content=event.text_delta.content)
            elif event.type == StreamEventType.ERROR:
                yield AgentEvent.agent_error(error=event.error)
                
                
    async def __aenter__(self) -> Agent:
        return self
    
    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.client:
            await self.client.close()
            self.client = None
    
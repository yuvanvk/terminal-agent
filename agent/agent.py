from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Self

from agent.events import AgentEvent, AgentEventType
from client.llm_client import LLMClient
from client.response import StreamEventType, ToolCall, ToolCallMessage
from context.context_manager import ContextManager
from tools.registry import create_default_registry


class Agent:
    def __init__(self):
        self.client = LLMClient()
        self._context_manager = ContextManager()
        self._tool_registry = create_default_registry()

    async def run(self, message: str):
        final_response = ""
        yield AgentEvent.agent_start(message=message)
        self._context_manager.add_user_message(content=message)

        async for event in self._agent_loop():
            if event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content", "")

            yield event

        yield AgentEvent.agent_end(response=final_response)

    async def _agent_loop(self) -> AsyncGenerator[AgentEvent, None]:
        full_response = ""
        tool_calls: list[ToolCall] = []
        
        async for event in self.client.chat_completion(
            messages=self._context_manager.get_messages(),
            tools=self._tool_registry.get_schemas(),
        ):
            if event.type == StreamEventType.TEXT_DELTA and event.text_delta:
                content = event.text_delta.content
                full_response += content
                yield AgentEvent.text_delta(content=content)
            elif event.type == StreamEventType.ERROR:
                yield AgentEvent.agent_error(
                    error=event.error or "Unknown error occurred.", details={}
                )
            # Execute the tool call
            elif event.type == StreamEventType.TOOL_CALL_COMPLETE:
                if event.tool_call:
                    tool_calls.append(event.tool_call)

        if full_response:
            self._context_manager.add_assistant_message(content=full_response)
            yield AgentEvent.text_complete(content=full_response)
        
        tool_calls_results: list[ToolCallMessage] = []
        if tool_calls:
            for tool_call in tool_calls:
                yield AgentEvent.tool_call_start(
                    name=tool_call.name,
                    tool_call_id=tool_call.id,
                    arguments=tool_call.arguments
                )
                
                # execute the tool_call
                result = await self._tool_registry.invoke(
                    tool_call.name, 
                    params=tool_call.arguments, 
                    cwd=Path.cwd()
                )
                
                yield AgentEvent.tool_call_complete(
                    tool_call_id=tool_call.id,
                    name=tool_call.name,
                    result=result
                )

                tool_calls_results.append(
                    ToolCallMessage(
                        tool_call_id=tool_call.id,
                        content=result.to_model_output(),
                        is_error=not result.success
                    )
                )
        
        for tool_call_result in tool_calls_results:
            self._context_manager.add_tool_message(
                tool_call_id=tool_call_result.tool_call_id, 
                content=tool_call_result.content
            )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self, 
        exc_type, 
        exc, 
        tb
    ) -> None:
        if self.client:
            await self.client.close()
            self.client = None
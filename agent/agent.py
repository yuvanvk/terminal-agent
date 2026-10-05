from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Self

from agent.events import AgentEvent, AgentEventType
from agent.session import Session
from client.llm_client import LLMClient
from client.response import StreamEventType, ToolCall, ToolCallMessage
from config.config import Config
from context.context_manager import ContextManager
from tools.registry import create_default_registry


class Agent:
    def __init__(self, config: Config):
        self.config = config
        self.session = Session(config=config)

    async def run(self, message: str):
        final_response = ""
        yield AgentEvent.agent_start(message=message)
        self.session._context_manager.add_user_message(content=message)

        async for event in self._agent_loop():
            if event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content", "")

            yield event

        yield AgentEvent.agent_end(response=final_response)

    async def _agent_loop(self) -> AsyncGenerator[AgentEvent, None]:
        max_turns = self.config.max_turns
        
        for _ in range(max_turns):
            self.session.increment_turn_count()
            full_response = ""
            tool_calls: list[ToolCall] = []
            
            async for event in self.session.client.chat_completion(
                messages=self.session._context_manager.get_messages(),
                tools=self.session._tool_registry.get_schemas(),
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
                self.session._context_manager.add_assistant_message(
                    content=full_response or None,
                    tool_calls=[
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": tc.arguments
                            }
                        }
                        for tc in tool_calls
                    ]
                    if tool_calls else None
                )
                yield AgentEvent.text_complete(content=full_response)
        
            if not tool_calls:
                return
            tool_calls_results: list[ToolCallMessage] = []
            
            if tool_calls:
                for tool_call in tool_calls:
                    yield AgentEvent.tool_call_start(
                        name=tool_call.name,
                        tool_call_id=tool_call.id,
                        arguments=tool_call.arguments
                    )
                    
                    # execute the tool_call
                    result = await self.session._tool_registry.invoke(
                        tool_call.name, 
                        params=tool_call.arguments, 
                        cwd=self.config.cwd
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
                self.session._context_manager.add_tool_message(
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
        if self.session and self.session.client:
            await self.session.client.close()
            self.session = None
from __future__ import annotations

import json
from collections.abc import AsyncGenerator, Callable
from typing import Self

from agent.events import AgentEvent, AgentEventType
from agent.session import Session
from client.response import StreamEventType, ToolCall, ToolCallMessage
from config.config import Config
from prompts.system import create_loop_breaker_prompt
from tools.base import ToolConfirmation


class Agent:
    def __init__(
        self, 
        config: Config, 
        confirmation_cb: Callable[[ToolConfirmation], bool] | None = None
    ):
        self.config = config
        self.session = Session(config=config)
        self.session.approval_manager.confirmation_cb = confirmation_cb

    async def run(self, message: str):
        await self.session.hook_system.trigger_before_agent(user_message=message)
        final_response = ""
        yield AgentEvent.agent_start(message=message)
        self.session._context_manager.add_user_message(content=message)

        async for event in self._agent_loop():
            if event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content", "")

            yield event
        await self.session.hook_system.trigger_after_agent(user_message=message, agent_response=final_response)
        yield AgentEvent.agent_end(response=final_response)

    async def _agent_loop(self) -> AsyncGenerator[AgentEvent, None]:
        max_turns = self.config.max_turns
        
        for _ in range(max_turns):
            self.session.increment_turn_count()
            full_response = ""
            tool_calls: list[ToolCall] = []
            
            if self.session._context_manager.needs_compression():
                summary, usage = await self.session.chat_compactor.compress(
                    context_manager=self.session._context_manager
                )
                
                if summary:
                    self.session._context_manager.replace_with_summary(summary=summary)
                    self.session._context_manager.set_latest_usage(usage=usage)
                    self.session._context_manager.add_usage(usage=usage)
            
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
                        
                elif event.type == StreamEventType.MESSAGE_COMPLETE:
                    usage = event.usage

            if full_response or tool_calls:
                self.session._context_manager.add_assistant_message(
                    content=full_response,
                    tool_calls=[
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments)
                            }
                        }
                        for tc in tool_calls
                    ]
                    if tool_calls else None
                )
            if full_response:
                yield AgentEvent.text_complete(content=full_response)
                self.session.loop_detector.record_action(action_type='response', text=full_response)
        
            if not tool_calls:
                if usage:
                    self.session._context_manager.set_latest_usage(usage=usage)
                    self.session._context_manager.add_usage(usage=usage)
                
                self.session._context_manager.prune_tool_outputs()
                return
            
            tool_calls_results: list[ToolCallMessage] = []
            
            if tool_calls:
                for tool_call in tool_calls:
                    yield AgentEvent.tool_call_start(
                        name=tool_call.name,
                        tool_call_id=tool_call.id,
                        arguments=tool_call.arguments
                    )
                    self.session.loop_detector.record_action(
                        action_type='tool_call', 
                        tool_call=tool_call.name, 
                        args=tool_call.arguments
                    )

                    
                    # execute the tool_call
                    result = await self.session._tool_registry.invoke(
                        tool_call.name, 
                        params=tool_call.arguments, 
                        cwd=self.config.cwd,
                        hook_system=self.session.hook_system,
                        approval_manager=self.session.approval_manager,
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
            
            loop = self.session.loop_detector.check_for_loop()
            if loop:
                steer_prompt = create_loop_breaker_prompt(loop_description=loop)
                self.session._context_manager.add_user_message(steer_prompt)
                continue
            
            if usage:
                self.session._context_manager.set_latest_usage(usage=usage)
                self.session._context_manager.add_usage(usage=usage)
            
            self.session._context_manager.prune_tool_outputs()
        yield AgentEvent.agent_error(f"Maxiumum turns ({max_turns})")

    async def __aenter__(self) -> Self:
        await self.session.initialise()
        return self

    async def __aexit__(
        self, 
        exc_type, 
        exc, 
        tb
    ) -> None:
        if self.session and self.session.client and self.session.mcp_manager:
            await self.session.client.close()
            await self.session.mcp_manager.shutdown()
            self.session = None
            
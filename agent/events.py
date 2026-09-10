from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from client.response import TokenUsage
from tools.base import ToolResult


class AgentEventType(str, Enum):
    """Agent Lifecycle Events"""
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    AGENT_ERROR = "agent_error"
    
    """Tool call events"""
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_COMPLETE = "tool_call_complete"
    
    """Textual Events"""
    TEXT_DELTA = "text_delta"
    TEXT_COMPLETE = "text_complete"
            
@dataclass
class AgentEvent:
    type: AgentEventType
    data: dict[str, Any]
    
    @classmethod
    def agent_start(cls, message: str) -> AgentEvent:
        return cls(
            type=AgentEventType.AGENT_START,
            data={"message": message}        
        )
    
    @classmethod
    def agent_end(cls, response: str, usage: TokenUsage | None = None) -> AgentEvent:
        return cls(
            type=AgentEventType.AGENT_END,
            data={"response": response, "usage": usage.__dict__ if usage else None }
        )
        
    @classmethod
    def agent_error(cls, error: str, details: dict[str, Any]) -> AgentEvent:
        return cls(
            type=AgentEventType.AGENT_ERROR,
            data={ "error": error, "details": details or {} }
        )
    
    @classmethod
    def text_delta(cls, content: str) -> AgentEvent:
        return cls(
            type=AgentEventType.TEXT_DELTA,
            data={ "content": content }
        )

    @classmethod
    def text_complete(cls, content: str) -> AgentEvent:
        return cls(
            type=AgentEventType.TEXT_COMPLETE,
            data={"content": content}
        )
        
    @classmethod
    def tool_call_start(
        cls,
        tool_call_id: str,
        name: str,
        arguments: dict[str, Any]
    ):
        return cls(
            type=AgentEventType.TOOL_CALL_START,
            data={
                "tool_call_id": tool_call_id,
                "name": name,
                "agruments": arguments
            }
        )
        
    @classmethod
    def tool_call_complete(
        cls,
        tool_call_id: str,
        name: str,
        result: ToolResult
    ): 
        return cls(
            type=AgentEventType.TOOL_CALL_COMPLETE,
            data={
                "tool_call_id": tool_call_id,
                "name": name,
                "success": result.success,
                "output": result.output,
                "error": result.error,
                "metadata": result.metadata,
                "truncated": result.truncated
            }
        )
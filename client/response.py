from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from json import JSONDecodeError, loads
from typing import Any


class StreamEventType(str, Enum):
    TEXT_DELTA = "text_delta"
    MESSAGE_COMPLETE = "message_complete"
    ERROR = "error"
    
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_DELTA = "tool_call_delta"
    TOOL_CALL_COMPLETE = "tool_call_complete"

@dataclass
class TextDelta:
    content: str
    
    def __str__(self):
        return self.content
    
@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    total_tokens: int = 0
    
    def __add__(self, other: TokenUsage):
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            cached_tokens=self.cached_tokens + other.cached_tokens,
            total_tokens=self.total_tokens + other.total_tokens
        )
@dataclass
class ToolCallDelta:
    id: str
    name: str = ""
    arguments_delta: str = ""

@dataclass
class ToolCall:
    id: str
    name: str = ""
    arguments: str = ""    
    
@dataclass
class ToolCallMessage:
    tool_call_id: str
    content: str
    
    is_error: bool = False
    
    

@dataclass
class StreamEvent:
    type: StreamEventType
    text_delta: TextDelta | None = None
    
    tool_call_delta: ToolCallDelta | None = None
    tool_call: ToolCall | None = None
    
    usage: TokenUsage | None = None
    finish_reason: str | None = None
    error: str | None = None
    
    @classmethod
    def start_tool_call(
        cls,
        tool_call_id: str,
        tool_call_name: str,
    ):
        return cls(
            type=StreamEventType.TOOL_CALL_START,
            tool_call_delta=ToolCallDelta(
                id=tool_call_id,
                name=tool_call_name
            )
        )
    
    @classmethod
    def tool_call_delta(
        cls,
        tool_call_id: str,
        tool_call_name: str,
        arguments_delta: str
    ):
        return cls(
            type=StreamEventType.TOOL_CALL_DELTA,
            tool_call_delta=ToolCallDelta(
                id=tool_call_id,
                name=tool_call_name,
                arguments_delta=arguments_delta
            )
        )
        
    @classmethod
    def tool_call_complete(
        cls,
        tool_call_id: str,
        tool_call_name: str,
        arguments: str
    ):
        return cls(
            type=StreamEventType.TOOL_CALL_COMPLETE,
            tool_call=ToolCall(
                id=tool_call_id,
                name=tool_call_name,
                arguments=arguments
            )
        )
        
        
def parse_tool_call_arguments(arugments: str) -> dict[str, Any]:
    if not arugments:
        return {}
    
    try:
        parsed_arugments = loads(arugments)
        return parsed_arugments
    except JSONDecodeError:
        return { "raw_argments": arugments }
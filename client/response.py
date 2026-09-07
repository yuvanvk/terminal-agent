from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


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
    pass  

@dataclass
class StreamEvent:
    type: StreamEventType
    text_delta: TextDelta | None = None
    tool_call_delta: ToolCallDelta | None = None
    
    usage: TokenUsage | None = None
    finish_reason: str | None = None
    error: str | None = None
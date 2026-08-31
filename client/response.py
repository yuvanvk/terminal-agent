from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EventType(str, Enum):
    TEXT_DELTA = "text_delta"
    MESSAGE_COMPLETE = "message_complete"

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
class StreamEvent:
    type: EventType
    text_delta: TextDelta | None = None
    usage: TokenUsage | None = None
    finish_reason: str | None = None
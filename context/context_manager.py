from dataclasses import dataclass, field
from typing import Any

from prompts.system import get_system_prompt
from utils.token import count_tokens


@dataclass
class Message:
    role: str
    content: str
    token_count: int
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = { "role": self.role }
        
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
            
        if self.tool_calls:
            result["tools_calls"] = self.tool_calls
        
        if self.content:
            result["content"] = self.content
            
        return result
            
        
class ContextManager:
    def __init__(self):
        self._system_prompt = get_system_prompt()
        self._model = "inclusionai/ling-3.0-flash-fin:free"
        self._messages: list[Message]= []
        
    def add_user_message(self, content: str) -> None:
        message = Message(
            role="user",
            content=content,
            token_count=count_tokens(content, self._model)
        )
            
        self._messages.append(message)
        
    def add_assistant_message(self, content: str) -> None:
        message = Message(
            role="assistant",
            content=content or "",
            token_count=count_tokens(content or "", self._model)
        )
            
        self._messages.append(message)
        
    def add_tool_message(self, tool_call_id: str, content: str) -> None:
        message = Message(
            role="tool",
            content=content,
            tool_call_id=tool_call_id,
            token_count=count_tokens(content, self._model)
        )
            
        self._messages.append(message)
            
    def get_messages(self) -> list[dict[str, Any]]:
        messages = []

        if self._system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": self._system_prompt
                }
            )
            
        if self._messages:
            for message in self._messages:
                messages.append(message.to_dict())
            
        return messages
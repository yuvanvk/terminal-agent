from dataclasses import dataclass
from typing import Any

from prompts.system import get_system_prompt
from utils.token import count_tokens


@dataclass
class Message:
    role: str
    content: str
    token_count: int

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = { "role": self.role }
        
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
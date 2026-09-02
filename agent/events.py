from dataclasses import dataclass
from enum import Enum


class AgentEventType(str, Enum):
    """Agent Lifecycle Events"""
    
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    AGENT_ERROR = "agent_error"
    
    """Textual Events"""
    TEXT_DELTA = "text_delta"
    TEXT_COMPLETE = "text_complete"
            
@dataclass
class AgentEvent:
    type: AgentEventType
    
    @classmethod
    def agent_start(cls):
        return cls(
            type=AgentEventType.AGENT_START
        )
    
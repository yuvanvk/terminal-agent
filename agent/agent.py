from collections.abc import AsyncGenerator

from agent.events import AgentEvent


class Agent:
    def __init__(self):
        pass
    
    def _agent_loop(self) -> AsyncGenerator[AgentEvent, None]:
        pass
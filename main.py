import asyncio
import sys

import click

from agent.agent import Agent
from agent.events import AgentEventType
from tui.tui import TUI, get_console


class CLI:
    def __init__(self):
        self.agent: Agent | None = None
        self.tui = TUI(console=get_console())
    
    async def run_single(self, message: str) -> str | None:
        async with Agent() as agent:
            self.agent = agent
            return await self._process_message(message)
        
    async def _process_message(self, message: str) -> str | None:
        if not self.agent:
            return None
        
        self.agent_streaming = False
        final_response: str | None = None

        async for event in self.agent.run(message=message):
            if event.type == AgentEventType.TEXT_DELTA:
                if self.agent_streaming is False:
                    self.agent_streaming = True
                    self.tui.begin_agent()
                content = event.data.get("content", "")
                self.tui.stream_agent_response(message=content)
            elif event.type == AgentEventType.TEXT_COMPLETE:
                if self.agent_streaming:
                    self.tui.end_agent()
                
                final_response = event.data.get("content")
            elif event.type == AgentEventType.AGENT_ERROR:
                message = event.data.get("error")
                details = event.data.get("details")
                
                self.tui.log_error(message=message, details=details or {})
        
        return final_response
        

@click.command()
@click.argument("prompt")
def main(
    prompt: str
):
    cli = CLI()
    result = asyncio.run(cli.run_single(message=prompt))
    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    main()

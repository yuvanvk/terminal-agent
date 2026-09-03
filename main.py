import asyncio

import click

from agent.agent import Agent
from agent.events import AgentEventType


class CLI:
    def __init__(self):
        self.agent: Agent | None = None
    
    async def run_single(self, prompt: str):

        async for event in self.agent.run_agent(messages={"role": "user", "content": prompt }):
            if event.type == AgentEventType.TEXT_DELTA:
                self._process_message(event.data["content"])
        
    def _process_message(self):
        pass


@click.command()
@click.argument("prompt")
def main(
    prompt: str
):
    cli = CLI()
    asyncio.run(cli.run_single(prompt=prompt))

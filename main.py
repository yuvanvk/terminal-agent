import asyncio
import sys
from pathlib import Path

import click

from agent.agent import Agent
from agent.events import AgentEventType
from config.config import Config
from config.loader import load_config
from tui.tui import TUI, get_console

console = get_console()

class CLI:
    def __init__(self, config: Config):
        self.config = config
        self.agent: Agent | None = None
        self.tui = TUI(console=get_console())
    
    async def run_single(self, message: str) -> str | None:
        async with Agent(config=self.config) as agent:
            self.agent = agent
            return await self._process_message(message)
        
    async def run_interactive_mode(self) -> str | None:
        self.tui.print_welcome(
            "AI Agent",
            lines=[
                f"model: {self.config.model_name}",
                f"cwd: {self.config.cwd}",
                "commands: /help /config /approval /model /exit",
            ],
        )
        
        async with Agent(config=self.config) as agent:
            self.agent = agent
            while True:
                try:
                    user_input = console.input("\n[user]>[/user] ").strip()
                    if not user_input:
                        continue
                    
                    await self._process_message(user_input)
                except KeyboardInterrupt:
                    console.print("\n[dim]Use /exit to quit[/dim]")
                except EOFError:
                    break
        
        console.print("\n[dim]Goodbye![/dim]")
        
    def _get_tool_kind(self, tool_call_name: str) -> str:
        tool_kind = None
        tool = self.agent._tool_registry.get(tool_call_name)
        if not tool:
            tool_kind = None

        tool_kind = tool.kind.value

        return tool_kind
        
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
            elif event.type == AgentEventType.TOOL_CALL_START:
                tool_name = event.data.get("name", "unknown")
                
                
                self.tui.tool_call_start(
                    tool_call_id=event.data.get("tool_call_id"),
                    tool_call_name=tool_name,
                    tool_kind=self._get_tool_kind(tool_name),
                    args=event.data.get("arguments", {})
                )
            elif event.type == AgentEventType.TOOL_CALL_COMPLETE:
                tool_name = event.data.get("name", "unknown")
                self.tui.tool_call_complete(
                    tool_call_id=event.data.get("tool_call_id"),
                    tool_call_name=tool_name,
                    tool_kind=self._get_tool_kind(tool_name),
                    success=event.data.get("success", False),
                    output=event.data.get("output", ""),
                    metadata=event.data.get("metadata"),
                    error=event.data.get("error"),
                    truncated=event.data.get("truncated", False)
                )
        
        return final_response
        

@click.command()
@click.argument("prompt", required=False)
@click.option(
    "--cwd",
    "-c",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Working directory for the agent.",
)
def main(
    prompt: str | None,
    cwd: Path | None
):

    try:
        config = load_config(cwd)
    except Exception as e:
        console.print(f"[error]Configuration Error: {e}[/error]")
        sys.exit(1)
        
    errors = config.validate()
    if errors:
        for error in errors:
            console.print(f"[error]Config validation error: {error}[/error]")
            
        sys.exit(1)
        
    cli = CLI(config)
    
    if prompt:
        result = asyncio.run(cli.run_single(prompt))
        if result is None:
            sys.exit(1)
    else:
        asyncio.run(cli.run_interactive_mode())


if __name__ == "__main__":
    main()

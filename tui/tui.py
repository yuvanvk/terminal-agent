from typing import Any

from rich.console import Console
from rich.rule import Rule
from rich.text import Text

from tui.agent_theme import AGENT_THEME

_console: Console | None = None

def get_console():
    global _console
    if not _console:
        _console = Console(theme=AGENT_THEME)
    
    return _console

class TUI:
    def __init__(self, console: Console):
        self.console = console or get_console()
        self.agent_is_streaming = False
            
    def begin_agent(self) -> None:
        self.agent_is_streaming = True
        self.console.print()
        self.console.print(Rule(Text("Agent", style="assistant")))
    
    
    def end_agent(self) -> None:
        self.console.print()
        if self.agent_is_streaming:
            self.agent_is_streaming = False
        
    def stream_agent_response(self, message: str) -> None:
        self.console.print(message, end="", markup=False, style="assistant")
        
    def log_error(self, message: str, details: dict[str, Any]):
        self.console.print(message, style="error")
from pathlib import Path
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
        self._tool_args_by_call_id: dict[int, dict[str, Any]] = {}
            
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
        
    def tool_call_start(
        self, 
        tool_call_id: str,
        tool_call_name: str,
        tool_kind: str,
        arguments: dict[str, Any]
    ):
        self._tool_args_by_call_id[tool_call_id] = arguments
        
        title = Text.assemble(
            ("⏺ ", "muted"),
            (tool_call_name, "tool"),
            ("  ", "muted"),
            (f"#{tool_call_id[:8]}", "muted"),
        )
        
    
    def _render_args_table(args: dict[str, Any]):
        pass
    
    def _guess_language(self, path: str | None) -> str:
        if not path:
            return "text"
        suffix = Path(path).suffix.lower()
        return {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "jsx",
            ".ts": "typescript",
            ".tsx": "tsx",
            ".json": "json",
            ".toml": "toml",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".md": "markdown",
            ".sh": "bash",
            ".bash": "bash",
            ".zsh": "bash",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".kt": "kotlin",
            ".swift": "swift",
            ".c": "c",
            ".h": "c",
            ".cpp": "cpp",
            ".hpp": "cpp",
            ".css": "css",
            ".html": "html",
            ".xml": "xml",
            ".sql": "sql",
        }.get(suffix, "text")
        
    def _extract_read_file_code(context: str) -> str:
        pass

        
        
    def log_error(self, message: str, details: dict[str, Any]):
        self.console.print(message, style="error")
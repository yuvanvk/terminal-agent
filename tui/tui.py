import re
from pathlib import Path
from typing import Any

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from tui.agent_theme import AGENT_THEME
from utils.path import get_relative_path_to_cwd
from utils.token import truncate_text

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
        self.cwd = Path.cwd()
        self._tool_args_by_call_id: dict[str, dict[str, Any]] = {}

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

    def _ordered_arguments(self, tool_call_name: str, args: dict[str, Any]):
        _PREFFERED_ORDER = {
            "read_file": ["path", "offset", "limit"],
        }

        ordered: list[tuple[str, Any]] = []
        preffered = _PREFFERED_ORDER.get(tool_call_name, [])
        seen = set()

        for key in preffered:
            if key in args:
                ordered.append((key, args[key]))
                seen.add(key)

        remaining = set(args.keys() - seen)
        ordered.extend((key, args[key]) for key in remaining)

        return ordered

    def _render_args_table(self, tool_call_name: str, args: dict[str, Any]):
        table = Table.grid(padding=(0, 1))
        table.add_column(style="muted", justify="right", no_wrap=True)
        table.add_column(style="muted", overflow="fold")

        for key, value in self._ordered_arguments(
            tool_call_name=tool_call_name, args=args
        ):
            table.add_row(key, value)

        return table

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

    def _extract_read_file_code(self, text: str) -> tuple[int, str] | None:
        body = text
        header = re.match(r"^Showing lines (\d+)-(\d+) of (\d+)\n\n", text)

        if header:
            body = text[header.end(): ]
        
        code_lines: list[str] = []
        start_line_no: int | None = None
        
        for line in body.splitlines():
            m = re.match(r"^\s*(\d+)\|(.*)$", line)
            if m is None:
                return None
            
            line_no = m.group(1)
            code_line = m.group(2)
            
            if start_line_no is None:
                start_line_no = line_no
            
            code_lines.append(code_line)
            
        if start_line_no is None:
            return None
        
        return start_line_no, "\n".join(code_lines)

    def tool_call_start(
        self,
        tool_call_id: str,
        tool_call_name: str,
        tool_kind: str | None,
        args: dict[str, Any],
    ):
        self._tool_args_by_call_id[tool_call_id] = args
        border_style = f"tool.{tool_kind}" if tool_kind else "tool"

        title = Text.assemble(
            ("⏺ ", "muted"),
            (tool_call_name, "tool"),
            ("  ", "muted"),
            (f"#{tool_call_id[:8]}", "muted"),
        )

        display_args = dict(args)

        for key in ("path", "cwd"):
            value = display_args.get(key)
            if isinstance(value, str) and self.cwd:
                display_args[key] = get_relative_path_to_cwd(path=value, cwd=self.cwd)

        panel = Panel(
            renderable=self._render_args_table(
                tool_call_name=tool_call_name, args=display_args
            )
            if display_args
            else Text("(no args provided)", style="muted"),
            title=title,
            title_align="left",
            subtitle=Text("running", style="muted"),
            subtitle_align="right",
            padding=(1, 2),
            box=box.ROUNDED,
            border_style=border_style,
        )

        self.console.print(panel)
        
    def tool_call_complete(
        self,
        tool_call_id: str,
        tool_call_name: str,
        tool_kind: str | None,
        success: bool,
        output: str,
        error: str | None,
        metadata: dict[str, Any],
        truncated: bool
    ):
        border_style = f"tool.{tool_kind}" if tool_kind else "tool"
        status_icon = "✔" if success else "✖"
        status_style = "success" if success else "error"
          
        title = Text.assemble(
            (status_icon, status_style),
            (tool_call_name, "tool"),
            ("  ", "muted"),
            (f"#{tool_call_id[:8]}", "muted"),
        )
        
        blocks = []
        primary_path: str | None = None
        if isinstance(metadata, dict) and hasattr(metadata, "path"):
            primary_path = metadata.get("path")
        
        if tool_call_name == "read_file" and success:
            if primary_path:
                start_line_no, code = self._extract_read_file_code(output)
                
                start_from = metadata.get("start_from")
                end_from = metadata.get("end_from")
                total_lines = metadata.get("total_lines")
                
                pl = self._guess_language(primary_path)
                
                header_parts = [get_relative_path_to_cwd(primary_path, self.cwd)]
                header_parts.append(" 🔹 ")
                
                if start_from and end_from and total_lines:
                    header_parts.append(f"lines from ${start_from}-{end_from} of {total_lines}")
                
                header = "".join(header_parts)
                blocks.append(header)
                blocks.append(Syntax(
                    code,
                    lexer=pl,
                    theme="monokai",
                    start_line=start_line_no,
                    word_wrap=False
                ))
            else:
                output_display = truncate_text(output, "", 240)
                blocks.append(
                    Syntax(
                        code=output_display,
                        lexer="text",
                        theme="monokai",
                        word_wrap=False
                    )
                )
                
        if truncated:
            blocks.append(
                Text("note: tool output was trucated", style="warning")
            )

        panel = Panel(
            Group(
                *blocks
            ),
            title=title,
            title_align="left",
            subtitle=Text("Done" if success else "Failed", style=status_style),
            subtitle_align="right",
            padding=(1, 2),
            box=box.ROUNDED,
            border_style=border_style,
        )
        
        self.console.print(panel)
    
    
    def log_error(self, message: str, details: dict[str, Any]):
        self.console.print(message, style="error")

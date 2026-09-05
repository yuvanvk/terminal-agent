from rich.theme import Theme

AGENT_THEME = Theme(
    {
        # General
        "info": "cyan",
        "warning": "yellow",
        "error": "bright_red bold",
        "success": "green",
        "dim": "dim",
        "muted": "grey50",
        "border": "grey35",
        "highlight": "bold cyan",

        # Roles
        "user": "bright_blue bold",
        "assistant": "bright_white",
        "system": "grey62 italic",

        # Tools — general + per-category
        "tool": "bright_magenta bold",
        "tool.read": "cyan",
        "tool.write": "yellow",
        "tool.shell": "magenta",
        "tool.network": "bright_blue",
        "tool.memory": "green",
        "tool.mcp": "bright_cyan",
        "tool.search": "blue",
        "tool.name": "bold white",
        "tool.arg": "grey70",
        "tool.pending": "yellow dim",
        "tool.running": "yellow",
        "tool.success": "green",
        "tool.error": "bright_red bold",

        # Diffs (file edits)
        "diff.add": "green",
        "diff.remove": "bright_red",
        "diff.header": "cyan bold",
        "diff.range": "grey50",

        # Code / blocks
        "code": "white",
        "code.border": "grey35",
        "code.lang": "grey50 italic",
        "code.lineno": "grey42",

        # Filesystem
        "path": "cyan underline",
        "path.dir": "bright_blue",

        # Status / progress
        "status.thinking": "grey62 italic",
        "status.working": "yellow",
        "status.done": "green bold",
        "status.blocked": "bright_red",

        # Prompts / input
        "prompt": "bright_blue bold",
        "prompt.cursor": "bright_white on grey35",

        # Misc
        "badge": "black on cyan",
        "link": "bright_blue underline",
        "token_count": "grey50 dim",
    }
)
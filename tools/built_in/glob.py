import os
import re
from pathlib import Path

from pydantic import BaseModel, Field

from tools.base import Tool, ToolInvocation, ToolKind, ToolResult
from utils.path import is_binary_path, resolve_path


class GlobParams(BaseModel):
    pattern: str = Field(..., description="Glob pattern to match")
    path: str = Field(
        ".", description="Directory to search in (default: current directory)"
    )


class GlobTool(Tool):
    name = "glob"
    description = "Find files matching a glob pattern. Supports ** recursive matching."
    kind = ToolKind.READ

    schema = GlobParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = GlobParams(**invocation.params)

        search_path = resolve_path(invocation.cwd, params.path)

        if not search_path.exists() or not search_path.is_dir():
            return ToolResult.error_result(f"Directory does not exist: {search_path}")

        try:
            matches = list(search_path.glob(params.pattern))
            matches = [p for p in matches if p.is_file()]
        except Exception as e:
            return ToolResult.error_result(f"Error searching: {e}")

        output_lines = []

        for file_path in matches[:1000]:
            try:
                rel_path = file_path.relative_to(search_path)
            except Exception:
                rel_path = file_path
            
            output_lines.append(str(rel_path))
        
        if len(matches) > 1000:
            output_lines.append("... limited to first 1000 matches")
            


        return ToolResult.success_result(
            "\n".join(output_lines),
            metadata={
                "path": str(search_path),
            },
        )

    def _find_files(self, search_path: Path) -> list[Path]:
        files = []

        for root, dir, filenames in os.walk(search_path):
            dir[:] = [
                d
                for d in dir
                if d not in {".git", ".venv", "__pycache__", "node_modules", "venv"}
            ]
            for filename in filenames:
                if filename.startswith("."):
                    continue

                file_path = Path(root) / filename
                if not is_binary_path(file_path):
                    files.append(filename)
                    if len(files) >= 500:
                        break

        return files

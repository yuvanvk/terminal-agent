from pathlib import Path

from pydantic import BaseModel, Field

from tools.base import Tool, ToolInvocation, ToolKind, ToolResult
from utils.path import is_binary_path, resolve_path
from utils.token import count_tokens, truncate_text


class ReadFileParams(BaseModel):
    path: str | Path = Field(
        ..., 
        description="Path to the file to read (relative to the working directory or absolute)",
    )
    
    offset: int = Field(
        1,
        ge=1,
        description="Line number to start reading from a file (1-based). Defaults to 1"
    )
    
    limit: int | None = Field(
        None,
        ge=1,
        description="Maximum number of lines to read. If not specified, reads entire file."
    )
    
class ReadFile(Tool):
    name = "read_file"
    description = (
        "Read the contents of a text file. Returns the file content with line numbers. "
        "For large files, use offset and limit to read specific portions. "
        "Cannot read binary files (images, executables, etc.)."
    )
    kind = ToolKind.READ
    
    schema = ReadFileParams
    
    MAX_FILE_SIZE = 1024 * 1024 * 10
    MAX_TOKENS = 25000
    
    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = ReadFileParams(**invocation.params)
        
        path = resolve_path(invocation.cwd, params.path)
        
        if not path.exists():
            return ToolResult.error_result(
                error=f"File not found: {path}"
            )
        
        if not path.is_file():
            return ToolResult.error_result(
                error=f"Path is not a file: {path}"
            )
        
        file_size = path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        
        if file_size > self.MAX_FILE_SIZE:
            return ToolResult.error_result(
                error=f"File too large ({file_size_mb:.1f})MB",
                output=f"Maximum file size is {self.MAX_FILE_SIZE / (1024 * 1024):.0f}MB"
            )
        
        if is_binary_path(path):
            size_str = f"{file_size_mb:.2f}MB" if file_size_mb > 1 else f"{file_size} bytes"
            return ToolResult.error_result(
                error=f"Cannot read binary file: {path.name} ({size_str})",
                output="This tool only reads text files."
            )
        
        try:
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeError as e:
                content = path.read_text(encoding="latin-1")
                
            lines = content.splitlines()
            total_lines = len(lines)
            
            if total_lines == 0:
                return ToolResult.success_result(
                    output="File is empty.",
                    metadata={
                        "lines": total_lines
                    }
                )
            
            start_idx = max(0, params.offset - 1)
            
            if params.limit is not None:
                end_idx = min(start_idx + params.limit, total_lines)
            else:
                end_idx = total_lines
            
            selected_lines = lines[start_idx, end_idx]
            formatted_lines = []
            
            for i, line in enumerate(selected_lines, start=start_idx + 1):
                formatted_lines.append(f"{i:6}|{line}")
            
            output = "\n".join(formatted_lines)
            
            token_count = count_tokens(output)
            truncated = False
            
            if token_count > self.MAX_TOKENS:
                output = truncate_text(
                    text=output,
                    model="",
                    max_tokens=self.MAX_TOKENS,
                    suffix="\n... [truncated]",
                    preserver_lines=True
                )
            
                truncated = True
                
                metadata_lines = []
                if start_idx > 0 or end_idx < total_lines:
                    metadata_lines.append(
                        f"Showing lines {start_idx+1}-{end_idx} of {total_lines}"
                    )

                if metadata_lines:
                    header = " | ".join(metadata_lines) + "\n\n"
                    output = header + output

                return ToolResult.success_result(
                    output=output,
                    truncated=truncated,
                    metadata={
                        "path": str(path),
                        "total_lines": total_lines,
                        "shown_start": start_idx + 1,
                        "shown_end": end_idx,
                    },
                )
        except Exception as e:
            return ToolResult.error_result(f"Failed to read file: {e}")
        
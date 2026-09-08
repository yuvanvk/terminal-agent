import logging
from typing import Any

from tools.base import Tool, ToolInvocation, ToolResult

logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}
        
    def register(self, tool: Tool) -> None:
        if tool in self._tools:
            logger.warning(f"Overwriting existing tool registration: {tool.name}")
        
        self._tools[tool.name] = tool
        
    def unregister(self, tool_name: str) -> bool:
        if tool_name in self._tools:
            del self._tools[tool_name]
            return True

        return False
    
        
    def get_tools(self) -> list[Tool]:
        return list(self._tools.values())

    
    def get(self, name) -> Tool | None:
        if name in self._tools:
            return self._tools[name]
        
        return None
    
    def get_schemas(self) -> list[dict[str, Any]]:
        return [tool.to_openai_json() for tool in self.get_tools()]
            
    async def invoke(self, tool_name: str, params: dict[str, Any], cwd: str | None = None) -> ToolResult:
        tool = self.get(tool_name)
        
        if tool is None:
            return ToolResult.error_result(
                error=f"Tool '{tool_name}' not found.",
                output="Please check the tool name and try again."
            )
        
        validation_errors = tool.validate_params(params=params)
        
        if validation_errors:
            return ToolResult.error_result(
                error=f"Invalid parameters for tool {tool.name}",
                output="\n".join(validation_errors),
                metadata={
                    "validation_errors": validation_errors
                }
            )
        
        invocation = ToolInvocation(
            params=params,
            cwd=cwd
        )
        
        return await tool.execute(invocation=invocation)

def create_default_registry():
    registry = ToolRegistry()
    
    return registry
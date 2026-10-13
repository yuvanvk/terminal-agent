import logging
from pathlib import Path
from typing import Any

from config.config import Config
from tools import get_all_built_tools
from tools.base import Tool, ToolInvocation, ToolResult
from tools.sub_agent import SubAgentTool, get_default_subagent_definitions

logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self, config: Config):
        self._tools: dict[str, Tool] = {}
        self.config = config
        
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
        tools: list[Tool] = []
        
        for tool in self._tools.values():
            tools.append(tool)
        
        if self.config.allowed_tools:
            allowed_set = set(self.config.allowed_tools)
            tools = [t for t in tools if t.name in allowed_set]

        return tools
    
    def get(self, name) -> Tool | None:
        if name in self._tools:
            return self._tools[name]
        
        return None
    
    def get_schemas(self) -> list[dict[str, Any]]:
        return [tool.to_openai_json() for tool in self.get_tools()]
            
    async def invoke(self, tool_name: str, params: dict[str, Any], cwd: Path) -> ToolResult:
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

def create_default_registry(config: Config):
    registry = ToolRegistry(config=config)
    
    for tool_class in get_all_built_tools():
        registry.register(tool_class(config))
        
    for sub_agent in get_default_subagent_definitions():
        registry.register(SubAgentTool(config=config, definition=sub_agent))
        
    return registry
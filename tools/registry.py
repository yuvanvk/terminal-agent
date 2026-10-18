import logging
from pathlib import Path
from typing import Any

from config.config import Config
from hooks.hook_system import HookSystem
from safety.approval import ApprovalContext, ApprovalDecision, ApprovalManager
from tools import get_all_built_tools
from tools.base import Tool, ToolInvocation, ToolResult
from tools.sub_agent import SubAgentTool, get_default_subagent_definitions

logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self, config: Config):
        self._tools: dict[str, Tool] = {}
        self._mcp_tools: dict[str, Tool] = {}

        self.config = config

    @property
    def connected_mcp_servers(self) -> list[Tool]:
        return self._mcp_tools.values()

    def register(self, tool: Tool) -> None:
        if tool in self._tools:
            logger.warning(f"Overwriting existing tool registration: {tool.name}")

        self._tools[tool.name] = tool

    def register_mcp_tool(self, tool: Tool) -> None:
        self._mcp_tools[tool.name] = tool
        logger.debug(f"Registered MCP tool: {tool.name}")

    def unregister(self, tool_name: str) -> bool:
        if tool_name in self._tools:
            del self._tools[tool_name]
            return True

        return False

    def get_tools(self) -> list[Tool]:
        tools: list[Tool] = []

        for tool in self._tools.values():
            tools.append(tool)

        for mcp_tool in self._mcp_tools.values():
            tools.append(mcp_tool)

        if self.config.allowed_tools:
            allowed_set = set(self.config.allowed_tools)
            tools = [t for t in tools if t.name in allowed_set]

        return tools

    def get(self, name) -> Tool | None:
        if name in self._tools:
            return self._tools[name]
        elif name in self._mcp_tools:
            return self._mcp_tools[name]

        return None

    def get_schemas(self) -> list[dict[str, Any]]:
        return [tool.to_openai_json() for tool in self.get_tools()]

    async def invoke(
        self,
        tool_name: str,
        params: dict[str, Any],
        cwd: Path,
        hook_system: HookSystem,
        approval_manager: ApprovalManager | None = None,
    ) -> ToolResult:
        tool = self.get(tool_name)

        if tool is None:
            result =  ToolResult.error_result(
                error=f"Tool '{tool_name}' not found.",
                output="Please check the tool name and try again.",
            )
            
            await hook_system.trigger_after_tool(tool_name=tool_name, tool_params=params, tool_result=result)
            return result

        validation_errors = tool.validate_params(params=params)

        if validation_errors:
            result =  ToolResult.error_result(
                error=f"Invalid parameters for tool {tool.name}",
                output="\n".join(validation_errors),
                metadata={"validation_errors": validation_errors},
            )
            await hook_system.trigger_after_tool(tool_name=tool_name, tool_params=params, tool_result=result)
            return result

        await hook_system.trigger_before_tool(tool_name=tool_name, tool_params=params)
        invocation = ToolInvocation(params=params, cwd=cwd)
        if approval_manager:
            confirmation = await tool.get_confirmation(invocation=invocation)

            if confirmation:
                context = ApprovalContext(
                    tool_name=tool_name,
                    params=params,
                    is_mutating=tool.is_mutating(params=params),
                    affected_paths=confirmation.affected_paths,
                    command=confirmation.command,
                    is_dangerous=confirmation.is_dangerous,
                )

                decision = approval_manager.check_approval(context=context)
                if decision == ApprovalDecision.REJECTED:
                    result = ToolResult.error_result(
                        "Operation was rejected because of safety policy"
                    )
                    await hook_system.trigger_after_tool(tool_name=tool_name, tool_params=params, tool_result=result)
                    return result

                elif decision == ApprovalDecision.NEEDS_CONFIRMATION:
                    approved = approval_manager.request_confirmation(
                        confirmation=confirmation
                    )
                    
                    if not approved:
                        result = ToolResult.error_result(
                            "User rejected the operation"
                        )
                        await hook_system.trigger_after_tool(tool_name=tool_name, tool_params=params, tool_result=result)
                        return result
        
        try:
            result = await tool.execute(invocation=invocation)
        except Exception as e:
            logger.exception(f"Tool {tool_name} raised unexpected error")
            result = ToolResult.error_result(
                error=f"Internal error: {str(e)}",  
                metadata={
                    "tool_name": tool_name
                }
            )
        await hook_system.trigger_after_tool(tool_name=tool_name, tool_params=params, tool_result=result)
        return result

def create_default_registry(config: Config):
    registry = ToolRegistry(config=config)

    for tool_class in get_all_built_tools():
        registry.register(tool_class(config))

    for sub_agent in get_default_subagent_definitions():
        registry.register(SubAgentTool(config=config, definition=sub_agent))

    return registry

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import SSETransport, StdioTransport

from config.config import MCPServerConfig


class MCPServerStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"

@dataclass
class MCPToolInfo:
    name: str
    description: str
    server_name: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    
class MCPClient:
    def __init__(self, name: str, config: MCPServerConfig, cwd: Path):
        self.name = name
        self.config = config
        self.cwd = cwd
        self.status = MCPServerStatus.DISCONNECTED
        self._client: Client | None = None
        
        self.tools: dict[str, MCPToolInfo] =  dict()
        
    def _create_transport(self) -> StdioTransport | SSETransport:
        if self.config.command:
            env = os.environ.copy()
            env.update(self.config.env)
            
            return StdioTransport(
                command=self.config.command,
                args=list(self.config.args),
                env=env,
                cwd=str(self.config.cwd or self.cwd),
                log_file=Path(os.devnull)
            )
            
        return SSETransport(
            url=self.config.url
        )
    
    async def connect(self) -> None:
        if self.status == MCPServerStatus.CONNECTED:
            return
        
        self.status = MCPServerStatus.CONNECTING
        
        try:
            self._client = Client(transport=self._create_transport())
            
            await self._client.__aenter__()
            
            tool_results = await self._client.list_tools()
            
            for tool in tool_results:
                input_schema = getattr(tool, "input_schema", None)
                if input_schema is None:
                    input_schema = getattr(tool, "inputSchema", {})

                self.tools[tool.name] = MCPToolInfo(
                    name=tool.name,
                    description=tool.description or "",
                    input_schema=input_schema,
                    server_name=self.name
                )
                
            self.status = MCPServerStatus.CONNECTED
        except Exception:
            self.status = MCPServerStatus.ERROR
            raise
        
    
    async def disconnect(self) -> None:
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None
        
        self.tools.clear()
        self.status = MCPServerStatus.DISCONNECTED

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]):
        if not self._client or self.status != MCPServerStatus.CONNECTED:
            raise RuntimeError(f"Not connected to server {self.name}")

        result = await self._client.call_tool(tool_name, arguments)

        output = []
        for item in result.content:
            if hasattr(item, "text"):
                output.append(item.text)
            else:
                output.append(str(item))

        return {
            "output": "\n".join(output),
            "is_error": result.is_error,
        }
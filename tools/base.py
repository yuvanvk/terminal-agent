from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError
from pydantic.json import model_json_schema


@dataclass
class ToolInvocation:
    cwd: Path
    params: dict[str, Any]

@dataclass
class ToolResult:
    success: bool
    output: str
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
@dataclass
class ToolConfirmation:
    tool_name: str
    description: str
    params: dict[str, Any]


class ToolKind(str, Enum):
    READ = "read"
    WRITE = "write"
    SHELL = "shell"
    NETWORK = "network"
    MCP = "mcp"
    MEMORY = "memory"


class ToolBase(ABC):
    name: str = "Base tool"
    description: str = "Base tool"
    kind: ToolKind = ToolKind.READ

    @property
    def schema(self) -> dict[str, Any] | type[BaseModel]:
        raise NotImplementedError(
            "Tool should implement schema property or class attribute"
        )

    @abstractmethod
    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        pass
    
    def validate_params(self, params: dict[str, Any] | type["BaseModel"]) -> list[str]:
            schema = self.schema
            if isinstance(schema, type) and issubclass(schema, BaseModel):
                try:
                    BaseModel(**params)
                except ValidationError as e:
                    errors = []
                    for error in e.errors():
                        field = ".".join(str(x) for x in error.get("loc", []))
                        msg = error.get("msg", "Validation error")
                        errors.append(f"Parameter '{field}': {msg}")
                    return errors
                except Exception as e:
                    return [str(e)]
                
            return []

    def is_mutating(self) -> bool:
        return self.kind in {
            ToolKind.WRITE, 
            ToolKind.SHELL, 
            ToolKind.NETWORK, 
            ToolKind.MEMORY
        }

    async def get_confirmation(self, invocation: ToolInvocation) -> ToolConfirmation | None:
        if self.is_mutating() is False:
            return None
        
        return ToolConfirmation(
            tool_name=self.name,
            description=self.description,
            params=invocation.params
        )
        
    def to_openai_json(self) -> dict[str, Any]:
        schema = self.schema
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            json_schema = model_json_schema(schema)
            
            return {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": json_schema.get("properties", {}),
                    "required": json_schema.get("required", []),
                }
            }
            
        if isinstance(schema, dict):
            result = {
                "name": self.name,
                "description": self.description,
            }
            
            if "parameters" in schema:
                result["parameters"] = schema["parameters"]
            else:
                result["parameters"] = schema
            
            return result
        
        raise ValueError(f"Invalid schema type for tool {self.name}: {type(schema)}")
    
    
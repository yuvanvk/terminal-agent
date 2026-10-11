import json

from pydantic import BaseModel, Field

from config.loader import get_data_dir
from tools.base import Tool, ToolInvocation, ToolKind, ToolResult


class MemoryParams(BaseModel):
    action: str = Field(
        ..., description="Action: 'set', 'get', 'delete', 'list', 'clear'"
    )
    key: str | None = Field(
        None, description="Memory key (required for `set`, `get`, `delete`)"
    )
    value: str | None = Field(None, description="Value to store (required for `set`)")
    
    
class MemoryTool(Tool):
    name = "memory"
    description = "Store and retrieve persistent memory. Use this to remember user preferences, important context or notes."
    kind = ToolKind.MEMORY

    schema = MemoryParams
    
    def _load_memory(self):
        data_path = get_data_dir()
        data_path.mkdir(parents=True, exist_ok=True)
        memory_file = data_path / "memory.json"
        
        if not memory_file.exists():
            return {'entries': {}}
        
        try:
            content = memory_file.read_text(encoding="utf-8")
            return json.loads(content)
        except Exception:
            return {'entries': {}}
        
    def _save_memory(self, memory):
        data_path = get_data_dir()
        data_path.mkdir(parents=True, exist_ok=True)
        path = data_path / "memory.json"
        
        try:
            content = json.dumps(memory, indent=2, ensure_ascii=False)
            path.write_text(content)
        except Exception as e:
            raise RuntimeError(f"Failed to save memory: {e}")
        

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = MemoryParams(**invocation.params)

        if params.action == "list":
            memory = self._load_memory()
            
            entries = memory.get("entries", {})
            if not entries:
                return ToolResult.success_result(
                    "No memories stored",
                    metadata={
                        "found": False,
                    },
                )
            
            
            output_lines = ["Stored memories: "]
            
            for key, value in sorted(entries.items()):
                output_lines.append(f"   {key}: {value}")
        
            return ToolResult.success_result(
                "\n".join(output_lines),
                metadata={
                    "found": True,
                },
            )
        
        elif params.action.lower() == "set":
            if not params.key or not params.value:
                return ToolResult.error_result(
                    "`key` and `value` are required for 'set' action"
                )
            
            memory = self._load_memory()
            memory['entries'][params.key] = params.value
            
            self._save_memory(memory=memory)
            
            return ToolResult.success_result(f"Set memory: {params.key}")
        
        elif params.action.lower() == "get":
            if not params.key:
                return ToolResult.error_result("`key` required for 'get' action")

            memory = self._load_memory()
            if params.key not in memory.get("entries", {}):
                return ToolResult.success_result(
                    f"Memory not found: {params.key}",
                    metadata={
                        "found": False,
                    },
                )
            return ToolResult.success_result(
                f"Memory found: {params.key}: {memory['entries'][params.key]}",
                metadata={
                    "found": True,
                },
            )
        
        elif params.action == "delete":
            if not params.key:
                return ToolResult.error_result("`key` required for 'get' action")
            memory = self._load_memory()
            if params.key not in memory.get("entries", {}):
                return ToolResult.success_result(f"Memory not found: {params.key}")

            del memory["entries"][params.key]
            self._save_memory(memory)


        elif params.action == "clear":
            memory = self._load_memory()
            count = len(memory.get("entries", {}))
            memory["entries"] = {}
            self._save_memory(memory)
            return ToolResult.success_result(f"Cleared {count} memory entries")
        else:
            return ToolResult.error_result(f"Unknown action: {params.action}")

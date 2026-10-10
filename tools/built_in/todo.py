import uuid

from pydantic import BaseModel, Field

from tools.base import Tool, ToolInvocation, ToolKind, ToolResult


class TodosParams(BaseModel):
    action: str = Field(..., description="Action: 'add', 'complete', 'list', 'clear'")
    id: str | None = Field(None, description="Todo ID (for complete)")
    content: str | None = Field(None, description="Todo content (for add)")
    todos: list[str] | None = Field(
        None,
        description="Pass a list of todos"
    )
    

class TodosTool(Tool):
    name = "todos"
    description = "Manage a task list for the current session. Use this to track progress on multi-step tasks."
    kind = ToolKind.MEMORY

    schema = TodosParams
    
    def __init__(self, config):
        super().__init__(config=config)
        
        self._todos = {}

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = TodosParams(**invocation.params)

        if params.action == "list":
            if not self._todos:
                return ToolResult.error_result("")
            
            output_lines = ["Todos: "]
            
            for id, content in self._todos.items():
                output_lines.append(f"   [{id}] - {content}")
        
            return ToolResult.success_result("\n".join(output_lines))
        
        elif params.action == "add":
            if not params.content:
                return ToolResult.error_result("Provide a `content` in order to 'add' a todo")
            
            id = str(uuid.uuid4())[:8]
            self._todos[id] = params.content
            return ToolResult.success_result(f"Added Todo [{id}] - {params.content}")
        
        elif params.action == "complete":
            if not params.id:
                return ToolResult.error_result("`id` required for 'complete' action")
            
            if  params.id not in self._todos:
                return ToolResult.error_result(f"Todo not found: {params.id}")

            content = self._todos.pop(params.id)
            return ToolResult.success_result(f"Completed todo [{params.id}]: {content}")

        elif params.action == "clear":
            count = len(self._todos)
            self._todos.clear()
            return ToolResult.success_result(f"Cleared {count} todos")
        elif params.action == "add_all":
            if not params.todos and not isinstance(params.todos, list[str]):
                return ToolResult.error_result("To add multiple todos, provide a list of strings in the `todos` field")
            
            for todo in params.todos:
                todo_id = str(uuid.uuid4())[:8]
                self._todos[todo_id] = todo
            
            return ToolResult.success_result("Added todos: " + "\n".join(params.todos))
        else:
            return ToolResult.error_result(f"Unknown action: {params.action}")

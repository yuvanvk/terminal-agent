import json
import uuid
from datetime import datetime

from client.llm_client import LLMClient
from config.config import Config
from config.loader import get_data_dir
from context.compaction import ChatCompactor
from context.context_manager import ContextManager
from tools.discovery import ToolDiscoveryManager
from tools.mcp.manager import MCPManager
from tools.registry import create_default_registry


class Session:
    def __init__(self, config: Config):
        self.config = config
        self._tool_registry = create_default_registry(config=config)
        self.client = LLMClient(config=config)
        self._context_manager: ContextManager | None = None
        self.session_id = str(uuid.uuid4())
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.tool_discovery_manager = ToolDiscoveryManager(
            config=self.config,
            registry=self._tool_registry 
        )
        
        self.mcp_manager = MCPManager(config=self.config)
        self.chat_compactor = ChatCompactor(client=self.client)

        self._turn_count = 0
        
    async def initialise(self):
        await self.mcp_manager.initialize()
        self.mcp_manager.register_tools(self._tool_registry)
        
        self.tool_discovery_manager.discover_all()
        self._context_manager = ContextManager(
            config=self.config,
            tools=self._tool_registry.get_tools(),
            user_memory=self._load_memory(),
        )

    def _load_memory(self):
        data_path = get_data_dir()
        data_path.mkdir(parents=True, exist_ok=True)
        path = data_path / "memory.json"

        if not path.exists():
            return None

        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            entries = data.get("entries")
            if not entries:
                return None

            lines = ["User preferences and notes:"]
            for key, value in entries.items():
                lines.append(f"- {key}: {value}")

            return "\n".join(lines)
        except Exception:
            return None

    def increment_turn_count(self) -> int:
        self._turn_count += 1
        self.updated_at = datetime.now()

        return self._turn_count

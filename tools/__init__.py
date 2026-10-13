from tools.built_in.edit_file import EditFileTool
from tools.built_in.glob import GlobTool
from tools.built_in.grep import GrepTool
from tools.built_in.list_dir import ListDirTool
from tools.built_in.memory import MemoryTool
from tools.built_in.shell import ShellTool
from tools.built_in.todo import TodosTool
from tools.built_in.web_fetch import WebFetchTool
from tools.built_in.web_search import WebSearchTool
from tools.sub_agent import CODEBASE_INVESTIGATOR

from .built_in.read_file import ReadFileTool
from .built_in.write_file import WriteFileTool

__all__ = [
    'EditFileTool',
    'GlobTool',
    'GrepTool',
    'ListDirTool',
    'MemoryTool',
    'ReadFileTool',
    'ShellTool',
    'TodosTool',
    'WebFetchTool',
    'WebSearchTool',
    'WriteFileTool'
]

def get_all_built_tools() -> list[type]:
    return [
        ReadFileTool,
        WriteFileTool,
        EditFileTool,
        ShellTool,
        ListDirTool,
        GrepTool,
        GlobTool,
        WebSearchTool,
        WebFetchTool,
        TodosTool,
        MemoryTool
    ]
    

from tools.built_in.edit_file import EditFileTool
from tools.built_in.shell import ShellTool

from .built_in.read_file import ReadFileTool
from .built_in.write_file import WriteFileTool

__all__ = [
    'EditFileTool',
    'ReadFileTool',
    'ShellTool',
    'WriteFileTool'
]

def get_all_built_tools() -> list[type]:
    return [
        ReadFileTool,
        WriteFileTool,
        EditFileTool,
        ShellTool  
    ]

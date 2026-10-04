import logging
from pathlib import Path
from typing import Any

import tomli
from platformdirs import user_config_dir

from utils.errors import ConfigError

from .config import Config

CONFIG_FILE_NAME = "config.toml"
AGENT_MD_FILE_NAME = "AGENT.md"
logger = logging.getLogger(__name__)

def get_config_dir():
    return Path(user_config_dir(appname="terminal-agent"))

def get_system_config_path() -> Path:
    return get_config_dir() / CONFIG_FILE_NAME

def _get_project_config(cwd: Path) -> Path | None:
    current = cwd.resolve()
    agent_dir = current / '.terminal-agent'
    
    if agent_dir.is_dir():
        config_file = agent_dir / CONFIG_FILE_NAME
        if config_file.is_file():
            return config_file
    
    return None

def get_agent_md_file(cwd: Path) -> str:
    current = cwd.resolve()
    
    if current.is_dir():
        agent_md_file = current / AGENT_MD_FILE_NAME
        if agent_md_file.is_file():
            content = agent_md_file.read_text(encoding="utf-8")
            return content
    
    return None

def __parse_toml(path: Path):
    try:
        with open(path, "rb") as f:
            return tomli.load(f)

    except tomli.TOMLDecodeError as e:
        raise ConfigError("Invalid TOML in {path}: {e}", config_file=str(path)) from e
    except (OSError, IOError):
        raise ConfigError("Failed to read config file {path}: {e}", config_file=str(path))
    
def _merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_dicts(result[key], value)
        else:
            result[key] = value
    return result
    
    
def load_config(cwd: Path | None) -> Config:
    cwd = cwd or Path.cwd()
    
    system_config = get_system_config_path()
    config_dict = {}
    
    if system_config.is_file():
        try:
            config_dict = __parse_toml(system_config)
        except ConfigError:
            logger.warning(f"Skipping invalid system config: {system_config}")

    project_path = _get_project_config(cwd)
    if project_path:
        try:
            project_config_dict = __parse_toml(path=project_path)
            config_dict = _merge_dicts(config_dict, project_config_dict)
        except ConfigError:
            logger.warning(f"Skipping invalid system config: {project_path}")
        
    if "cwd" not in config_dict:
        config_dict["cwd"] = cwd
    
    if "developer_instructions" not in config_dict:
        agent_md_content = get_agent_md_file(cwd)
        if agent_md_content:
            config_dict["developer_instructions"] = agent_md_content
        
    try:
        config = Config(**config_dict)
    except Exception as e:
        raise ConfigError(f"Invalid configuration: {e}", details=config_dict) from e
    
    return config
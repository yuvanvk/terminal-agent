import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from config.config import ApprovalPolicy
from tools.base import ToolConfirmation


class ApprovalDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_CONFIRMATION = "needs_confirmation"
    
@dataclass
class ApprovalContext:
    tool_name: str
    params: dict[str, Any]
    is_mutating: bool
    affected_paths: list[Path]
    command: str | None = None
    is_dangerous: bool = False

DANGEROUS_PATTERNS = [
    # File system destruction
    r"rm\s+(-rf?|--recursive)\s+[/~]",
    r"rm\s+-rf?\s+\*",
    r"rmdir\s+[/~]",
    # Disk operations
    r"dd\s+if=",
    r"mkfs",
    r"fdisk",
    r"parted",
    # System control
    r"shutdown",
    r"reboot",
    r"halt",
    r"poweroff",
    r"init\s+[06]",
    # Permission changes on root
    r"chmod\s+(-R\s+)?777\s+[/~]",
    r"chown\s+-R\s+.*\s+[/~]",
    # Network exposure
    r"nc\s+-l",
    r"netcat\s+-l",
    # Code execution from network
    r"curl\s+.*\|\s*(bash|sh)",
    r"wget\s+.*\|\s*(bash|sh)",
    # Fork bomb
    r":\(\)\s*\{\s*:\|:&\s*\}\s*;",
]

def is_dangerous_command(command: str) -> bool:
    for p in DANGEROUS_PATTERNS:
        if re.search(p, command, re.IGNORECASE):
            return True
        
    return False


def is_safe_command(command: str) -> bool:
    for p in SAFE_PATTERNS:
        if re.search(p, command, re.IGNORECASE):
            return True
        
    return False

# Patterns for safe commands (can be auto-approved)
SAFE_PATTERNS = [
    # Information commands
    r"^(ls|dir|pwd|cd|echo|cat|head|tail|less|more|wc)(\s|$)",
    r"^(find|locate|which|whereis|file|stat)(\s|$)",
    # Development tools (read-only)
    r"^git\s+(status|log|diff|show|branch|remote|tag)(\s|$)",
    r"^(npm|yarn|pnpm)\s+(list|ls|outdated)(\s|$)",
    r"^pip\s+(list|show|freeze)(\s|$)",
    r"^cargo\s+(tree|search)(\s|$)",
    # Text processing (usually safe)
    r"^(grep|awk|sed|cut|sort|uniq|tr|diff|comm)(\s|$)",
    # System info
    r"^(date|cal|uptime|whoami|id|groups|hostname|uname)(\s|$)",
    r"^(env|printenv|set)$",
    # Process info
    r"^(ps|top|htop|pgrep)(\s|$)",
]


class ApprovalManager:
    def __init__(
        self, 
        approval_policy: ApprovalPolicy, 
        cwd: Path | None, 
        confirmation_cb: Callable[[ToolConfirmation], bool] | None = None
    ) -> None:
        self.approval_policy = approval_policy
        self.cwd = cwd
        self.confirmation_cb = confirmation_cb
        
    def _assess_command_safety(self, command: str) -> ApprovalDecision:
        if self.approval_policy == ApprovalPolicy.YOLO:
            return ApprovalDecision.APPROVED
        if is_dangerous_command(command=command):
            return ApprovalDecision.REJECTED
        
        if self.approval_policy == ApprovalPolicy.NEVER:
            if is_safe_command(command):
                return ApprovalDecision.APPROVED
            return ApprovalDecision.REJECTED
        
        if self.approval_policy in { ApprovalPolicy.AUTO, ApprovalPolicy.ON_FAILURE }:
            return ApprovalDecision.APPROVED
        
        if self.approval_policy == ApprovalPolicy.AUTO_EDIT:
            if is_safe_command(command=command):
                return ApprovalDecision.APPROVED
            
            return ApprovalDecision.NEEDS_CONFIRMATION
        
        
        if is_safe_command(command=command):
            return ApprovalDecision.APPROVED
        
        return ApprovalDecision.NEEDS_CONFIRMATION
        
    def check_approval(self, context: ApprovalContext) -> ApprovalDecision:
        if not context.is_mutating:
            return ApprovalDecision.APPROVED
        
        if context.command:
            decision = self._assess_command_safety(command=context.command)
            if decision != ApprovalDecision.NEEDS_CONFIRMATION:
                return decision
            
        for p in context.affected_paths:
            path_decision = ApprovalDecision.NEEDS_CONFIRMATION
            
            if p.is_relative_to(self.cwd):
                path_decision = ApprovalDecision.APPROVED   
            else:
                return path_decision
        
        if context.is_dangerous:
            if self.approval_policy == ApprovalPolicy.YOLO:
                return ApprovalDecision.APPROVED
            
            return ApprovalDecision.NEEDS_CONFIRMATION
        
        return ApprovalDecision.APPROVED
    
    
    def request_confirmation(self, confirmation: ToolConfirmation) -> bool:
        if self.confirmation_cb:
            result = self.confirmation_cb(confirmation)
            return result
        
        return True
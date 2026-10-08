import asyncio
import fnmatch
import os
import sys
from pathlib import Path
from signal import signal

from pydantic import BaseModel, Field

from tools.base import Tool, ToolInvocation, ToolKind, ToolResult

BLOCKED_COMMANDS = {
    "rm -rf /",
    "rm -rf ~",
    "rm -rf /*",
    "dd if=/dev/zero",
    "dd if=/dev/random",
    "mkfs",
    "fdisk",
    "parted",
    ":(){ :|:& };:",  # Fork bomb
    "chmod 777 /",
    "chmod -R 777",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "init 0",
    "init 6",
}

class ShellParams(BaseModel):
    command: str = Field(
        ...,
        description=""
    )
    timeout: int = Field(
        120,
        le=1,
        ge=600,
        description="Timeout in seconds for the command execution."
    )
    cwd: str | None = Field(
        None,
        description="Current working directory for the command execution."
    )


class ShellTool(Tool):
    name = "shell"
    description = "Execute a shell command. Use this for running system commands, scripts and CLI tools."

    schema = ShellParams
    kind = ToolKind.SHELL
    
    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = ShellParams(**invocation.params)
        
        # block sensitive commands
        for blocked in BLOCKED_COMMANDS:
            if blocked in params.command:
                return ToolResult.error_result(
                    f"Command blocked for safety: {params.command}",
                    metadata={"blocked": True},
                )
        
        if params.cwd:
            cwd = Path(params.cwd)
            if not cwd.is_absolute():
                cwd = invocation.cwd / cwd
        else:
            cwd = invocation.cwd
            
        if not cwd.exists():
            return ToolResult.error_result(
                f"Working directory doesn't exist: {cwd}"
            )
        
                
        env = self._build_shell_environment()
        if sys.platform == "win32":
            shell_cmd = ["cmd.exe", "/c", params.command]
        else:
            shell_cmd = ["/bin/bash", "-c", params.command]
            
        process = await asyncio.create_subprocess_exec(
            *shell_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=env,
            start_new_session=True,
        )

        try:
            stdout_data, stderr_data = await asyncio.wait_for(
                process.communicate(),
                timeout=params.timeout,
            )
        except TimeoutError:
            if sys.platform != "win32":
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            else:
                process.kill()
            await process.wait()
            return ToolResult.error_result(f"Command timed out after {params.timeout}s")

        stdout = stdout_data.decode("utf-8", errors="replace")
        stderr = stderr_data.decode("utf-8", errors="replace")
        exit_code = process.returncode

        output = ""
        if stdout.strip():
            output += stdout.rstrip()

        if stderr.strip():
            output += "\n--- stderr ---\n"
            output += stderr.rstrip()

        if exit_code != 0:
            output += f"\nExit code: {exit_code}"

        if len(output) > 100 * 1024:
            output = output[: 100 * 1024] + "\n... [output truncated]"

        return ToolResult(
            success=exit_code == 0,
            output=output,
            error=stderr if exit_code != 0 else None,
            exit_code=exit_code,
        )
        
    
    def _build_shell_environment(self) -> dict[str, str]:
        env = os.environ.copy()
        
        shell_env = self.config.shell_environment
        
        if not shell_env.ignore_default_excludes:
            for pattern in shell_env.exclude_patterns:
                keys_to_remove = [
                    k for k in env.keys() if fnmatch.fnmatch(k.upper(), pattern.upper())
                ]
        
            if keys_to_remove:
                for k in keys_to_remove:
                    del env[k]
        
        if shell_env.set_vars:
            env.update(shell_env.set_vars)

        return env
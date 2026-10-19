# Terminal Agent

Terminal Agent is an AI coding assistant that runs in your terminal. Give it a
task in plain language and it can inspect a project, answer questions about the
code, make changes, run shell commands, and use additional tools exposed by
configured MCP servers. It streams responses and tool activity in a
Rich-powered terminal interface.

The agent uses an OpenAI-compatible chat completions API. Select a model and
configure the API credentials and, when needed, the provider's base URL.

## Features

- Interactive chat or a single prompt from the command line.
- Project-aware instructions from a root-level `AGENT.md`.
- Built-in tools for reading, writing, and editing files; listing and searching
  directories; running shell commands; web search and fetch; session todos; and
  persistent user memory.
- MCP client support for connecting to configured stdio or SSE servers and
  making their tools available to the agent.
- Approval policies for operations, including interactive confirmation in the
  terminal.
- Two specialized subagents: a codebase investigator and a code reviewer.
- Custom Python tools discovered from `.terminal-agent/tools/`.
- Session statistics, saved sessions, checkpoints, and restore/resume commands.
- Optional lifecycle hooks for agent and tool events.

## Requirements

- Python 3.11 or newer.
- An API key for an OpenAI-compatible chat completions provider.
- `uv` is recommended for creating the environment and installing dependencies.
- Node.js and npm/npx are needed only if an MCP server is configured to run
  through `npx`.

## Installation

Clone the repository and install its dependencies:

```sh
git clone https://github.com/yuvanvk/terminal-agent.git
cd terminal-agent
uv sync
```

Create a `.env` file in the project root:

```dotenv
API_KEY=your-api-key
# Optional. Set this for an OpenAI-compatible provider with a custom endpoint.
BASE_URL=https://your-provider.example/v1
```

Keep `.env` and API credentials private. Do not commit secrets to the
repository.

## Usage

Start an interactive session in the current directory:

```sh
uv run python main.py
```

Pass a prompt to run one task and exit:

```sh
uv run python main.py "Explain the main components of this project"
```

Choose a different working directory:

```sh
uv run python main.py --cwd /path/to/project
```

The `--cwd` option can also be shortened to `-c`. The working directory is
used as the project context for file tools and MCP stdio servers.

## Configuration

Configuration is loaded from the user configuration file and then overridden
by the project configuration at `.terminal-agent/config.toml`. The project
configuration is useful for settings that should apply only to one repository.
If no working directory is specified in the configuration, the current
directory (or the directory passed with `--cwd`) is used.

For example:

```toml
max_turns = 100
approval = "on-request"

[model]
name = "your-provider/your-model"
temperature = 1.0
context_window = 128000
```

The model name and other model properties belong under `[model]`. Top-level
settings include `max_turns`, `approval`, `allowed_tools`, and `hooks_enabled`.
When `allowed_tools` is set, it limits which registered tools are exposed to
the model.

### MCP servers

Define MCP servers in the `[mcp_servers.<server-name>]` section. For example,
this config starts the filesystem server over stdio and allows it to access
the project directory and `/tmp`:

```toml
[mcp_servers.filesystem]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", ".", "/tmp"]
startup_timeout_sec = 10
```

MCP servers can use either a `command` with `args` for stdio, or a `url` for
SSE; a server entry cannot specify both. Set `enabled = false` to disable a
configured server. For stdio servers, the process working directory defaults
to the agent's working directory. Pass only directories the MCP server should
be allowed to access.

Use `/mcp` in an interactive session to see configured server connection
status and discovered tool counts. Use `/tools` to list tools available to the
agent.

### Custom tools and instructions

- Put a project-specific `AGENT.md` in the working directory to provide
  developer instructions to the agent.
- Put custom Python tool modules in `.terminal-agent/tools/`. The agent
  discovers tools defined there when it initializes.
- User-level config and custom tools are loaded from the platform's
  `terminal-agent` configuration directory.

## Interactive commands

Type a message to ask the agent to work on a task. Slash commands provide
session controls:

| Command | Description |
| --- | --- |
| `/help` | Show the command list and usage tips. |
| `/exit`, `/quit` | End the interactive session. |
| `/clear` | Clear the current conversation. |
| `/config` | Show the active model, approval policy, working directory, and related settings. |
| `/model <name>` | Change the model for the current session. |
| `/approval <mode>` | Change the approval policy for the current session. |
| `/stats` | Show session statistics. |
| `/tools` | List the tools available to the agent. |
| `/mcp` | Show MCP server status and discovered tool counts. |
| `/save` | Save the current session. |
| `/sessions` | List saved sessions. |
| `/resume <session_id>` | Resume a saved session. |
| `/checkpoint [name]` | Save a checkpoint of the current session. |
| `/restore <checkpoint_id>` | Restore a checkpoint. |

## Development

Install dependencies and run the CLI from the repository root:

```sh
uv sync
uv run python main.py
```

The project currently has no dedicated automated test suite.